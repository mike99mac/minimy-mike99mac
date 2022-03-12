from threading import Event
from skills.sva_base import SimpleVoiceAssistant
from bus.Message import Message
from bus.MsgBusClient import MsgBusClient
from framework.message_types import MSG_SKILL
from framework.util.utils import aplay, Config

class FallbackSkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        super().__init__(msg_handler=self.handle_message, skill_id='fallback_skill', skill_category='fallback')

        # array of registered qna skill handlers
        self.qna_skills = []
        cfg = Config()
        base_dir = cfg.get_cfg_val('Basic.BaseDir')
        self.boing_filename = base_dir + '/framework/assets/boing.wav'


    def handle_register_qna(self,msg):
        data = msg.data
        skill_id = data['qna_skill_id']
        self.log.info("[%s] Registered as a Q&A skill" % (skill_id,))
        if skill_id not in self.qna_skills:
            self.qna_skills.append(skill_id)


    def handle_qna_response(self,msg):
        # gather responses and decide who to handle the question
        # then send message to that skill_id to play the answer
        # if error play default fail earcon.

        message = {'subtype':'qna_answer_question', 
                'skill_id':msg.data['from_skill_id'], 
                'skill_data':msg.data['skill_data']}
        # for now assume the only skill to answer gets it
        self.send_message(msg.data['from_skill_id'], message)


    def handle_message(self,msg):
        if msg.data['subtype'] == 'qna_register_request':
            return self.handle_register_qna(msg)

        if msg.data['subtype'] == 'qna_confidence_response':
            return self.handle_qna_response(msg)

    def handle_fallback(self,msg):
        self.log.debug("FBS: handle_fallback() hit!")
        # for questions only right now
        data = msg.data['utt']

        if data['sentence_type'] == 'Q':
            # send out message to all Q&A skills
            # saying you got 3 seconds to give me 
            # your confidence level. all Q&A skills
            # need to respond to the 'get_confidence'
            # message and the 'play_qna_answer' message
            for skill_id in self.qna_skills:
                # send 'q' getconf qna
                # 'Q', 'getconf', 'qna',
                self.log.debug("FBS: sending qna_get_confidence to %s" % (skill_id,))
                info = {
                    'subtype': 'qna_get_confidence',
                    'skill_id': skill_id,
                    'sentence_type': 'Q',
                    'qword': 'getconf',
                    'np': 'qna',
                    'intent_match': 'Q:getconf:qna',
                    'msg_np':data['np'],
                    'msg_vp':data['vp'],
                    'msg_aux':data['aux_verb'],
                    'msg_qword':data['qword'],
                    'msg_rule':data['rule'],
                    'msg_tree':data['tree'],
                    'msg_sentence':data['sentence']
                    }
                self.bus.send(MSG_SKILL, skill_id, info)
        else:
            self.log.info("** Fallback Skill only handles sentences of type Question for now!, Utterance ignored! **")

            message = {'subtype':'unrecognized_utterance', 
                    'skill_id':'system_monitor_skill', 
                'skill_data':data}
            self.send_message('system_monitor_skill', message)
            #aplay(self.boing_filename)

            # TODO send message to monitor skill
            # lol, while this seems like a good idea, on systems 
            # with poor aec this can cause an infinite feedback loop 
            #self.speak("Sorry I do not understand %s" % (data['sentence'],))


if __name__ == '__main__':
    fs = FallbackSkill()
    Event().wait()  # Wait forever

