#
# This code is distributed under the Apache License, v2.0 
#
class Music_info:
  match_type = ""                  # album, artist, song, next or prev
  mesg_file = ""                   # if mycroft has to speak first
  mesg_info = {}                   # values to plug in
  tracks_or_urls = []              # list of music files or radio URLs to play
  def __init__(self, match_type, mesg_file, mesg_info, tracks_or_urls):
    self.match_type = match_type
    self.mesg_file = mesg_file
    self.mesg_info = mesg_info
    self.tracks_or_urls = tracks_or_urls
