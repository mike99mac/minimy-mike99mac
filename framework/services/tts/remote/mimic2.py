import urllib3
from framework.util.utils import execute_command

class remote_tts:
    def __init__(self):
        pass

    def remote_speak(self, text, filename, wait_q):
        status = 'fail'
        text = urllib3.request.urlencode( {"text" : text} )
        command = "wget -O%s https://mimic-api.mycroft.ai/synthesize?%s" % (filename, text)
        try:
            res = execute_command(command)
            if res.find("200 OK") > -1:
                status = 'success'
        except:
            pass
        wait_q.put({'service':'remote', 'status':status})

