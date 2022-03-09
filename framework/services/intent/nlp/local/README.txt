This is the cmu link parser. Unzip it and run 'make'. The 
script parse_interface.py will provide the interface for the 
system. It calls the program ./parse and uses stdin/out to
communicate with it.

This is just a local version of the API called by the cmu_parse.py
script. That is a remote version of this.

If you don't wat to bother with this simply run configure.py and
select remote NLP and the system will hit the CMU website API.
