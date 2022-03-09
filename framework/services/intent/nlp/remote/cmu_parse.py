import requests, sys

"""
If input is given that file is used as the source
of sentences otherwise the file sentences.txt is used.

This script will convert input file into a python
file which contains the mappings of shallow grammar
rules to utterance handlers.

The file named cmu_trees.txt is overwritten by this script.
"""

API_ENDPOINT = "https://www.link.cs.cmu.edu/cgi-bin/link/construct-page-4.cgi#submit"

def remote_get_tree(sentence):
    data = {'Sentence':sentence,
        'Constituents':'on',
        'NullLinks':'on',
        'LinkDisplay':'on',
        'ShortLength':'6',
        'PageFile':'/docs/submit-sentence-4.html',
        'InputFile':'/scripts/input-to-parser',
        'Maintainer':'sleator@cs.cmu.edu'}
  
    r = requests.post(url = API_ENDPOINT, data = data)
    start = r.text.find("Constituent tree:") + len("Constituent tree:")
    end = r.text.find("</pre>", start)

    snip = r.text[start:end].replace("\n","")
    snip = ' '.join(snip.split())
    return snip[3:-1]


if __name__ == "__main__":
    input_filename = "sentences.txt"
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]

    fh = open(input_filename)
    flines = fh.readlines()
    fh.close()
    sentences = []
    for sentence in flines:
      sentences.append(sentence.strip())

    fh = open("cmu_trees.txt","w")

    for sentence in sentences:
        if sentence.startswith("#") or len(sentence) < 5:
            pass
        else:
            print(sentence)
            sentence = sentence.replace(" ","+")
            snip = get_tree(sentence)
            print(snip)
            print()
            fh.write(snip + "\n")

    fh.close()
    print("Created file cmu_trees.txt")

