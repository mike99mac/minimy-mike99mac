import os, re, pty, time, json, datetime
from subprocess import Popen, PIPE, STDOUT
from lingua_franca.parse import extract_datetime
from lingua_franca.time import to_local
import lingua_franca
import logging
import yaml

# the larger the chunk size the less responsive the barge-in. the smaller
# the chunk size the more choppy the outout sounds. you pick your poison.
# MAX_CHUNK_LEN = 15
# MIN_CHUNK_LEN = 5
MAX_CHUNK_LEN = 45
MIN_CHUNK_LEN = 35

def get_hal_obj(which):
    jobj = ''
    fh = open("framework/hal/hal.cfg")
    for line in fh.readlines():
        if not line.startswith("#"):
            jobj += line.strip()
    fh.close()
    hal_obj = json.loads(jobj)
    if hal_obj is None:
        return hal_obj
    return hal_obj.get(which,None)

class Config:
    # minimal yaml based config file support class - must coordinate this with mmconfig.py
    config_defaults = [
        {
        'Basic': {
            'Version':'1.0.4',
            'BaseDir':'',
            'WakeWords': ['hey computer', 'computer'],
            'GoogleApiKeyPath' : 'install/my_google_key.json',
            'AWSId': '',
            'AWSKey': ''
            },
        'Advanced': {
            'Platform': 'l',
            'LogLevel': 'i',
            'CrappyAEC': 'n',
            'InputDeviceId': '0',
            'OutputDeviceName': '',
            'InputLevelControlName': '',
            'OutputLevelControlName': '',
            'ButtonsType': '3',
            'STT' : {
                     'UseRemote': 'y'
                    },
            'TTS' : {
                     'UseRemote': 'y',
                     'Local': 'm',
                     'Remote': 'p'
                    },
            'NLP' : {
                     'UseRemote': 'n'
                    },
            }
        }
    ]

    def __init__(self):
        base_dir = os.getenv('SVA_BASE_DIR')
        if base_dir is None:
            base_dir = os.getcwd()
            print("Warning, SVA_BASE_DIR environment variable is not set. Defaulting it to %s" % (base_dir,))
        self.config_file = base_dir + '/install/mmconfig.yml'
        self.cfg = None                    # if not exists create
        try:
            self.cfg = self.load_cfg()
        except:
            pass
        if self.cfg is None:
            #print("Warning, install/mmconfig.yml not found, creating one!\n")
            self.reset_config()
        self.set_cfg_val('Basic.BaseDir', base_dir)

    def load_cfg(self):
        with open(self.config_file, "r") as ymlfile:
            return yaml.safe_load(ymlfile)

    def save_cfg(self):
        with open(self.config_file, 'w') as yamlfile:
            data = yaml.dump(self.cfg, yamlfile)

    def reset_config(self):
        self.cfg = self.config_defaults
        self.save_cfg()
        self.cfg = self.load_cfg()

    def get_cfg_val(self,key):
        ka = key.split(".")
        sect = self.cfg[0]
        for k in ka:
            try:
                sect = sect[k]
            except:
                return None
        return sect

    def set_cfg_val(self,key,value):
        ka = key.split(".")
        cmd = "self.cfg[0]"
        for k in ka:
            cmd = cmd + "['%s']" % (k,)
        if isinstance(value, str):
            cmd = cmd + " = '%s'" % (value,)
        else:
            cmd = cmd + " = %s" % (value,)
        exec(cmd)

    def dump_cfg(self):
        tmp_cfg = self.cfg[0]
        for section in tmp_cfg.keys():
            print("  %s" % (section,))
            for item in (tmp_cfg[section]).items():
                print("    %s" % (item,))

class LOG:
    def __init__(self, filename):
        log_level = logging.ERROR
        cfg = Config()
        #cfg_log_level = cfg.get_cfg_val('log_level')
        cfg_log_level = cfg.get_cfg_val('Advanced.LogLevel')

        if cfg_log_level == 'w':
            log_level = logging.WARNING
        if cfg_log_level == 'i':
            log_level = logging.INFO
        if cfg_log_level == 'd':
            log_level = logging.DEBUG
        
        logging.basicConfig(filename=filename,
                format='[%(asctime)s  %(levelname)s] %(message)s',
                level=log_level)
        self.log = logging.getLogger()

class MediaSession:
    def __init__(self,session_id, owner):
        self.session_id = session_id
        self.owner = owner
        self.ce = None
        self.time_out_ctr = 0
        self.media_type = '' # wav or mp3
        self.media_queue = []
        self.state = 'idle'
        self.correlator = ''

def aplay(file):
    # one place where the raw aplay is used which uses proper device entry from
    # the config file. eventually belongs in a hal object
    cfg = Config()
    device_id = cfg.get_cfg_val('Advanced.OutputDeviceName')
    cmd = "aplay " + file
    if device_id is not None and device_id != '':
        cmd = "aplay -D" + device_id + " " + file
    os.system(cmd)

