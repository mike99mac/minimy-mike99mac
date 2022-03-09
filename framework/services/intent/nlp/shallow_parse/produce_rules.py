import string

table = str.maketrans('', '', string.ascii_lowercase)

def get_shallow_rule_from_tree(s):
  rule = ''
  s = s.translate(table)
  s = s.replace("(","")
  s = s.replace(")","")
  s = s.strip()
  sa = s.split(" ")
  for x in sa:
    if x.startswith("NP") or x.startswith("PP") or x.startswith("VP") or x.startswith("PRT") or x.startswith("AD"):
      rule += x.strip() + ' '
  return rule

if __name__ == "__main__":
    # we will overwrite this file!
    output_filename = "generated_rule_handlers.py"

    nodes = []

    # produce rules from results of cmu parse
    with open('cmu_trees.txt') as f:
        nodes = f.read().splitlines()

    rules = []
    for s in nodes:
        rule = get_shallow_rule_from_tree(s)
        rules.append(rule.strip())

    rules = set(rules)
    tmp_rules = list(rules)
    rules = sorted(tmp_rules, key=len, reverse=True)

    method_code_section = ""
    rule_map_section = "rule_map = {"

    static_code_section = """

VP_TAG = "(VP "
NP_TAG = "(NP "
PP_TAG = "(PP "
PRT_TAG = "(PRT "
ADVP_TAG = "(ADVP "

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
    """

    num_rules_produced = 0
    for rule in rules:
        if len(rule) > 0:
            num_rules_produced += 1
            method_name = rule.replace(" ", "_")
            method_code = "def %s(sentence):return {'error':'unimplemented = %s'}" % (method_name, method_name)
            method_code_section += method_code + "\n"
            rule_map_entry = "'%s':%s," % (rule, method_name)
            rule_map_section += rule_map_entry + "\n"

    rule_map_section += "}"

    fh = open(output_filename,"w")
    fh.write(static_code_section)
    fh.write("\n\n")
    fh.write(method_code_section)
    fh.write("\n\n")
    fh.write(rule_map_section)
    fh.write("\n\n")
    fh.close()

    print("Produced %s rules from %s sentences" % (num_rules_produced, len(nodes)))
