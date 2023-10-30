import os

def local_speak_dialog(text, filename, wait_q):
    cmd = "echo '%s!' | ./piper --model en_US-lessac-medium.onnx --output_file speech.wav;aplay speech.wav" % (text,)
    os.system(cmd)
    os.system("rm speech.wav")
    wait_q.put({'service':'local', 'status':'success'})
    