# for simple blocking operations
def execute_command(command):
    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
    stdout, stderr = p.communicate()
    stdout = str(stdout.decode('utf-8'))
    stderr = str(stderr.decode('utf-8'))
    return "STDOUT:" + stdout + "\nSTDERR:" + stderr

class CommandExecutor:
    """
    Support for old school type linux utilities like aplay and mpg123. Note, for async users,
    mpg123 should be terminated using send('s') while aplay requires kill(). Note also you
    can not currently read stdout using this method. 
    Synchronous Example:
      retcode = CommandExecutor('aplay -i test.wav').wait()
    Asynchronous Example:
      ce = CommandExecutor('aplay -i test.wav')
      ce.send(' ')  # pause aplay or send 's' to pause mpg123
      ce.kill()     # stop play or send 'q' to kill mpg123
    """
    def __init__(self, command):
        self.error = None
        self.proc = None
        self.master = None
        self.slave = None
        self.master, self.slave = os.openpty()
        try:
            self.proc = Popen(command.strip().split(" "), stdin=self.master)
        except Exception as e:
            self.error = e
        time.sleep(0.0625)                 # if you write too fast you hose the fd
    def send(self, text):
        os.write(self.slave, text.encode('utf-8'))

    def is_completed(self):
        # call this and when it returns true you can call get_return_code()
        try:
            if self.proc.poll() is None:
                return False
            else:
                return True
        except:
            return True

    def get_return_code(self):
        # if None, still alive 
        if self.proc is not None:
            return self.proc.returncode
        return self.proc

    def kill(self):
        self.proc.kill()
        os.close(self.slave)
        os.close(self.master)

    def wait(self):
        while not self.is_completed():
            time.sleep(1)
        return self.get_return_code()

# read two letter abbreviations to US states and vice-versa
base_dir = os.getenv('SVA_BASE_DIR')
abbrevs = ""
fh = open(f"{base_dir}/install/us_abbrev_to_state.json")
for line in fh.readlines():
    abbrevs += line.strip()
fh.close()
us_abbrev_to_state = json.loads(abbrevs)

abbrevs = ""
fh = open(f"{base_dir}/install/us_state_to_abbrev.json")
for line in fh.readlines():
    abbrevs += line.strip()
fh.close()
us_state_to_abbrev = json.loads(abbrevs)

def get_ampm(sentence):
    ampm = None
    if sentence.find("a m") > -1:
        sentence = sentence.replace("a m", "am")
    if sentence.find("p m") > -1:
        sentence = sentence.replace("p m", "pm")
    if sentence.find(" am") > -1:
        ampm = 'am'
    else:
        if sentence.find(" pm") > -1:
            ampm = 'pm'
    return ampm

def get_hour_min(qual):
    hour = 0
    minute = 0
    nums = re.findall(r'\d+',qual)
    if len(nums) > 1:                      # have a number, if we have two we have hour and minute otherwise we just have an hour.
        hour = nums[0]
        minute = nums[1]
    elif len(nums) > 0:
        hour = nums[0]
    else:
        #print("No time at all")
        pass
    print(f"get_hour_min() sentence: {sentence} hour: {hour} minute: {minute}")    
    return int(hour), int(minute)

def get_raw(sentence):
    print(f"get_raw() sentence: {sentence}")
    sentence = sentence.replace("a m", "")
    sentence = sentence.replace("p m", "")
    sentence = sentence.replace("am", "")
    sentence = sentence.replace("pm", "")
    sentence = sentence.strip()
    if sentence.find(":") > -1:
        sa = sentence.split(":")
        hour = sa[0]
        minute = sa[1]
    else:
        hour,minute = get_hour_min(sentence)
    print(f"get_raw()- hour: {hour} minute: {minute}, sentence: {sentence}")
    # TODO maybe - if we have time but no date assume today?
    return None, int(hour), int(minute)

def get_time_from_utterance(sentence):
    print(f"get_time_from_utt() sentence: {sentence}")
    lingua_franca.load_language('en')
    ampm = get_ampm(sentence)
    hour = 0
    minute = 0
    qual = ''
    have_date = False
    have_time = False
    if sentence.find("a m") > -1:
        sentence = sentence.replace("a m", "am")
    if sentence.find("p m") > -1:
        sentence = sentence.replace("p m", "pm")
    now = datetime.datetime.now()
    now = to_local(now)
    dt = extract_datetime(sentence, now)
    if dt is not None:                     # lingua franca handled it
        have_date = True
        qual = dt[1]
        dt = dt[0]
        if dt.hour == 0 and dt.minute == 0:   # if lf didn't get a time maybe we can get one
            hour, minute = get_hour_min(qual) # should probably use None so you can handle midnight!
            if hour != 0:                  # we got a time lf overlooked
                have_time = True
                # dt hour is in 24 hour format so we need to handle that. also note lf assumes utc
                # unless you overide it by passing in an anchorDate.
                if ampm is not None:
                    if ampm == 'pm':
                        hour += 12
                dt = dt.replace(hour=hour, minute=minute)
        else:
            have_time = True
    else:                                  # lingua franca can't help - last resort fall back
        dt, hour, minute  = get_raw(sentence)
    print(f"get_time_from_utt()- have_date: {have_date} have_time: {have_time} hour: {hour} minute: {minute}, dt: {dt} sentence: {sentence}")
    return have_date, have_time, hour, minute, dt

