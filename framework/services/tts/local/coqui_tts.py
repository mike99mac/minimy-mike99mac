from framework.util.utils import execute_command

def local_speak_dialog(text, filename, wait_q):
    # Note - currently unsupported. it was hanging my system
    # on some requests
    command = "tts --text \"%s\" --model_name tts_models/en/ljspeech/tacotron2-DDC_ph --out_path %s" % (text, filename)
    self.log.error("COQUI ASKED to execute %s" % (command,))
    #res = execute_command(command)
    #wait_q.put({'service':'local', 'status':'success'})
    wait_q.put({'service':'local', 'status':'failure'})

