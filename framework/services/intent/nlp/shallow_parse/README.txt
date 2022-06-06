
Prototype to show how to use simplistic natural language understanding
(NLU) to extract usable information from the spoken word. 

The basic approach is aas follows 

1) Using NLP we convert the sentence to a graph. This is currently
   done using the CMU link parser but could be expanded to use others.

2) Using the graph from above we convert this to a flattend list of
   shallow tokens. 

3) We next determine if we are dealing with a question, command or
   informational exchange. We ignore informational exchanges.

4) We produce a unified set of attributes for the sentence which we 
   call a SentenceInformation object. This in turn consists of a 
   SentenceStructure object and a SentenceInsight object.

5) This object is in turn used by the intent processor to match 
   the input to an intent.

Note we process commands differently than questions. For commands
we use the shallow token string to pattern match to a specific 
semantic handler which in turn extracts the semantic information. 

For questions we use a more general logic based approach which
needs to be improved. Perhaps this too will need to become a 
set of question rule handlers but for now we simply categorize
the question into one of three categories; 'yes no question', 
'who what' type questions and comparison questions. Each is 
parsed differently with comparison questions not supported at
all, 'yes no' questions weakly supported and 'wh' type questions
supported reasonably well for such a generic approach.

Prepositional phrases are only now starting to get attention
as well as conceptual abstraction (briefly introduced in
release 1.0.3).



NLP
---
You can think of natural language processing (NLP) 
as the syntactic parse stage. The result(s) of this
stage is a tree graph representing one or more 
probable sentence structures.

In addition we extract a shallow token pattern from 
the tree graph and both of these as well as the 
general sentence type (question, command, info)
are provided as input to the NLU stage.

NLU
---
You can think of natural language understanding 
(NLU) as the initial sematic parse stage. During 
this stage a bundle of attributes are produced.

This incudes noun, verb, utterance type, value,
tense, plurality, subject/dependent relationships,
proper noun to pronoun mapping, locale inferences,
etc. Context is also provided during this stage.

In general, NLU takes the output from NLP (a tree) 
and produces an object composed of structure and insight.
It begins with three basic NLP inputs; a NLP parse tree,
a list of shallow tokens extracted from the tree and
a sentence type. 

Initially, an utterance (or sentence) is categorized as 
either a question, a command or an informational input.
Each is parsed differently.

The result of this semantic parse is a SentenceInformation 
object which looks something like this.

Structure:
  parse tree - a tree representing the result of the NLP
  shallow pattern - a list of tokens extracted from the tree
  original sentence - the original unmodified input
  normalized sentence - a normalized version of the input
  nodes - a list of first level nodes from the tree

Insight:
  type - 'question', 'command', 'information', 'media', 'oob', 'unknown'
  noun - a word or list of words
  proper nouns - a list
  np - a tree
  verb - a word or list of words
  vp - a tree
  subject - a word or list
  dependent a word or list
  plurality - 'singular' or 'plural'
  tense - 'past', 'present', 'future'
  value - value if any provided in the input
  qword - question word 
  qaux - question aux word
  squal - if present a subject or verb qualifier (like 'all', 'one',
  'the', 'none') etc.

The above SentenceInformation object is used to match intents and 
currently is passed in the message to the matching endpoint as a 
json object.

