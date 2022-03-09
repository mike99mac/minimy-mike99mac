Shallow Parsing

Extract information from utterances using shallow parsing. 
This approach takes a sample sentence set and creates a
set of grammatical rules from them along with skeleton
methods and associated "rule to method" mapping dictionary. 

Usage
-----
1) Manually create sample sentences in file "sentences.txt" (or any file name you prefer).
2) Run cmu_parse.py sentences_filename.txt which will convert input file to "cmu_trees.txt"
3) Run produce_rules.py which creates a "grammar to method" map in file named "generated_parse_handlers.py".
4) Manually fill in the empty methods in file "generated_parse_handlers.py".
This file was created by step (3). When done rename this to command_rule_handlers.py
or question_rule_handlers.py accordingly.
5) In your code include parse_sentence from the file named "parse_sentence.py"

Example:
  from parse_sentence import parse_sentence
  info = parse_sentence("turn off the kitchen light")

Note the file 'generated_file_handlers.py' is created by the produce_rules.py script.
The file user_generated_handlers.py are the actual handlers which are created by the user.
In this case they are the default handlers provided by the system. You can use them or
replace them with your own if you prefer or add to them. 


Overview
--------
Shallow parsing is based on the concept that for our simple use-case we can
divide sentences into one of three categories; question, command or information.

If we take the command category only we can then break each sentence down into its
grammatical structure (a parse tree) and then flatten it into a grammatical rule. 
We can then use this rule to invoke a specific method designed to handle just 
sentences of this grammatical structure. 

The complete process looks like this ...

STEP1) sentence ---> parse tree
STEP2) parse tree ---> grammar rule
STEP3) grammar rule ---> grammar rule handler

For example ...
---------------
STEP1) sentence ---> parse tree
  close the living room window
  (VP close (NP the living room window))

STEP2) parse tree ---> grammar rule
  (VP close (NP the living room window))
  VP NP

STEP3) grammar rule ---> grammar rule handler
  VP NP
  resp = rule_map['VP_NP']

This will determine the sentence structure
then invoke the proper handler based on
the derived grammar rule. It is a very simple
pattern matching approach.

This is used only for imperatives and the skeleton is
generated but then modified manually ultimately producing
the command_rule_handlers.py file which is the actual code
that handles each unique command rule structure. this file
also includes the dictionary which is used as a branch 
table for the various handlers.

If you run into command sentences that are not recognized 
you can create the rule manually and then add your handler 
to this file or you can create a text file of example command 
sentences and run cmu_parse.py against them which will produce
a file named cmu_trees.txt which can then be fed into the file
named produce_rules.py which will convert them into an execuatble 
python file named generated_rule_handlers.py. this is a raw 
initial rule handler file which you can modify accordingly.
Typically you will sumply add your new rule handlers to this
file and keep the existing code.

