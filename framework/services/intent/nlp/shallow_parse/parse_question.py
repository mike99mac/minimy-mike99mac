from framework.services.intent.nlp.remote.cmu_parse import remote_get_tree
from framework.services.intent.nlp.local.parse_interface import local_get_tree
from .produce_rules import get_shallow_rule_from_tree
from .shallow_utils import (
        get_tag_value, 
        get_node, 
        get_nodes, 
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


def np_in_vp(np,vp):
  if vp.find(np) > -1:
    return True
  return False


def handle_wh_type(info, question):
  info['qtype'] = QTYPE_WH
  info['dependent'] = ''
  tree = info['tree']

  if info['rule'].find("PP") > -1:
    print("XXXXXXXXXXXXXXXXXXXXXXX Warning PP Not handled properly yet!")

  verb = get_tag_value(VP_TAG, tree)
  if verb == '':
    verb = get_tag_value(ADVP_TAG, tree)

  # extract qword and qaux then remove from tree
  qword, aux_verb = get_qw(tree)

  # get nodes from modified tree
  start = tree.find("(")
  tree = tree[start:]
  nodes = get_nodes(tree)
  #print(nodes)

  value = get_tag_value(PRT_TAG, tree)

  subject = get_subject(tree)
  subject = subject.strip()
  if subject == 'it' or subject == '':
    subject = aux_verb

  info['qword'] = qword
  info['aux_verb'] = aux_verb
  info['verb'] = verb
  info['subject'] = subject
  info['value'] = value
  return info


def get_subject(tree):
  subject = ''
  exit_flag = False
  while not exit_flag:
    # combine all NPs for now
    next_np = get_tag_value(NP_TAG, tree)
    if next_np:
      subject = subject + ' ' + next_np
      indx = tree.find("(NP ")
      tree = tree[indx + len(next_np) + len(NP_TAG) + 1:]
    else:
      exit_flag = True

  subject = subject.replace(NP_TAG,"")
  subject = subject.replace(" is","")
  subject = subject.replace(" it","")
  subject = subject.strip()
  if subject.startswith("the "):
    subject = subject[len("the "):]
  subject = np_to_subject(subject)

  return subject


def get_qw(tree):
  if tree.startswith(ADVP_TAG):
    # typically of the form
    # how {bla} {does|is|hot|long|etc} {something|it}
    # where aux is basically the question
    ta = tree.split(" ")
    qword = ta[1]
    qaux = ta[1]
    if len(ta) > 2:
      qaux = ta[2]
    return qword, qaux

  tree = tree
  tree = tree.replace("?","")
  tree = tree.replace(".","")
  tree = tree.replace("!","")
  start_index = tree.find("(")
  qa = tree[0:start_index].strip()
  qa = qa.split(" ")
  qword = qa[0]
  qaux = qa[0]
  if len(qa) > 1:
    qaux = qa[1]
  else:
    qaux = get_tag_value(VP_TAG, tree)

  if qword == '' and qaux == '':
    # probably starts with an adverbial phrase
    qa = tree.split(" ")
    qword = qa[1]
    qaux = qa[2]

  return qword, qaux


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

  node = get_node(ADJP_TAG, np)
  np = np.replace(node,"")
  np = whack_tags(np)
  np = np_to_subject(np)
  np = np.lower()

  subject = whack_tags(np_to_subject(np))

  if subject == '':
    subject = extract_phrase(VP_TAG, tree)

  if val == '':
    val = extract_phrase(PP_TAG, tree)

  if val == '':
    val = extract_phrase(PRT_TAG, tree)

  info['np'] = np
  info['vp'] = whack_tags(vp)
  info['subject'] = subject
  info['aux_verb'] = val
  info['val'] = val
  if val == '':
    info['val'] = extract_phrase(ADJP_TAG, tree)
    info['aux_verb'] = info['val']
  return info


def parse_question(tree, rule, sentence, use_remote):
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
  original_sentence = sentence
  sentence = sentence.replace("'s", " is")
  tree = tree.replace("'s", " is")

  # this may be a bad idea but 'currently' and 'now' are 
  # nothing more than tense indicators to me
  sentence = sentence.replace("currently ", "")
  sentence = sentence.replace(" currently", "")
  sentence = sentence.replace("now ", "")
  sentence = sentence.replace(" now ", "")

  tree = tree.replace("currently ", "")
  tree = tree.replace(" currently", "")
  tree = tree.replace("now ", "")
  tree = tree.replace(" now", "")

  # this is what is returned by this method/process.
  np = ''
  vp = ''
  tense = 'present'
  plural = 'false'
  qword = ''
  qtype = ''
  verb = ''
  topic = ''
  location = ''
  subject = ''
  aux_verb = ''
  parse_err = ''
  original_tree = tree
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
          'verb':verb, 
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
  not_sure_what_to_do_with_yet = ['do', 'does', 'did', 'will', 'which', 'would', 'are', 'can', 'is']
  question = sentence

  # handle comparison type questions
  if is_comparison(question):
    return handle_comparison_type(info, question)

  else:

    sa = sentence.split(" ")

    if sa[0].lower() in wh_words:
      return handle_wh_type(info, question)

    else:
      return handle_yesno_type(info, question)

