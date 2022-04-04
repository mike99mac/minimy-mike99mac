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
        SBAR_TAG,
        )
# question_types 
QTYPE_YESNO = 'qt_yes_no'
QTYPE_COMPARE = 'qt_compare'
QTYPE_WH = 'qt_wh'
QTYPE_TAG = 'qt_tag'
QTYPE_MISSING_CONTEXT = 'qt_missing_context'
QTYPE_UNKNOWN = 'qt_unknown'

# these are mainly used to clean up noun phrases
# when attempting to convert them to subjects
determiners = [' a ', ' any ', ' the ', ' this ', ' that ', 
        ' these ', ' those ', ' my ', ' your ', ' his ', 
        ' her ', ' its ', ' our ', ' their ', ' few ',
        ' little ', ' much ', ' many ', ' a lot of ', 
        ' most ', ' some ', ' any ', ' enough ',
        ' all ', ' both ', ' half ', ' either ', 
        ' neither ', ' each ', ' every ', ' other ', 
        ' another ', ' such ', ' what ', ' rather ', ' quite '
        ]
chatter = [' is ', ' not ', ' are ', ' of ', ' the ', 
        ' in ', ' an ', ' that ', ' which ', ' there', 
        ' for ', ' a ', ' it ', ' on ', ' off ']
# don't lose site that the larger goal is intent matching!
# Note - this is an extremely abbreviated solution. the correct
# solution is to pattern match like commands do but I do not
# have that much time right now.
# notes
# 1) "is it raining" implies weather
#    since the larger goal is intent matching
#    we need to make sure we can get this
#    question to the right handler
#
# 2) you can cheat since you know all the verbs 
#    contained in your intents and you also know all 
#    the subjects you could intent match against. 
#    BUT as (1) demonstrates, don't get too cute.
# 
# it would also be nice to detect the word 'it' in
# sentences and replace it with what it actually 
# refers to so 'is it colder in texas or arizona' 
# after noise removal is colder texas arizona and
# it refers to colder.
# 
def whack_tags(tree):
  # remove tag related artifacts from a string
  tags = (
      S_TAG,
      VP_TAG,
      NP_TAG,
      PP_TAG,
      PRT_TAG,
      ADVP_TAG,
      ADJP_TAG,
      SBAR_TAG,
      )
  for tag in tags:
      tree = tree.replace(tag,"")
  tree = tree.replace("(","")
  tree = tree.replace(")","")
  tree = tree.replace("  "," ")
  return tree.strip()


def extract_phrase(phrase, tree):
  # return first phrase found in tree
  strt = tree.find(phrase)
  if strt == -1:
      # if no phrase
      return ''

  tree = tree[strt+len(phrase):]
  ctr = 1
  max_len = 250
  indx = 0
  while ctr > 0 and indx < max_len and indx < len(tree):
    if tree[indx] == '(':
      ctr += 1
    if tree[indx] == ')':
      ctr -= 1
    indx += 1

  return tree[0:indx-1]


def np_to_subject(np):
  # the subject is the noun phrase with all noise removed
  # TODO this is where you can pick up addtl info like
  # negation (the word not preceedes a VP), determiners
  # to establish tense and plurality, etc
  subject = ' ' + np + ' '
  for chat in chatter:
    subject = subject.replace(chat,' ')
  for det in determiners:
    subject = subject.replace(det,' ')
  subject = subject.replace("  ", " ")
  return subject.strip()


def brute_subject_match(sentence,subjects):
  # old regex type brute force match 
  # mainly used for verification and
  # a last resort
  for subject in subjects:
    if sentence.find(subject) > -1:
      return subject
  return ''

def np_in_vp(np,vp):
  if vp.find(np) > -1:
    return True
  return False

def handle_wh_type(info, question):
  info['qtype'] = QTYPE_WH
  tree = info['tree']
  np = extract_phrase(NP_TAG, tree)

  # if np is 'it', keep looking
  if np == 'it':
    #print("Indirect np being tracked")
    sa = tree.split(" ")
    np = sa[1]

  vp = extract_phrase(VP_TAG, tree)
  val = extract_phrase(PRT_TAG, tree)
  #print("WH: NP:%s, VP:%s, VAL:%s" % (np,vp,val))
  info['np'] = np
  info['vp'] = vp
  info['aux_verb'] = val
  info['val'] = val
  np_not_handled = True

  #print("Rule:%s, Tree:%s" % (info['rule'], tree))

  # TODO i hate doing this here but for now
  # eventually handle like commands with branch table

  if info['rule'] == 'VP NP PP NP':
    np_not_handled = False
    np = handle_pp_in_np(vp)

  elif info['rule'] == 'NP NP NP VP PP':
    np_not_handled = False
    np = tree.replace(vp,'')

  elif info['rule'] == 'NP PP NP NP VP PP':
    np_not_handled = False
    np = tree.replace(vp,'')
    np = handle_pp_in_np(np)

  else:
    if tree.find(PP_TAG) > -1:
      #print("PP not handled properly. this will not go well")
      pass

  subject = whack_tags(np)
  subject = np_to_subject(subject)
  subject = subject.lower()
  info['subject'] = subject

  return info


def is_comparison(question):
  if question.find(" than ") > -1 or question.find(" or ") > -1:
    return True
  return False


