import os

def local_speak_dialog(text, filename, wait_q):
    cmd = "espeak \"%s\" -w %s -p3 -s170 -ven-gb -k10" % (text, filename)
    os.system(cmd)
    wait_q.put({'service':'local', 'status':'success'})

