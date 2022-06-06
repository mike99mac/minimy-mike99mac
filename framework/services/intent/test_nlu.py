import os
from framework.services.intent.nlp.shallow_parse.nlu import SentenceInfo

if __name__ == '__main__':
    utterances = [
            #"Is it warm outside",
            #"Play it never rains in southern california",
            #"Listen to ninety eight point seven the gator please",
            #"Stop timer",
            #"Stop",
            #"Terminate",
            "Do I have any active alarms",
            "Are there any active alarms",
            "Are there currently any active alarms",
            "Are any alarms currently active",
            "Are there any doors open",
            "Is the front door open",
            "What time is it",
            #"How tall is the Eiffel Tower",
            #"How long does it take to play a game of cricket",
            #"Where is the Eiffel Tower located",
            #"Which is further away Jupiter or Mars",
            "Is the light in the living room on",
            "What is the temperature in the living room",
            "What is the living room temperature",
            "What is the temperature outside",
            "What is the current temperature in Boise Idaho",
            "What is thermostat seven set to",
            "How hot does it get in Boise Idaho",
            "What time is it",
            "What day is today",
            "What is today's date",
            "Is today friday",
            #"Turn the living room light on",
            #"Turn on the living room light",
            #"Turn on the light in the living room",
            #"Turn the light in the living room on",
            ]

    base_dir = os.getenv('SVA_BASE_DIR')
    si = SentenceInfo(base_dir)

    for utt in utterances:
        si.parse_utterance(utt)
        print("utt = %s" % (utt,))
        print("sentence type = %s" % (si.sentence_type,))
        print("qtype:%s" % (si.insight.qtype,))
        print("tree = %s" % (si.structure.tree,))
        print("shallow = %s" % (si.structure.shallow,))
        print("nodes: (%s)" % (len(si.structure.nodes),))
        for node in si.structure.nodes:
            print("    %s" % (node,))
        print("proper nouns = %s" % (si.insight.proper_nouns,))
        print("subject:%s" % (si.insight.subject,))
        print("verb:%s" % (si.insight.verb,))
        print("question:%s" % (si.insight.question,))
        print("aux:%s" % (si.insight.aux_verb,))
        print("value:%s" % (si.insight.value,))
        print("Key:%s:%s:%s" % (si.sentence_type, si.insight.question.lower(), si.insight.subject.lower()))
        print("----------------------------------------")

