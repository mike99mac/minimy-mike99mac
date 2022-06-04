
# this is a subject concept map
concepts = {
        'hot':'temperature',
        'hotter':'temperature',
        'hottest':'temperature',
        'heat':'temperature',
        'warm':'temperature',
        'cold':'temperature',
        'colder':'temperature',
        'coldest':'temperature',
        'cool':'temperature',
        }

# used by command parsing only to 
# convert a command to a concept
# this needs to be used at an 
# intent level, not globally
command_concept_map = {
        'set':'alter',
        'increase':'alter',
        'cancel':'alter',
        'renew':'alter',
        'delete':'alter',
        'decrease':'alter',
        'turn':'alter',
        'change':'alter',
        'modify':'alter',
        }
