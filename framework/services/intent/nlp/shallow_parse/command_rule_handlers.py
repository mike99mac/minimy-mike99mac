import re

S_TAG = "(S "
VP_TAG = "(VP "
NP_TAG = "(NP "
PP_TAG = "(PP "
PRT_TAG = "(PRT "
ADVP_TAG = "(ADVP "
ADJP_TAG = "(ADJP "
SBAR_TAG = "(SBAR "

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


def vp_np_pp_np_np_pp_np(node):
  # note this is actually bad recognition (per cent)
  # Tree: (VP set (NP volume) (PP to (NP (NP fifty) (PP per (NP cent)))))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  squal = get_tag_value(PP_TAG, node)
  start_indx = node.find(PP_TAG) + len(PP_TAG)
  start_indx = node.find(NP_TAG,start_indx) + len(NP_TAG)
  value = node[start_indx:]
  value = value.replace(NP_TAG,"")
  value = value.replace(PP_TAG,"")
  value = value.replace("(","")
  value = value.replace(")","")
  value = value.strip()
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squal}

def vp_np_pp_np_np_np_vp_np(node):
  # (VP create (NP alarm) (PP for (NP (NP 5) (SBAR (S (NP 30) (VP pm (NP today)))))))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  start_indx = node.find(PP_TAG) + len(PP_TAG)
  start_indx = node.find(NP_TAG,start_indx) + len(NP_TAG)
  squal = node[start_indx:]
  squal = squal.replace(NP_TAG,"")
  squal = squal.replace(VP_TAG,"")
  squal = squal.replace(SBAR_TAG ,"")
  squal = squal.replace(S_TAG ,"")
  squal = squal.replace(")","")
  squal = squal.replace("(","")
  squal = squal.strip()
  value = squal
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squal}

def vp_np_pp_np_np_np_vp(node):
  # (VP create (NP alarm) (PP for (NP (NP 5) (SBAR (S (NP 15) (VP pm))))))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  start_indx = node.find(PP_TAG) + len(PP_TAG)
  start_indx = node.find(NP_TAG,start_indx) + len(NP_TAG)
  squal = node[start_indx:]
  squal = squal.replace(NP_TAG,"")
  squal = squal.replace(VP_TAG,"")
  squal = squal.replace(SBAR_TAG ,"")
  squal = squal.replace(S_TAG ,"")
  squal = squal.replace(")","")
  squal = squal.replace("(","")
  squal = squal.strip()
  value = squal
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squal}

def vp_np_pp_np_np(node):
  # (VP create (NP alarm) (PP for (NP 7)) (NP tonight))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  start_indx = node.find(PP_TAG) + len(PP_TAG)
  start_indx = node.find(NP_TAG,start_indx) + len(NP_TAG)
  squal = node[start_indx:]
  squal = squal.replace(NP_TAG,"")
  squal = squal.replace(")","")
  squal = squal.replace("(","")
  squal = squal.strip()
  value = squal
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squal}

def vp_np_pp_np_adjp_np(node):
  # (VP set (NP an alarm) (PP for (NP 3 (ADJP pm (NP today)))))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  start_indx = node.find(PP_TAG) + len(PP_TAG)
  start_indx = node.find(NP_TAG,start_indx) + len(NP_TAG)
  squal = node[start_indx:]
  squal = squal.replace(ADJP_TAG,"")
  squal = squal.replace(NP_TAG,"")
  squal = squal.replace(")","")
  squal = squal.replace("(","")
  squal = squal.strip()
  value = squal
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squal}

def vp_pp_np_pp_np_pp_np(node):
  # (VP turn (PP off (NP the light)) (PP in (NP the closet)) (PP in (NP the master bedroom)))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  value = get_tag_value(PP_TAG, node)
  start_indx = node.find(NP_TAG) + len(NP_TAG) + len(subject)
  squal = node[start_indx:]
  squal = squal.replace(PP_TAG,"")
  squal = squal.replace(NP_TAG,"")
  squal = squal.replace(")","")
  squal = squal.replace("(","")
  squal = squal.strip()
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squal}

def vp_np_prt_pp_np(node):
  # (VP turn (NP the heat) (PRT up) (PP to (NP 27 degrees)))
  # (VP turn (NP the light) (PRT off) (PP in (NP the living room)))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)

  subject_pp = get_tag_value(PRT_TAG, node)
  print("subject_pp", subject_pp)

  value = get_tag_value(PP_TAG, node)

  start_indx = node.find(PP_TAG)
  node = node[start_indx:]
  value = value + ' ' + get_tag_value(NP_TAG, node)

  if value.startswith('in '):
      tmp = value
      value = subject_pp
      subject_pp = tmp


  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':subject_pp}

