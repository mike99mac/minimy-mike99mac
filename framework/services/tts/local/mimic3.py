from framework.util.utils import execute_command

def local_speak_dialog(text, filename, wait_q):
    status = 'fail'
    command = "curl -sS -X GET -G --data-urlencode \"INPUT_TEXT=%s\" --data-urlencode \"INPUT_TYPE=TEXT\" --data-urlencode \"OUTPUT_TYPE=AUDIO\" --data-urlencode \"AUDIO=WAVE\" \"localhost:59125/process\" --output - > %s" % (text, filename)
    try:
        res = execute_command(command)
        if res.find("200 OK") > -1:
            status = 'success'
    except:
        pass
    wait_q.put({'service':'local', 'status':status})