def get_wake_words():
    # if we find a wake_words.txt file we use that otherwise we default to these
    # note local stt works best with 'hello jarvis' or 'jarvis' and note capitalization
    wws = ['hey Jarvis', 'Jarvis', 'hey Bubba', 'Bubba']
    cfg = Config()
    cfg_wws = cfg.get_cfg_val('Basic.WakeWords')
    if cfg_wws is not None:
        wws = cfg_wws
        if isinstance(wws, str):
            wws = [wws,]
        indx = 0
        while indx < len(wws):
            wws[indx] = wws[indx].strip()
            indx += 1
    wws = sorted(wws, key=len, reverse=True)
    return wws

def make_time_speakable(text):
    text = text.replace("00","")
    words = text.split(" ")
    indx = 0
    while indx < len(words):
        # if words[indx].startswith('0'):
        #     words[indx] = words[indx][1:]
        #     break
        try:
            if int(words[indx]):
                break
        except:
            pass
        indx += 1
    text = " ".join(words)
    return text

def remove_pleasantries(sentence):
    pleasantries = ['please', 'o.k.', 'ok', 'thanks', 'thank you']
    altered = ''
    sentence = sentence.replace("?","")
    sentence = sentence.replace(".","")
    sentence = sentence.replace(",","")
    sentence = sentence.replace("!","")
    sa = sentence.split(" " )
    for s in sa:
        if not s.lower() in pleasantries:
            altered += s + ' '
    return altered.strip()

def expand_abbrevs(text):
    abbrevs = {
            "DC":"District of Columbia",
            "US":"United States",
            "USA":"United States of America",
            "UK":"United Kingdom",
            "UAE":"United Arab Emirates",
            "NRA":"National Rifle Association",
            "Mr":"Mister",
            "TV":"television",
            "IBM":"International Business Machines",
            }
    ta = text.split(" ")
    expanded_sentence = ''
    for t in ta:
        if t.replace('.','') in abbrevs:
            expanded_sentence += abbrevs[t.replace('.','')]
        else:
            expanded_sentence += t
        expanded_sentence += ' '
    return expanded_sentence.strip()

def normalize_sentence(sentence):
  sentence = sentence.replace("a.m.","am")
  sentence = sentence.replace("p.m.","pm")
  sentence = sentence.replace("a m","am")
  sentence = sentence.replace("p m","pm")
  sentence = sentence.replace("%"," percent")
  return sentence

def tts_scrub_output(text):
    # very tts specific - scrub output
    text = expand_abbrevs(text)
    text = re.sub('\-', '', text)
    text = re.sub(';', '', text)
    text = re.sub(':', ' ', text)
    text = re.sub('"', "'", text)
    text = re.sub('\(', '', text)
    text = re.sub('\)', '', text)
    text = re.sub('\[', '', text)
    text = re.sub('\]', '', text)
    text = re.sub('\{', '', text)
    text = re.sub('\}', '', text)
    text = re.sub('\<', '', text)
    text = re.sub('\>', '', text)
    text = re.sub('\=', 'equal', text)
    text = re.sub('  ', ' ', text)
    text = make_time_speakable(text)
    return text

def chunk_text(data):
    MAX_WRD_LEN = 12
    data = tts_scrub_output(data)
    paragraphs = []
    for line in data.split("\n"):
        if line.strip():
            paragraphs.append(line)
    sentences = []
    for para in paragraphs:
        # remove everything in parens
        para = re.sub(r'\([^)]*\)', '', para)
        para = expand_abbrevs(para)        # normalize common terms
        para = para.split(".")             # split on sentences
        for p in para:
            p = p.replace("  ", " ")
            p = p.lstrip().strip()
            if len(p) > 0:
                p += '.'
                wrds = p.split(" ")
                if len(wrds) > MAX_WRD_LEN:
                    half = int( len(wrds)/2 )
                    sentences.append( " ".join(wrds[:half]) )
                    sentences.append( " ".join(wrds[half:]) )
                else:
                    sentences.append(p)
    return sentences

if __name__ == '__main__':
    ## CommandExecutor tests
    # example sync 
    print("Start synchronous")
    retcode = CommandExecutor('aplay -i /home/ken/Desktop/lincoln.wav').wait()
    print("End", retcode)

    # example async
    print("Start asynchronous")
    ce = CommandExecutor("cvlc --global-key-play-pause='s' https://walmradio.com:8443/jazz")
    time.sleep(3)
    print("Pause")
    os.system("dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.vlc /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause")
    print("Paused ...")
    time.sleep(3)
    print("Resume")
    os.system("dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.vlc /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause")
    time.sleep(5)
    print("Kill")
    ce.kill()
    while not ce.is_completed():
        print("Waiting for process exit")
        time.sleep(1)
    print("End", ce.get_return_code())
    print("Start error")
    retcode = CommandExecutor('boo').wait()
    print("End", retcode)
