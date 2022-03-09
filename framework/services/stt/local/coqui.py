from subprocess import Popen, PIPE, STDOUT

def execute_command(command):
    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
    stdout, stderr = p.communicate()
    stdout = str( stdout.decode('utf-8') )
    stderr = str( stderr.decode('utf-8') )
    return stdout, stderr

def local_transcribe_file(wav_filename):
    cmd = 'curl http://localhost:5002/stt -H "Content-Type: audio/wav" --data-binary @"%s"' % (wav_filename,)
    out, err = execute_command(cmd)
    return out.strip()

