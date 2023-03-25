#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.
#
# import hashlib
from framework.message_types import MSG_MEDIA
from mpc_client import MpcClient
from music_info import Music_info
# import requests, time, json, glob, os
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
    self.mpc_client = MpcClient("/media/") # search for music under /media
    self.log.debug("MpcSkill.__init__(): skill base dir is %s" % (self.skill_base_dir,))
    self.register_intent('C', 'play', 'album', self.handle_message)
    self.register_intent('C', 'play', 'artist', self.handle_message)
    self.register_intent('C', 'play', 'genre', self.handle_message)
    self.register_intent('C', 'play', 'music', self.handle_message)
    self.register_intent('C', 'play', 'playlist', self.handle_message)
    self.register_intent('C', 'play', 'radio', self.handle_message)
    self.register_intent('C', 'play', 'record', self.handle_message)
    self.register_intent('C', 'play', 'song', self.handle_message)
    self.register_intent('C', 'play', 'station', self.handle_message)
    self.register_intent('C', 'play', 'title', self.handle_message)
    self.register_intent('C', 'play', 'track', self.handle_message)

    self.register_intent('C', 'next', 'song', self.handle_next)
    self.register_intent('C', 'next', 'station', self.handle_next)
    self.register_intent('C', 'next', 'title', self.handle_next)
    self.register_intent('C', 'next', 'track', self.handle_next)

    self.register_intent('C', 'previous', 'song', self.handle_prev)
    self.register_intent('C', 'previous', 'station', self.handle_prev)
    self.register_intent('C', 'previous', 'title', self.handle_prev)
    self.register_intent('C', 'previous', 'track', self.handle_prev)

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
 
    # if track or album is specified, assume it is a song, else search for 'radio' or 'youtube' requests 
    song_words = ["track", "song", "title", "album", "record", "artist", "band" ]
    if "youtube" in sentence:      
      request_type = "youtube"
    elif any([x in sentence for x in song_words]): 
      request_type = "music"
    elif "radio" in sentence:      
      request_type = "radio"
    else:
      request_type = "music"
    self.log.debug("MpcSkill.get_media_confidence(): sentence = %s request_type = %s" % (sentence, request_type,))
    match request_type:
      case "music":
        self.music_info = self.mpc_client.parse_common_phrase(sentence)
      case "radio":
        self.music_info = self.mpc_client.parse_radio(sentence)
      case "youtube":
        self.music_info = self.mpc_client.search_youtube(sentence)

    if self.music_info.mesg_file == "":     # no error 
      confidence = 110
    else:                                  # error encountered
      confidence = 0
    return {'confidence':confidence, 'correlator':0, 'sentence':sentence, 'url':self.url}

  def media_play(self, msg):
    # I am being asked to play the media
    self.log.debug("MpcSkill.media_play() play this media: %s with start_music()" % (msg.data,))
    sentence = msg.data['skill_data']['sentence']
    if self.music_info.match_type == "youtube":
      self.mpc_client.stream_youtube(self.music_info)
    else:
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

  def stop(self, msg):
    self.log.info("Mpc.stop() hit")

if __name__ == '__main__':
  mpc = MpcSkill()
  Event().wait()                         # Wait forever
