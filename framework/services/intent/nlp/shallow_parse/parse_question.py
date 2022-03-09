from framework.services.intent.nlp.remote.cmu_parse import remote_get_tree
from framework.services.intent.nlp.local.parse_interface import local_get_tree
from .produce_rules import get_shallow_rule_from_tree
from .shallow_utils import (
        get_tag_value, 
        get_node, 
        scrub_node, 
        S_TAG,
        VP_TAG,
        NP_TAG,
        PP_TAG,
        PRT_TAG,
        ADVP_TAG,
        ADJP_TAG,
        )


# don't lose site that the larger goal is intent matching!
#
# notes
# 1) "is it raining" implies weather
#
# 2) you can cheat since you know all the verbs 
# contained in your intents and you also know all 
# the subjects you could intent match against. 
# BUT as (1) demonstrates, don't get too cute.

wh_style = ['who', 'what', 'where', 'when', 'how', 'why']

def parse_question(sentence, use_remote):
 # 1) yes/no questions
  # aux verb, subject, main verb, other
  # Do you, does he, can their, etc
  # Examples of yes/no questions:
  #  Is your mom from Germany
  #  Am I OK
  #
  # exceptions:
  #   if main verb of the sentence is of the
  #   form 'to be' it goes in the aux position.
  #
  # 2) wh questions
  # wh, aux verb, subject, main verb, other
  # Examples of 'wh' questions:
  #   where is carmen san diego
  #   what did Bob say
  #
  # 3) tag questions
  # currently unsupported
  # Examples of tag questions:
  #   that car was built last year, wasn't it
  #   it is hot today, isn't it
  #   we don't support tag questions, do we
  #
  #print("Warning, exceptions not handled yet and tag questions not removed!")
  original_sentence = sentence
  sentence = sentence.replace("'s", " is")
  tense = 'present'
  plural = 'false'
  qword = ''
  aux_verb = ''

  tree = ''
  if use_remote:
    tree = remote_get_tree(sentence.replace(" ", "+"))
  else:
    tree = local_get_tree(sentence)

  original_tree = tree
  rule = get_shallow_rule_from_tree(tree).strip()

  sa = sentence.split(" ")
  qword = sa[0]

  is_complex = False
  if tree.find("(S ",3) > -1:
    #print("Processing Question Type = COMPLEX")
    is_complex = True
    #qword = get_tag_value(S_TAG, tree)
    aux_verb = get_tag_value(VP_TAG, tree)

  else:
    #print("Processing Question Type = WH")
    if qword in wh_style:
      # if wh type question remove the wh
      wh_and_aux = get_tag_value(S_TAG,tree)
      tree = tree[3:-1]
      tree = tree.replace(wh_and_aux,'').strip()
      sa = wh_and_aux.split(" ")
      aux_verb = ''
      if len(sa) > 1:
          aux_verb = sa[1]


  #print("Processing Question Type = YES/NO")
  # fall thru to here and continue with 
  # np vp extraction
  np_node = get_node(NP_TAG, tree)
  vp_node = get_node(VP_TAG, tree)

  # if we don't have an aux_verb, then 
  # the vp is the aux_verb
  if aux_verb == '':
    aux_verb = get_tag_value(VP_TAG, tree)

  if is_complex:
    vp_node = vp_node.replace(np_node,'')
    vp_node = vp_node.replace(" )", ")")

  # at this point I think it is safe to
  # clean and flatten our NP and VP
  np = scrub_node(np_node)
  vp = scrub_node(vp_node)


  # one last thing - if our NP is 'it',
  # maybe our np is our aux verb 
  if np == 'it':
      np = aux_verb
   
  return {
        'error':'',
        'sentence':original_sentence,
        'tense':tense, 
        'plural':plural, 
        'tree':original_tree, 
        'rule':rule, 
        'qword':qword, 
        'aux_verb':aux_verb, 
        'np':np, 
        'vp':vp
        }