def handle_comparison_type(info, question):
  #print("Parse comparison TBD")
  tree = info['tree']
  info['qtype'] = QTYPE_COMPARE
  info['qword'] = 'tbd'
  info['tense'] = 'tbd'
  info['aux_verb'] = 'tbd'
  return info


def handle_pp_in_np(np):
    # we have a propositional phrase in our noun 
    # phrase. reverse the elements if more than one
    strt = np.find('(')
    np = np[strt:]
    np1 = extract_phrase(NP_TAG, np)
    np2 = extract_phrase(NP_TAG, np[len(np1):])
    if not (np1 and np2):
      np = np[1:]
      np1 = extract_phrase(NP_TAG, np)
      np2 = extract_phrase(NP_TAG, np[len(np1):])

    np = np2.replace('the ','') + ' ' +  np1.replace('the ','')

    return np


def handle_yesno_type(info, sentence):
  info['qtype'] = QTYPE_YESNO
  sa = sentence.split(" ")
  info['qword'] = sa[0]
  tree = info['tree']
  tree = tree[len(info['qword'])+1:]
  vp = extract_phrase(VP_TAG, tree)
  vp = VP_TAG + vp + ')'
  val = extract_phrase(PRT_TAG, tree)
  prt = PRT_TAG + val + ')'

  np = tree.replace(vp, "")
  np = np.replace(prt, "")

  if np.find(PP_TAG) > -1:
    np = handle_pp_in_np(np)

  np = whack_tags(np)
  np = np_to_subject(np)
  np = np.lower()

  subject = whack_tags(np_to_subject(np))
  info['np'] = np
  info['vp'] = vp
  info['subject'] = subject
  info['aux_verb'] = val
  info['val'] = val
  if val == '':
    info['val'] = extract_phrase(ADJP_TAG, tree)
    info['aux_verb'] = info['val']
  return info

def resort_to_pattern_matching(info):
  sentence = info['sentence']
  rule = info['rule']
  if rule == "VP NP" or rule == "VP PP":
    sa = sentence.split(" ")
    return sa[1]

  if rule == "VP ADJP":
    sa = sentence.split(" ")
    return sa[len(sa)-1]

 
def parse_question(sentence, use_remote):
  # note sensor comes before sensors!
  subjects = ['sensors', 'sensor', 'living room light', 'light one', 'hall light']
  info = _parse_question(sentence, use_remote)
  sub1 = info['subject']
  sub2 = brute_subject_match(sentence, subjects)
  if sub1 == '':
    sub1 = sub2
  info['subject'] = sub1

  if info['subject'] == '':
    # emergency measures are needed :-)
    info['subject'] = resort_to_pattern_matching(info)


  return info

def _parse_question(sentence, use_remote):
  # takes in a sentence, returns a data structure
  # representing what the system thinks was 
  # communicated. a lot of different values are
  # returned but what's important from an intent 
  # perspective is the qword is the verb and the 
  # subject is the intent subject.
  #
  # Note tag questions are currently unsupported.
  # Examples of tag questions:
  #   that car was built last year, wasn't it
  #   it is hot today, isn't it
  #   we don't support tag questions, do we
  #   but we could by probably dropping the last
  #   word and pre-pending the next to last word 
  #   to the sentence.
  # 
  # TODO missing preprocess phase like expand 
  # isn't to is not, USA to united states, etc
  # but maybe that should be done higher up anyway
  original_sentence = sentence
  sentence = sentence.replace("'s", " is")

  # this may be a bad idea but 'currently' and 'now' are 
  # nothing more than tense indicators to me
  sentence = sentence.replace("currently ", "")
  sentence = sentence.replace(" currently", "")
  sentence = sentence.replace("now ", "")
  sentence = sentence.replace(" now ", "")

  # this is what is returned by this method/process.
  np = ''
  vp = ''
  tense = 'present'
  plural = 'false'
  qword = ''
  qtype = ''
  topic = ''
  location = ''
  subject = ''
  aux_verb = ''
  tree = ''
  parse_err = ''

  if use_remote:
    tree = remote_get_tree(sentence.replace(" ", "+"))
  else:
    tree = local_get_tree(sentence)

  original_tree = tree
  rule = get_shallow_rule_from_tree(tree).strip()

  sa = sentence.split(" ")
  qword = sa[0]

  # defaults 
  info = {
          'error':parse_err,
          'sentence':original_sentence,
          'qtype':qtype, 
          'pp':qtype, 
          'tense':tense, 
          'plural':plural, 
          'tree':original_tree, 
          'rule':rule, 
          'qword':qword, 
          'aux_verb':aux_verb, 
          'val':aux_verb, 
          'topic':topic, 
          'location':location, 
          'subject':subject, 
          'np':np, 
          'vp':vp
         }
  # questions are typically yes/no, but can also be
  # open ended or comparisons. open ended could be
  # further subdivided but we don't do it. 
  wh_words=['who', 'what', 'where', 'when', 'how', 'why']
  not_sure_what_to_do_with_yet = ['do', 'does', 'did', 'will', 'which', 'would', 'are', 'can']
  question = sentence

  # handle comparison type questions
  if is_comparison(question):
    return handle_comparison_type(info, question)

  else:
    sa = sentence.split(" ")
    if sa[0] in wh_words:
      return handle_wh_type(info, question)

    else:
      return handle_yesno_type(info, question)