def vp_prt_np(node):
  #(VP turn (PRT up) (NP the heat))
  verb = get_tag_value(VP_TAG, node)
  value = get_tag_value(PRT_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  subject_pp = ''
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':subject_pp}

def vp_np_pp_np_pp_np(node):
  # (VP set (NP the thermostat) (PP in (NP the living room)) (PP to eighty (NP two degrees)))
  # in this case our subject is the first NP PP NP and our value is the remaining PP NP
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  subject_pp = get_tag_value(PP_TAG, node)
  start_indx = node.find(PP_TAG) + len(subject_pp)
  node = node[start_indx:]
  subject_pp = subject_pp + ' ' + get_tag_value(NP_TAG, node)
  start_indx = node.find(PP_TAG) + len(PP_TAG)
  node = node[start_indx:]
  node = node.replace(NP_TAG,"")
  node = node.replace(")","")
  node = node.replace(")","")
  value = node
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':subject_pp}

def vp_np_np_pp_np_prt(node):
  # (VP turn (NP (NP the light) (PP in (NP the living room))) (PRT off))
  verb = get_tag_value(VP_TAG, node)
  value = get_tag_value(PRT_TAG, node)
  start_indx = node.find(NP_TAG) + len(NP_TAG)
  end_indx = node.rfind(PRT_TAG)
  node = node[start_indx:end_indx]
  subject = get_tag_value(NP_TAG, node)
  subject_pp = get_tag_value(PP_TAG, node)
  start_indx = node.find(PP_TAG) + len(PP_TAG)
  node = node[start_indx:]
  subject_pp = subject_pp + ' ' + get_tag_value(NP_TAG, node)
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':subject_pp}

def vp_np_advp_np(node):
  # (VP turn (NP the volume) (ADVP up (NP ten percent)))
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  start_indx = node.find(ADVP_TAG) + len(ADVP_TAG)
  node = node[start_indx:]
  node = node.replace(NP_TAG,"")
  node = node.replace(")","")
  node = node.replace(")","")
  value = node
  subject_pp = ''
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':subject_pp}

def vp_pp_np_pp_np(node):
  # (VP turn (PP off (NP the light)) (PP in (NP the living room)))
  verb = get_tag_value(VP_TAG, node)
  value = get_tag_value(PP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  start_indx = node.rfind(PP_TAG)
  node = node[start_indx-1:]
  subject_pp = get_tag_value(PP_TAG, node)
  subject_pp = subject_pp + ' ' + get_tag_value(NP_TAG, node)
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':subject_pp}

def vp_pp_np_np(node):
  # (VP turn (PP off (NP all (NP my lights))))
  verb = get_tag_value(VP_TAG, node)
  value = get_tag_value(PP_TAG, node)
  squalifier = get_tag_value(NP_TAG, node)
  start_indx = node.rfind(NP_TAG)
  node = node[start_indx-1:]
  subject = get_tag_value(NP_TAG, node)
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squalifier}

def vp_np_pp_np(node):
  # (VP change (NP the temperature) (PP to seventy (NP two degrees)))
  # or
  # (VP unlock (NP the door) (PP in (NP the kitchen)))
  # if the PP is 'to' then PP + NP less 'to') is the value
  # otherwise we assume the PP is 'in' in which case it is
  # actually part of the NP and the value is actually derived
  # from the verb!
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  qualifier = ''
  value = 'derived from verb'

  pp = get_tag_value(PP_TAG, node)
  if pp == 'to':
    start_indx = node.find(PP_TAG) + len(PP_TAG) + len('to')
    value = node[start_indx:]
    value = value.replace(NP_TAG, "")
    value = value.replace("(", "")
    value = value.replace(")", "")
    value = 'to' + ' ' + value.strip()
  else:
    start_indx = node.find(PP_TAG) + len(PP_TAG)
    qualifier = node[start_indx:]
    qualifier = qualifier.replace(NP_TAG, "")
    qualifier = qualifier.replace("(", "")
    qualifier = qualifier.replace(")", "")
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':qualifier}

def vp_pp_np(node):
  # (VP turn (PP off (NP the heat)))
  verb = get_tag_value(VP_TAG, node)
  value = get_tag_value(PP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':''}

def vp_np_prt(node):
  verb = get_tag_value(VP_TAG, node)
  value = get_tag_value(PRT_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':''}

def vp_np(node):
  verb = get_tag_value(VP_TAG, node)
  subject = get_tag_value(NP_TAG, node)
  value = 'derived from verb'

  squal = ''
  first_digit = re.search('\d', subject)
  if first_digit:
    squal = subject[first_digit.start():]
    subject = subject[:first_digit.start()].strip()

  return {'error':'', 'verb':verb, 'value':value, 'subject':subject, 'squal':squal}


# maybe some sentences that start with a NP are really a command
# NOTE - you will need to manually add to map table at bottom!

def np_vp_pp_np_pp_np(node):
  # could (NP you) (VP turn (PP off (NP the light)) (PP in (NP the kitchen)))
  target = get_tag_value(NP_TAG, node)
  if target == 'you':
    # we assume 'you' means the listener
    start_indx = node.find(VP_TAG)
    return vp_pp_np_pp_np(node[start_indx:])
  else:
    # if target is not 'you' not sure what to do
    return {'error':'unknown command format'}

def np_vp_pp_np(node):
  # would (NP you) (VP turn (PP off (NP the kitchen light)))
  target = get_tag_value(NP_TAG, node)
  if target == 'you':
    start_indx = node.find(VP_TAG)
    return vp_pp_np(node[start_indx:])
  else:
    # if target is not 'you' not sure what to do
    return {'error':'unknown command format'}

def np_vp_np_prt(node):
  target = get_tag_value(NP_TAG, node)
  if target == 'you':
    start_indx = node.find(VP_TAG)
    return vp_np_prt(node[start_indx:])
  else:
    # if target is not 'you' not sure what to do
    return {'error':'unknown command format'}

def np_vp_np(node):
  target = get_tag_value(NP_TAG, node)
  if target == 'you':
    start_indx = node.find(VP_TAG)
    return vp_np(node[start_indx:])
  else:
    # if target is not 'you' not sure what to do
    return {'error':'unknown command format'}

# maybes

def VP_NP_PP_NP_NP_PP_NP(sentence):return vp_np_pp_np_np_pp_np(sentence)
def NP_VP_PP_NP_PP_NP(sentence):return np_vp_pp_np_pp_np(sentence)
def NP_VP_PP_NP(sentence):return np_vp_pp_np(sentence)
def NP_VP_NP_PRT(sentence):return np_vp_np_prt(sentence)
def NP_VP_NP(sentence):return np_vp_np(sentence)



# probablys
def VP_NP_PP_NP_NP_NP_VP_NP(sentence):return vp_np_pp_np_np_np_vp_np(sentence)
def VP_PP_NP_PP_NP_PP_NP(sentence):return vp_pp_np_pp_np_pp_np(sentence)
def VP_NP_PP_NP_NP_NP_VP(sentence):return vp_np_pp_np_np_np_vp(sentence)
def VP_NP_PRT_PP_NP(sentence):return vp_np_prt_pp_np(sentence)
def VP_PRT_NP(sentence):return vp_prt_np(sentence)
def VP_NP_PP_NP_ADJP_NP(sentence):return vp_np_pp_np_adjp_np(sentence)
def VP_NP_NP_PP_NP_PRT(sentence):return vp_np_np_pp_np_prt(sentence)
def VP_NP_PP_NP_NP_NP(sentence):return {'error':'unimplemented = VP_NP_PP_NP_NP_NP'}
def VP_PP_NP_NP_PP_NP(sentence):return {'error':'unimplemented = VP_PP_NP_NP_PP_NP'}
def VP_NP_NP_VP_PP_NP(sentence):return {'error':'unimplemented = VP_NP_NP_VP_PP_NP'}
def VP_NP_PP_NP_PP_NP(sentence):return vp_np_pp_np_pp_np(sentence)
def VP_NP_PP_NP_NP(sentence):return vp_np_pp_np_np(sentence)
def VP_PP_NP_PP_NP(sentence):return vp_pp_np_pp_np(sentence)
def VP_NP_VP_VP_NP(sentence):return {'error':'unimplemented = VP_NP_VP_VP_NP'}
def VP_NP_ADVP_NP(sentence):return vp_np_advp_np(sentence)
def VP_NP_PP_NP(sentence):return vp_np_pp_np(sentence)
def VP_PP_NP_NP(sentence):return vp_pp_np_np(sentence)
def VP_NP_PRT(sentence):return vp_np_prt(sentence)
def VP_PP_NP(sentence):return vp_pp_np(sentence)
def VP_NP(sentence):return vp_np(sentence)


rule_map = {
'VP NP PP NP NP NP VP NP':VP_NP_PP_NP_NP_NP_VP_NP,
'VP NP PP NP NP PP NP':VP_NP_PP_NP_NP_PP_NP,
'VP PP NP PP NP PP NP':VP_PP_NP_PP_NP_PP_NP,
'VP NP PP NP NP NP VP':VP_NP_PP_NP_NP_NP_VP,
'VP NP NP PP NP PRT':VP_NP_NP_PP_NP_PRT,
'VP NP PP NP ADJP NP':VP_NP_PP_NP_ADJP_NP,
'NP VP PP NP PP NP':NP_VP_PP_NP_PP_NP,
'VP NP PP NP NP NP':VP_NP_PP_NP_NP_NP,
'VP PP NP NP PP NP':VP_PP_NP_NP_PP_NP,
'VP NP NP VP PP NP':VP_NP_NP_VP_PP_NP,
'VP NP PP NP PP NP':VP_NP_PP_NP_PP_NP,
'VP NP PP NP NP':VP_NP_PP_NP_NP,
'VP PP NP PP NP':VP_PP_NP_PP_NP,
'VP NP PRT PP NP':VP_NP_PRT_PP_NP,
'VP NP VP VP NP':VP_NP_VP_VP_NP,
'VP NP ADVP NP':VP_NP_ADVP_NP,
'VP NP PP NP':VP_NP_PP_NP,
'VP PP NP NP':VP_PP_NP_NP,
'NP VP NP PRT':NP_VP_NP_PRT,
'NP VP PP NP':NP_VP_PP_NP,
'VP NP PRT':VP_NP_PRT,
'VP PP NP':VP_PP_NP,
'NP VP NP':NP_VP_NP,
'VP PRT NP':VP_PRT_NP,
'VP NP':VP_NP,
}

