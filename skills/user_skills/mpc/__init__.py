#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.
#
from framework.message_types import MSG_MEDIA
from mpc_client import MpcClient
from music_info import Music_info
import time, json, glob, os
from skills.sva_media_skill_base import MediaSkill
from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import subprocess

class MpcSkill(MediaSkill):

  def __init__(self, bus=None, timeout=5):
    self.skill_id = 'mpc_skill'
    super().__init__(skill_id=self.skill_id, skill_category='media')
    self.url = ''
    self.lang = "en-us"                    # just US English for now
    self.mpc_client = MpcClient("/media/") # search for music under /media
    self.log.debug("MpcSkill.__init__(): skill base dir is %s" % (self.skill_base_dir))
    self.log.debug("MpcSkill.__init__(): registering 'next' intents") 
    self.register_intent('C', 'next', 'song', self.handle_next)
    self.register_intent('C', 'next', 'station', self.handle_next)
    self.register_intent('C', 'next', 'title', self.handle_next)
    self.register_intent('C', 'next', 'track', self.handle_next)

    self.log.debug("MpcSkill.__init__(): registering 'previous' intents") 
    self.register_intent('C', 'previous', 'song', self.handle_prev)
    self.register_intent('C', 'previous', 'station', self.handle_prev)
    self.register_intent('C', 'previous', 'title', self.handle_prev)
    self.register_intent('C', 'previous', 'track', self.handle_prev)

    self.log.debug("MpcSkill.__init__(): registering other OOB intents") 
    self.register_intent('C', 'pause', 'music', self.handle_pause)
    self.register_intent('C', 'resume', 'music', self.handle_resume)
    self.register_intent('C', 'stop', 'music', self.handle_stop)

  def initialize(self):
    self.music_info = Music_info("none", "", {}, []) # music to play
    self._is_playing = False
    self.mpc_client = MpcClient("/media/") # search for music under /media

  def get_media_confidence(self, msg):
    # I am being asked if I can play this music 
    sentence = msg.data['msg_sentence']
    self.log.debug("MpcSkill.get_media_confidence(): parse request %s" % (sentence,))
    sentence = sentence.lower() 
    sa = sentence.split(" ")
 
    # if track or album is specified, assume it is a song, else search for 'radio' or 'internet' requests 
    song_words = ["track", "song", "title", "album", "record", "artist", "band" ]
    if "internet radio" in sentence:      
      request_type = "radio"
    elif "internet" in sentence:      
      request_type = "internet"
    elif any([x in sentence for x in song_words]): 
      request_type = "music"
    elif "radio" in sentence:      
      request_type = "radio"
    else:
      request_type = "music"

    # search for music in the library, on Internet radio, or on the Internet depending on request
    self.log.debug("MpcSkill.get_media_confidence(): sentence = %s request_type = %s" % (sentence, request_type,))
    match request_type:
      case "music":
        self.music_info = self.mpc_client.parse_common_phrase(sentence)
      case "radio":
        self.music_info = self.mpc_client.parse_radio(sentence)
      case "internet":
        self.music_info = self.mpc_client.search_internet(sentence)

    if self.music_info.tracks_or_urls != None: # no error 
      self.log.debug("MpcSkill.get_media_confidence(): found tracks or URLs") 
      confidence = 110                     # give 110% !!!
    else:                                  # error encountered
      confidence = 0
      self.log.debug("MpcSkill.get_media_confidence() did not find music: mesg_file = "+self.music_info.mesg_file+" mesg_info = "+str(self.music_info.mesg_info))
      fqdn_name = self.skill_base_dir+"/dialog/"+self.lang+"/"+self.music_info.mesg_file+".dialog"
      self.speak_lang(fqdn_name, self.music_info.mesg_info) # speak the message
    return {'confidence':confidence, 'correlator':0, 'sentence':sentence, 'url':self.url}

  def media_play(self, msg):
    """
    I am being asked to play some media
    """
#   if [ self.music_info.tracks_or_urls == None ]:  # no music was found
#     self.log.debug("MpcSkill.media_play() no music found") 
#   else:
    self.log.debug("MpcSkill.media_play() play this media: %s" % (msg.data))
    self.mpc_client.start_music(self.music_info)

  def handle_prev(self, message):
    """
    Play previous track or station
    """
    self.log.debug("MpcSkill.handle_prev() - calling mpc_client.mpc_cmd(prev)")
    self.mpc_client.mpc_cmd("prev")

  def handle_next(self, message):
    """
    Play next track or station - called by the playback control skill
    """
    self.log.debug("MpcSkill.handle_next() - calling mpc_client.mpc_cmd(next)")
    self.mpc_client.mpc_cmd("next")

  def handle_pause(self, msg):
    """
    Pause what is playing
    """
    self.log.info("MpcSkill.handle_pause() - calling mpc_client.mpc_cmd(toggle)")
    self.mpc_client.mpc_cmd("toggle")      # toggle between play and pause

  def handle_resume(self, msg):
    """
    Resume what was playing
    """
    self.log.info("MpcSkill.handle_resume() - calling mpc_client.mpc_cmd(toggle)")
    self.mpc_client.mpc_cmd("toggle")      # toggle between play and pause

  def handle_stop(self, msg):
    """
    Clear the mpc queue 
    """
    self.log.info("MpcSkill.handle_resume() - calling mpc_client.mpc_cmd(toggle)")
    self.mpc_client.mpc_cmd("clear") 

if __name__ == '__main__':
  mpc = MpcSkill()
  Event().wait()                         # Wait forever
