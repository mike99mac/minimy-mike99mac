S_TAG = "(S "
VP_TAG = "(VP "
NP_TAG = "(NP "
PP_TAG = "(PP "
PRT_TAG = "(PRT "
ADVP_TAG = "(ADVP "
ADJP_TAG = "(ADJP "
SBAR_TAG = "(SBAR "

def get_node(node_tag, tree):
  # one of the few pieces of code that could
  # probably have its performance improved
  # by using a regular expression.
  start_indx = tree.find(node_tag)
  if start_indx == -1:
    return ''

  paren_ctr = 1
  node = '('
  for c in tree[start_indx+1:]:
    node += c
    if c == '(':
      paren_ctr += 1

    if c == ')':
      paren_ctr -= 1
      if paren_ctr == 0:
        return node

  print('node parse error', paren_ctr)
  return node

def get_tag_value(tag, node):
  s1 = node.find(tag)

  if s1 == -1:
    return ''

  s = s1 + len(tag)

  e1 = node.find(")", s+1)
  e2 = node.find("(", s+1)
  e = e1
  if e == -1:
    e = e2

  if s1 == -1 and e1 == -1 and e2 == -1:
      return ''

  if e1 > -1 and e2 > -1:
      e = min(e1,e2)

  return node[s:e].strip()

def scrub_node(node):
  node = node.replace(VP_TAG,'')
  node = node.replace(NP_TAG,'')
  node = node.replace(PP_TAG,'')
  node = node.replace(PRT_TAG,'')
  node = node.replace(ADVP_TAG,'')
  node = node.replace(ADJP_TAG,'')
  node = node.replace(')','')
  node = node.replace('(','')
  node = node.replace('  ',' ')
  return node

def scrub_sentence(utt):
    # really need an overt pre-processing phase
    utt = utt.replace("per cent", " percent")
    utt = utt.replace("%", " percent")
    utt = utt.replace(".", " ")
    utt = utt.replace(",", "")
    utt = utt.replace("-", " ")
    utt = utt.replace("please ", "")
    utt = utt.replace(" please", "")
    return utt

def get_nodes(tree):
  # get first level of nodes in a tree
  nodes = []
  node = ''
  pctr = 0
  for c in tree:
    if c == '(':
      pctr += 1
    if c == ')':
      pctr -= 1

    node += c
    if pctr == 0:
      if node and len(node) > 3:
        nodes.append( node )
      node = ''
      pctr = 0

  return nodes

def extract_proper_nouns(sentence):
  sentence = sentence.replace(".","")
  sentence = sentence.replace(",","")
  sentence = sentence.replace("?","")
  sa = sentence.split(" ")
  sa[0] = sa[0].lower()
  gathering = False
  pn = ''
  pns = []
  for s in sa:
    if not s.islower():
      gathering = True
      pn += ' ' + s
    else:
      if pn != '' and pn.strip() != 'I':
        pns.append(pn.strip())
        pn = ''
        gathering = False
  if pn != '' and pn.strip() != 'I':
    pns.append(pn.strip())

  return pns

def remove_articles(sentence):
    # only from start of sentence for now!
    en_articles = ['a','an','the','all','some', 'most', 'no', 'my', 'his', 'hers', 'her', 'their', 'your']
    first_word = sentence.split(" ")[0]
    if first_word.lower() in en_articles:
        return sentence.replace(first_word + ' ', '')
    return sentence

