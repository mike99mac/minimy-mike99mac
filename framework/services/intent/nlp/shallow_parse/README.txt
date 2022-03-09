
Prototype to show how to use simplistic natural language parsing 
to extract usable information. This is a brain dead approach 
where the sentence tree is simply flattened and then we brute force 
the handlers based on patterns.

Since this simple approach worked surprisingly well I have decided to
move on to the next phase where we actually do a level one node parse
and then process this first level of nodes in a similar manner. 

From there, there are two ways I would like to go. First, I'd like 
to actually generate the acceptable grammar rules up front from 
input (ala NLTK) and second I'd like to explore some basic TGGs for 
advanced conceptual mapping.


