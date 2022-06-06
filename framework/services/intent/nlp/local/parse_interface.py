from subprocess import Popen, PIPE, STDOUT

import os

def local_get_tree(sentence):
    p = Popen(['framework/services/intent/nlp/local/link-4.1b/parse', 'framework/services/intent/nlp/local/link-4.1b/data/4.0.dict', '-pp', 'framework/services/intent/nlp/local/link-4.1b/data/4.0.knowledge', '-c', 'framework/services/intent/nlp/local/link-4.1b/data/4.0.constituent-knowledge', '-a', 'framework/services/intent/nlp/local/link-4.1b/data/4.0.affix'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)    

    std_input = "!constituents=1\n%s\n" % (sentence,)
    std_input = str.encode(std_input)
    stdout = p.communicate(input=std_input)[0]
    result = stdout.decode()
    # (S marks start of tree, first blank line is the end
    ra = result.split("\n")
    started = False
    res = []
    for r in ra:
        if started:
            if len(r.strip()) == 0:
                #print("end")
                break
            else:
                res.append(r)

        if r.startswith("(S "):
            #print("start")
            started = True
            res.append(r)

    res = " ".join(res)
    res = res.replace("\n","")
    res = ' '.join(res.split())
    #return res[3:-1]
    # be careful with backward compatability
    return res

