#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.
#
from framework.message_types import MSG_MEDIA
from mpc_client import MpcClient
from music_info import Music_info
import glob, os, requests, time
from skills.sva_media_skill_base import MediaSkill
from skills.sva_base import SimpleVoiceAssistant
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
    self.log.debug("MpcSkill.initialize(): setting vars") 
    self.music_info = Music_info("none", "", {}, []) # music to play
    self._is_playing = False
    self.sentence = None                   # 
    # self.mpc_client = MpcClient("/media/") # search for music under /media

  def fallback_internet(self, msg):
    """
    Requested music was not found in the library - fallback to Internet search
    """
    self.music_info = self.mpc_client.search_internet(self.sentence)

  def get_media_confidence(self, msg):
    """
    I am being asked if I can play this music
    """
    sentence = msg.data['msg_sentence']
    self.log.debug("MpcSkill.get_media_confidence(): parse request %s" % (sentence))
    sentence = sentence.lower()
 
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
    else:
      request_type = "music"

    # search for music in (1) library, on (2) Internet radio, on (3) the Internet or (4) play NPR news
    self.log.debug(f"MpcSkill.get_media_confidence(): sentence = {sentence} request_type = {request_type}")
    match request_type:
      case "music":                        # if not found in library, search internet
        self.music_info = self.mpc_client.search_library(sentence)
        self.log.debug(f"MpcSkill.get_media_confidence() match_type = {self.music_info.match_type}")
        if self.music_info.match_type == "none": # music not found in library
          self.sentence = sentence 
          self.log.debug(f"MpcSkill.get_media_confidence(): not found in library - searching Internet")
          self.speak_lang(self.skill_base_dir, "searching_internet", None, self.fallback_internet) # tell user "searching internet"
      case "radio":
        self.music_info = self.mpc_client.parse_radio(sentence)
      case "internet":
        self.music_info = self.mpc_client.search_internet(sentence)
      case "news":
        self.music_info = self.search_news(sentence)
    if self.music_info.tracks_or_urls != None: # no error 
      self.log.debug("MpcSkill.get_media_confidence(): found tracks or URLs") 
    else:                                  # error encountered
      self.log.debug(f"MpcSkill.get_media_confidence() did not find music: mesg_file = {self.music_info.mesg_file} mesg_info = {self.music_info.mesg_info}")
    confidence = 100                       # always return 100%
    return {'confidence':confidence, 'correlator':0, 'sentence':sentence, 'url':self.url}

  def media_play(self, msg):
    """
    Either some music has been found, or an error message has to be spoken
    """
    self.log.debug(f"MpcSkill.media_play() match_type = {self.music_info.match_type}")
    if self.music_info.match_type == "none": # no music was found
      self.log.debug("MpcSkill.media_play() no music found") 
      self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info) 
      return None

    # speak what music will be playing and pass callback to start the music 
    if self.music_info.match_type == "news":
      file_name = self.music_info.tracks_or_urls[0]
      self.play_media(self.skill_base_dir + '/' + file_name, delete_on_complete=True)
    else:                                  # clear the mpc queue then add all matching station URLs or tracks 
      self.mpc_client.mpc_cmd("clear")   
      for next_url in self.music_info.tracks_or_urls:
        self.log.debug(f"MpcSkill.media_play() adding URL to MPC queue: {next_url}")
        self.mpc_client.mpc_cmd("add", next_url)
      if self.music_info.mesg_file == None:  # no message
        self.start_music()
      else:                                  # speak message and pass callback  
        self.speak_lang(self.skill_base_dir, self.music_info.mesg_file, self.music_info.mesg_info, self.start_music)
    
  def start_music(self):
    """
    callback to start music after media_play() speaks informational message
    """
    self.mpc_client.start_music(self.music_info) # play the music

  def search_news(self, utterance):
    """
    search for NPR news 
    param: text of the request
    return: Music_info object
    """
    self.log.debug(f"MpcSkill.search_news() utterance = {utterance}")
    url = "https://www.npr.org/podcasts/500005/npr-news-now"
    self.log.debug(f"MpcSkill.search_news() url = {url}") 
    # self.speak("Getting the latest from N.P.R news")
    res = requests.get(url)
    page = res.text
    start_indx = page.find('audioUrl')
    if start_indx == -1:
        self.log.debug(f"MpcSkill.search_news() cannot find url") 
        return
    end_indx = start_indx + len('audioUrl')
    page = page[end_indx+3:]
    end_indx = page.find('?')
    if end_indx == -1:
        print("Parse error")
        return
    self.log.debug(f"MpcSkill.search_news() start_indx = {start_indx} end_indx = {end_indx} ")       
    new_url = page[:end_indx]
    new_url = new_url.replace("\\","")
    cmd = "wget %s" % (new_url,)
    os.system(cmd)
    file_names = glob.glob("*.mp3")         # find the downloaded file
    file_name = file_names[0]
    return Music_info("news", None, None, [file_name])

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

  def stop(self, message):
    self.log.info("MpcSkill.stop() - pausing music")
    self.mpc_client.mpc_cmd("pause")


if __name__ == '__main__':
  mpc = MpcSkill()
  Event().wait()                         # Wait forever
