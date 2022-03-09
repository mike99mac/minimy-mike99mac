import time
from framework.services.intent.nlp.remote.cmu_parse import remote_get_tree
from framework.services.intent.nlp.local.parse_interface import local_get_tree
from .produce_rules import get_shallow_rule_from_tree
from .command_rule_handlers import rule_map as command_rule_map
from .shallow_utils import get_tag_value, get_node, scrub_node, VP_TAG

media_verbs = ['play', 'watch', 'listen']

def handle_unknown_grammar(sentence, parse_tree, sentence_structure):
    return {'error':'Unrecognized grammar', 'sentence_type':'U', 'structure':sentence_structure, 'tree':parse_tree, 'sentence':sentence}

def parse_sentence(sentence, use_remote):
    # minor preprocessing
    sentence = sentence.replace("a m","am")
    sentence = sentence.replace("p m","pm")

    parse_tree = ''
    if use_remote:
         parse_tree = remote_get_tree(sentence)
    else:
         parse_tree = local_get_tree(sentence)

    sentence_structure = get_shallow_rule_from_tree(parse_tree).strip()
    save_struct = sentence_structure

    if sentence_structure == "VP" or (sentence_structure == "" and len(sentence.split(" ")) == 1):
        # fix this ugliness
        tmp_tree = parse_tree.replace("(VP ","")
        tmp_tree = tmp_tree.replace("(S ","")
        tmp_tree = tmp_tree.replace(")","")
        tmp_tree = tmp_tree.replace("  "," ")
        tmp_tree = tmp_tree.strip()
        info = {
                'error':'',
                'sentence_type':'system',
                'verb':tmp_tree,
                'structure':sentence_structure,
                'tree':parse_tree,
                'subject':'',
                'sentence':sentence,
                }
        #print("parse_sentence():Could be an OOB verb %s" % (tmp_tree,))
        sa = tmp_tree.split(" ")
        if len(sa) > 1:
            # if we end up with a single word we send it to 
            # the system skill, otherwise we convert it
            # to verb subject recognized
            info['sentence_type'] = 'I'
            info['verb'] = sa[0]
            info['subject'] = sa[1]
        return info

    start_verb = get_tag_value(VP_TAG, parse_tree).lower()
    #if parse_tree.startswith("(VP play") or parse_tree.startswith("(VP listen") or parse_tree.startswith("(VP watch"):
    if parse_tree.startswith("(VP ") and start_verb in media_verbs:
        return {'error':'media', 
                'sentence_type':'media', 
                'structure':sentence_structure, 
                'tree':parse_tree, 
                'sentence':sentence}

    elif sentence_structure.startswith("VP "):
        # assume its a command
        if sentence_structure not in command_rule_map:
            return handle_unknown_grammar(sentence, parse_tree, sentence_structure)

    else:
        # probably a question but could be of the form 'will you please do bla'
        if sentence_structure.startswith("NP "):
            # I suspect its of the form 'could you or will you do something'
            start_indx = parse_tree.find("(VP ")
            parse_tree = parse_tree[start_indx:]
            np = get_node("(NP ", parse_tree)
            # remove the NP from shallow rule
            sentence_structure = sentence_structure[3:]
            print("question converted to command. new rule:%s, new tree:%s " % (sentence_structure,parse_tree))

    if sentence_structure in command_rule_map:
        info = (command_rule_map[sentence_structure](parse_tree))
        info['tree'] = parse_tree
        info['structure'] = save_struct
        info['sentence_type'] = 'I'
        return info
    else:
        return handle_unknown_grammar(sentence, parse_tree, sentence_structure)

if __name__ == "__main__":
    pass

