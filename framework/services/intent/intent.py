import requests, time, glob, os
from bus.Message import Message
from bus.MsgBusClient import MsgBusClient
from framework.util.utils import LOG, Config, get_wake_words, aplay, normalize_sentence, remove_pleasantries
from framework.services.intent.nlp.shallow_parse.nlu import SentenceInfo
from framework.services.intent.nlp.shallow_parse.shallow_utils import scrub_sentence, remove_articles
from framework.message_types import (
        MSG_UTTERANCE, 
        MSG_MEDIA, 
        MSG_RAW, 
        MSG_SYSTEM
        )

class UttProc:
    # English language specific intent parser. Monitors the save_text/ FIFO 
    # for utterances to process. Emits utterance messages. If skill_id
    # is not '' the utterance matched an intent in the skill_id skill.
    def __init__(self, bus=None, timeout=5):
        self.skill_id = 'intent_service'

        # create bus client if none provided
        if bus is None:
            bus = MsgBusClient(self.skill_id)
        self.bus = bus

        self.intents = {}

        # set up logging into intent.log
        self.base_dir = os.getenv('SVA_BASE_DIR')
        self.tmp_file_path = self.base_dir + '/tmp/'
        log_filename = self.base_dir + '/logs/intent.log'
        self.log = LOG(log_filename).log

        # resources
        self.log.info("Intent Service Starting")
        self.earcon_filename = self.base_dir + "/framework/assets/earcon_start.wav"

        # set this to True before calling run()
        # set to false to discontinue running.
        self.is_running = False

        # get configuration
        cfg = Config()
        self.crappy_aec = cfg.get_cfg_val('Advanced.CrappyAEC')
        remote_nlp = cfg.get_cfg_val('Advanced.NLP.UseRemote')
        self.use_remote_nlp = True
        if remote_nlp and remote_nlp == 'n':
            self.use_remote_nlp = False

        # we try to keep in sync with the system skill
        # so we can limit OOBs to verbs which have been
        # registered
        self.recognized_verbs = []

        # TODO need get_stop_aliases() method in framework.util.utils
        self.stop_aliases = ['stop', 'terminate', 'abort', 'cancel', 'kill', 'exit']

        # establish wake word(s)
        self.wake_words = []
        wws = get_wake_words()
        for ww in wws:
            self.wake_words.append( ww.lower() )

        # register message handlers
        self.bus.on('register_intent', self.handle_register_intent)
        self.bus.on('system', self.handle_system_message)


    def handle_system_message(self, message):
        # we try to stay in-sync with the system skill regarding OOBs
        data = message.data
        self.log.debug("Intent svc handle sys msg %s" % (data,))
        if data['skill_id'] == 'system_skill':
            # we only care about system messages - reserve and release oob
            self.log.debug("Intent service handle system message %s" % (message.data,))

            if data['subtype'] == 'reserve_oob':
                self.recognized_verbs.append( data['verb'] )

            if data['subtype'] == 'release_oob':
                del self.recognized_verbs[ data['verb'] ]


    def is_oob(self, utt):
        # we don't just match hard oobs, we also look for oobs
        # using special handling to overcome poor hardware
        # return values:
        #  't' - normal oob detected
        #  'o' - aec oob detected
        #  'f' - no oob detected
        ua = utt.split(" ")

        if len(ua) == 1:
            if ua[0] in self.recognized_verbs or ua[0] in self.stop_aliases or ua[0] == 'pause' or ua[0] == 'resume':
                self.log.error("Intent Barge-In Normal OOB Detected")
                return 't'

        # in a system with decent aec you can just return 'f' here
        if not self.crappy_aec:
            return 'f'

        # here we try to deal with poor quality input (IE no AEC).
        # you can disable this on a device with good AEC. also see
        # sva_base for other code which would use this config value
        # if it were available (poor audio input quality indicator)
        for ww in self.wake_words:
            for alias in self.stop_aliases:
                oob_phrase = ww + ' ' + alias
                if oob_phrase.lower() in utt.lower() or ( alias in utt.lower() and ww in utt.lower() ):
                    self.log.warning("** Maybe ? Intent Barge-In detected. Don't Worry, I'm Handling It! **")
                    return 'o'

        return 'f'


    def get_sentence_type(self, utt):
        # very rough is question or not
        # TODO - improve upon this
        vrb = utt.split(" ")[0]
        resp = "I"
        for wrd in self.question_words:
            if utt.startswith(wrd):
                resp = "Q"
                break
        return resp


    def send_utt(self, utt):
        # sends an utterance to a 
        # target and handles edge cases
        target = utt.get('skill_id','*')
        if target == '':
            target = '*'
        if utt == 'stop':
            target = 'system_skill'
        self.log.error("WTFWTF %s" % (utt,))
        self.bus.send(MSG_UTTERANCE, target, {'utt': utt,'subtype':'utt'})


    def send_media(self, info):
        self.bus.send(MSG_MEDIA, 'media_skill', info)


    def send_oob_to_system(self, utt, contents):
        info = {
                'error':'', 
                'subtype':'oob', 
                'skill_id':'system_skill', 
                'from_skill_id':self.skill_id, 
                'sentence_type':'I', 
                'sentence':contents, 
                'verb':utt, 
                'intent_match':''
                }
        self.bus.send(MSG_SYSTEM, 'system_skill', info)


    def get_question_intent_match(self, info):
        aplay(self.earcon_filename)  # should be configurable

        # see if a quation matches an intent.
        skill_id = ''
        for intent in self.intents:
            stype, subject, verb = intent.split(":") 
            if stype == 'Q' and subject in info['subject'] and verb == info['qword']:
                # fuzzy match - TODO please improve upon this
                info['subject'] = subject
                skill_id = self.intents[intent]['skill_id']
                intent_state = self.intents[intent]['state']
                return skill_id, intent

        return skill_id, ''


    def get_intent_match(self, info):
        aplay(self.earcon_filename)  # should be configurable

        # for utterances of type command
        # an intent match is a subject:verb
        # and we don't fuzzy match
        skill_id = ''

        intent_type = 'C'
        if info['sentence_type'] == 'I':
            self.log.warning("Intent trying to match an informational statement which it is not designed to to! %s" % (info,))
            info['sentence_type'] == 'C'

        subject = remove_articles(info['subject'])
        if subject:
            subject = subject.replace(":",";")
            subject = subject.strip()

        key = intent_type + ':' + subject.lower() + ':' + info['verb'].lower().strip()

        self.log.error("Intent match key is %s" % (key,))

        if key in self.intents:
            skill_id = self.intents[key]['skill_id']
            intent_state = self.intents[key]['state']
            self.log.debug("Intent matched[%s] skill=%s, intent_state=%s" % (key,skill_id, intent_state))
            return skill_id, key

        # no match will return ('','')
        return skill_id, ''


    def handle_register_intent(self, msg):
        data = msg.data

        # the subject may contain colons which is 
        # what we prefer to use as a delimiter
        # so we convert them here
        subject = data['subject'].replace(":", ";")

        key = data['intent_type'] + ':' + subject.lower() + ':' + data['verb']

        if key in self.intents:
            self.log.warning("Intent clash! key=%s, skill_id=%s ignored!" % (key,data['skill_id']))
        else:
            self.intents[key] = {'skill_id':data['skill_id'], 'state':'enabled'}


    def run(self):
        self.log.info("Intent processor started - 'is_running' is %s" % (self.is_running,))
        si = SentenceInfo(self.base_dir)

        while self.is_running:
            # get all text files in the input directory
            mylist = sorted( [f for f in glob.glob(self.tmp_file_path + "save_text/*.txt")] )

            # if we have at least one
            if len(mylist) > 0:
                # take the first
                txt_file = mylist[0]

                # grab contents
                fh = open(txt_file)
                contents = fh.read()
                fh.close()

                # clean up input
                start = contents.find("]")
                utt_type = contents[1:start]
                utt = contents[start+1:]

                utt = scrub_sentence(utt)

                # we special case OOBs here
                oob_type = self.is_oob(utt)
                if oob_type == 't':
                    res = self.send_oob_to_system(utt, contents) 

                elif oob_type == 'o':
                    res = self.send_oob_to_system('stop', contents) 

                elif utt_type == 'RAW':
                    # send raw messages to the system skill
                    # and let it figure out what to do with them
                    if contents:
                        self.bus.send(MSG_RAW, 'system_skill', {'utterance': contents[5:]})

                else:
                    sentence_type = si.get_sentence_type(utt)
                    self.log.debug("Sentence type = %s" % (sentence_type,))
                    utt = normalize_sentence(utt)
                    if sentence_type != 'Q':
                        utt = remove_pleasantries(utt)

                    si.parse_utterance(utt)

                    info = {
                        'error':'', 
                        'sentence_type': si.sentence_type, 
                        'sentence': si.original_sentence, 
                        'normalized_sentence': si.normalized_sentence, 
                        'qtype': si.insight.qtype, 
                        'np': si.insight.np, 
                        'vp': si.insight.vp, 
                        'subject': si.insight.subject, 
                        'squal': si.insight.squal, 
                        'question': si.insight.question,
                        'qword': si.insight.question, 
                        'value': si.insight.value, 
                        'raw_input': contents, 
                        'verb': si.insight.verb,
                        'aux_verb': si.insight.aux_verb,
                        'rule': si.structure.shallow,
                        'tree': si.structure.tree,
                        'subtype':'', 
                        'from_skill_id':'', 
                        'skill_id':'', 
                        'intent_match':''
                        }

                    # sentence types 
                    # Q - question
                    # C - command
                    # I - info (currently unsupported)
                    # U - unknown sentence structure
                    # M - media request
                    # O - oob (out of bounds) request
                    if si.sentence_type == 'Q':
                        print("Match Question. key=Q:%s:%s" % (si.insight.question,si.insight.subject))
                        info['skill_id'], info['intent_match'] = self.get_question_intent_match({'subject':info['subject'], 'qword':info['question']})
                        print("Match Question. skid:%s, im:%s" % (info['skill_id'], info['intent_match']))
                        res = self.send_utt(info) 

                    elif si.sentence_type == 'C':
                        print("Match Command")
                        info['skill_id'], info['intent_match'] = self.get_intent_match(info)
                        res = self.send_utt(info) 

                    elif si.sentence_type == 'M':
                        print("Media Command")
                        info['skill_id'] = 'media_skill'
                        info['from_skill_id'] = self.skill_id
                        info['subtype'] = 'media_query'
                        res = self.send_media(info) 

                    elif si.sentence_type == 'O':
                        print("OOB Command")
                        if utt in self.recognized_verbs:
                            self.send_oob_to_system(utt, contents)
                        else:
                            self.log.warning("Ignoring not recognized OOB in intent_service '%s' not found in %s" % (utt,self.recognized_verbs))

                    else:
                        print("Unknown sentence type or Informational sentence. Ignored for now.")


                # remove input file from file system
                os.remove(txt_file)

            time.sleep(0.125)


if __name__ == '__main__':
    up = UttProc()
    up.is_running = True
    up.run()

