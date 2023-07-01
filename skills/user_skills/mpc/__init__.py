#
# This code is distributed under the Apache License, v2.0 
#
from framework.message_types import MSG_MEDIA
from mpc_client import MpcClient
from music_info import Music_info
import os, requests, time
from skills.sva_media_skill_base import MediaSkill
from threading import Event
import subprocess

class MpcSkill(MediaSkill):  
  """
  Play music skill for minimy.  It uses mpc and mpd to play music from:
  - A music library such as mp3 files 
  - Internet radio stations stored in the file radio.stations.csv
  - Internet music searches 
  """
  def __init__(self, bus=None, timeout=5):
    self.skill_id = 'mpc_skill'
    super().__init__(skill_id=self.skill_id, skill_category='media')
    self.url = ''                          # has to be returned from get_media_confidence()
    self.lang = "en-us"                    # just US English for now
    self.mpc_client = MpcClient("/media/") # search for music under /media
    self.log.debug(f"MpcSkill.__init__(): skill_base_dir: {self.skill_base_dir}")
    self.music_info = Music_info("none", "", {}, []) # music to play
    self.sentence = None 

  def fallback_internet(self):
    """
    Requested music was not found in library - fallback to Internet search
    """
    self.log.debug(f"MpcSkill.fallback_internet(): calling mpc_client.search_internet({self.sentence})")
    self.music_info = self.mpc_client.search_internet(self.sentence)

  def get_media_confidence(self, msg):
    """
    Determine if the music requested can be played
    """
    sentence = msg.data['msg_sentence']
    self.log.debug(f"MpcSkill.get_media_confidence(): parse request {sentence}")
    sentence = sentence.lower()
 
    # if first word is 'create', 'make', 'add', 'delete', 'remove' or 'list'
    # then this request is to manipulate playlists
    first_word = sentence.split(' ', 1)[0]
    match first_word:
      case 'create'|'make'|'add'|'at'|'delete'|'remove'|'list': # 'add' is sometimes 'at'
        self.music_info = self.mpc_client.manipulate_playlists(sentence)
        # if self.music_info.mesg_file:      # there is a message to speak
        #   self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info)
        return {'confidence':100, 'correlator':0, 'sentence':sentence, 'url':self.url} # all done

    # if track or album is specified, assume it is a song, else search for 'radio', 'internet' or 'news' requests 
    song_words = ["track", "song", "title", "album", "record", "artist", "band" ]
    if "internet radio" in sentence:      
      request_type = "radio"
    elif "internet" in sentence:      
      request_type = "internet"
    elif any([x in sentence for x in song_words]): 
      request_type = "music"
    elif "radio" in sentence:      
      request_type = "radio"
    elif "n p r" in sentence or "news" in sentence:
      request_type = "news"
    elif "playlist" in sentence:
      request_type = "playlist"  
    else:
      request_type = "music"

    # search for music in (1) library, on (2) Internet radio, on (3) the Internet, (4) in a playlist or (5) play NPR news
    self.log.debug(f"MpcSkill.get_media_confidence(): request_type = {request_type}")
    match request_type:
      case "music":                        # if not found in library, search internet
        self.music_info = self.mpc_client.search_library(sentence)
        self.log.debug(f"MpcSkill.get_media_confidence() match_type = {self.music_info.match_type}")
        if self.music_info.match_type == "none":
          # if self.music_info.match_type == "playlist":
          self.sentence = sentence 
          self.log.debug(f"MpcSkill.get_media_confidence(): not found in library - searching Internet")
          self.music_info.mesg_file = "searching_internet"
          self.music_info.mesg_info = {"sentence": sentence} 
        # the callback did not get called  
        # self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info, self.fallback_internet) # tell user "searching internet"
          self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info) 
          self.music_info = self.mpc_client.search_internet(self.sentence) # search Internet as fallback
      case "radio":
        self.music_info = self.mpc_client.parse_radio(sentence)
      case "internet":
        self.music_info = self.mpc_client.search_internet(sentence)
      case "news":
        self.music_info = self.mpc_client.search_news(sentence)
      case "playlist":
        playlist = sentence.split(' ', 1)[1].replace("playlist ", "").replace(" ", "_") # drop "playlist", replace spaces with _s
        self.log.debug(f"MpcSkill.get_media_confidence() playlist: {playlist}")
        self.music_info = self.mpc_client.get_playlist(playlist)
    if self.music_info.tracks_or_urls != None: # no error 
      self.log.debug("MpcSkill.get_media_confidence(): found tracks or URLs") 
    else:                                  # error encountered
      self.log.debug(f"MpcSkill.get_media_confidence() did not find music: mesg_file = {self.music_info.mesg_file} mesg_info = {self.music_info.mesg_info}")
    confidence = 100                       # running uncontested - always return 100%
    return {'confidence':confidence, 'correlator':0, 'sentence':sentence, 'url':self.url}

  def media_play(self, msg):
    """
    First clear the mpc queue, then either some music has been found, a playlist operation finished, 
    or an error message has to be spoken
    """
    self.log.debug(f"MpcSkill.media_play() match_type = {self.music_info.match_type}")
    self.mpc_client.mpc_cmd("clear")       # stop any media that might be playing
    if self.music_info.match_type == "none": # no music was found
      self.log.debug("MpcSkill.media_play() no music found") 
      self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info) 
      return None
    elif self.music_info.match_type == "playlist": # no music is played, just speak message
      self.log.debug("MpcSkill.media_play() speak results of playlist request") 
      self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info) 
      return None

    # add station URLs or track files
    for next_url in self.music_info.tracks_or_urls:
      self.log.debug(f"MpcSkill.media_play() adding URL to MPC queue: {next_url}")
      cmd = f'add "{next_url}"'            # double-quotes around URL
      self.mpc_client.mpc_cmd(cmd)
    if self.music_info.mesg_file == None:  # no message
      self.start_music()
    else:                                  # speak message and pass callback  
      self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info, self.start_music)
    
  def start_music(self):
    """
    callback to start music after media_play() speaks informational message
    """
    self.log.debug(f"MpcSkill.start_music() calling mpc_client.start_music({self.music_info}")
    self.mpc_client.start_music(self.music_info) # play the music

# main()
if __name__ == '__main__':
  mpc = MpcSkill()
  Event().wait()                         # Wait forever
