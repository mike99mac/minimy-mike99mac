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

