import csv
from dataclasses import dataclass
from enum import Enum
import glob
import logging
from music_info import Music_info
import os 
from pathlib import Path
import random
from random import shuffle
import re
import requests
from skills.sva_base import SimpleVoiceAssistant
import subprocess
from subprocess import run, Popen, PIPE, STDOUT
import time
from typing import Union, Optional, List, Iterable
import urllib.parse
from youtube_search import YoutubeSearch

class MpcClient(SimpleVoiceAssistant):
  # Accept voice commands to communicate with mpd using mpc calls 
  # Support cataloging of music files and accessing Internet radio stations
  music_dir: str                           # directory where music files are 
  max_queued: int                          # maximum number of tracks or stations to queue
  station_name: str                   
  station_genre: str  
  station_country: str  
  station_language: str 
  station_ads: str    
  station_URL: str 
  request_type: str                        # "genre", "country", "language", "random" or "next_station"
  list_lines: list                         # all radio stations in the CSV file
  
  def __init__(self, music_dir: Path):
    super().__init__(skill_id="mpc_skill", skill_category="media")
    self.log = logging.getLogger(__name__)
    self.music_dir = music_dir
    self.max_queued = 20                                         
    self.station_name = "unknown"                   
    self.station_genre = "unknown"
    self.station_country = "unknown"
    self.station_language = "unknown"
    self.station_ads = "unknown" 
    self.station_URL = "unknown"  
    self.request_type = "unknown"  
    self.list_lines = []
    self.temp_dir = self.base_dir + "/tmp/save_audio" # save audio files here 

  def initialize(self, music_dir: Path):  
    """ 
    Turn mpc "single" off so player keeps playing music   
    Return: boolean
    """
    return self.mpc_cmd("single off")
    # try:
    #   result = subprocess.check_output("/usr/bin/mpc single off", shell=True) 
    # except subprocess.CalledProcessError as e:      
    #   self.log.debug(f"MpcClient.__init__():  mpc single off return code: {e.returncode}") 

  def mpc_update(self, wait: bool=True):
    # Update the mpd database by searching for music files 
    cmd = "/usr/bin/mpc update"
    if wait:
      cmd.append("--wait")
    self.log.debug(f"mpc_update() running command: {cmd}")
    subprocess.check_call(cmd)
  
  def mpc_play(self):
    # Start the mpc player   
    self.log.debug(f"MpcClient.mpc_play() - first sleeping for .1 sec")
    time.sleep(.1)                         # is this really needed?
    self.mpc_cmd("play")

  def start_music(self, music_info: Music_info):
    # Start playing the type of music passed in the music_info object   
    self.log.debug(f"MpcClient.start_music(): match_type : {music_info.match_type}")
    if music_info.match_type == "internet":
      self.stream_internet_music(music_info)
      return True
    elif music_info.match_type == "next" or music_info.match_type == "prev":
      self.mpc_cmd(music_info.match_type)  # call "mpc next" or "mpc prev"
      return True
    elif music_info.tracks_or_urls == None:
      self.log.debug("MpcClient.start_music() Unexpected: no music found")
      return False
    else:                                  # must be song or album
      self.log.debug(f"MpcClient.start_music() -  calling mpc_play") 
      self.mpc_play()
      return True

  def search_music(self, command: str, type1: Optional[str]=None, name1: Optional[str]=None, type2: Optional[str]=None, name2: Optional[str]=None) -> List[List[str]]:
    # Search for music by album, artist, title, or genre allowing up to two qualifiers.
    # A "listall" command returns all music in library
    # mpc syntax: https://www.musicpd.org/doc/mpc/html/#cmdoption-f
    self.log.debug(f"MpcClient.search_music(): command: {command} type1: {type1} name1: {name1}, type2: {type2} name2: {name2}")
    cmd = ["mpc", command, "--format", "%artist%\t%album%\t%title%\t%time%\t%file%"]
    if type1 and name1 != None:            # there is a search qualifier
      cmd.extend([type1, name1])
    if type2 and name2 != None:            # there is a second search qualifier
      cmd.extend([type2, name2])
    self.log.debug(f"MpcClient.search_music(): cmd: {cmd}")  
    return [
      line.split("\t")
      for line in subprocess.check_output(cmd, universal_newlines=True).splitlines()
      if line.strip()
    ]

  def time_to_seconds(self, time_str: str) -> int:
    # convert HR:MIN:SEC to number of seconds 
    parts = time_str.split(":", maxsplit=2)
    assert parts
    hours, minutes, seconds = 0, 0, 0

    if len(parts) == 3:
      hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
    elif len(parts) == 2:
      minutes, seconds = int(parts[0]), int(parts[1])
    else:
      seconds = int(parts[0])
    return (hours * 60 * 60) + (minutes * 60) + seconds
  
  def search_library(self, phrase):
    # Perform "brute force" parsing of a music play request
    # Music playing vocabulary of search phrase:
    #   play (track|song|title|) {track} by (artist|band|) {artist}
    #   play (album|record) {album} by (artist|band) {artist}
    #   play (any|all|my|random|some|) music 
    #   play (playlist) {playlist}
    #   play (genre|johnra) {genre}     
    # Returns: Music_info object
    artist_name = "unknown_artist"
    found_by = "yes"                       # assume "by" is in the phrase
    intent = "unknown"                                                           
    if phrase[0:4] == "play":              # play is the first word                       
      phrase = phrase.split(" ", 1)[1]     # remove play   
    match_type = "unknown"                 # album, artist, song or unknown
    music_name = ""                        # search term of music being sought
    tracks_or_urls = []                    # files of songs to be played
    self.log.debug(f"MpcClient.search_library() phrase: {phrase}")

    # first check for a partial request with no music_name
    match phrase:
      case "album" | "track" | "song" | "artist" | "genre" | "johnra" | "playlist":
        if phrase == "johnra":             # fix the spelling
          phrase = "genre"
        self.log.debug(f"MpcClient.search_library() not enough information in phrase: {phrase}")
        mesg_info = {"phrase": phrase}
        self.log.debug(f"MpcClient.search_library() mesg_info: {mesg_info}")
        music_info = Music_info("song", "not_enough_info", {"phrase": phrase}, None)
        self.log.debug(f"MpcClient.search_library() music_info.mesg_info: {music_info.mesg_info}")
        return music_info
    key = re.split(" by ", phrase)
    if len(key) == 1:                      # did not find "by"
      found_by = "no"
      music_name = str(key[0])             # check for all music, genre and playlist
      self.log.debug(f"MpcClient.search_library() music_name: {music_name}")
      match music_name:
        case "any music" | "all music" | "my music" | "random music" | "some music" | "music":
          self.log.debug(f"MpcClient.search_library() removed keyword {music_name} from music_name")
          music_info = self.get_music("music", music_name, artist_name)
          return music_info
      key = re.split("^genre ", music_name)
      if len(key) == 2:                    # found first word "genre"
        genre = str(key[1])
        self.log.debug(f"MpcClient.search_library() removed keyword {music_name} from music_name")
        return self.get_music("genre", genre, artist_name)
      else:
        key = re.split("^playlist ", music_name)
        if len(key) == 2:                # found first word "playlist"
          playlist = str(key[1])
          self.log.debug(f"MpcClient.search_library() removed keyword {music_name} from music_name")
          return self.get_music("playlist", playlist, artist_name)
    elif len(key) == 2:                  # found one "by"
      music_name = str(key[0])
      artist_name = str(key[1])          # artist name follows "by"
      self.log.debug(f"MpcClient.search_library() found the word by - music_name: {music_name} artist_name: {artist_name}")
    elif len(key) == 3:                  # found "by" twice - assume first one is in music
      music_name = str(key[0]) + " by " + str(key[1]) # paste the track or album back together
      self.log.debug("MpcClient.search_library() found the word by twice: assuming first is music_name")
      artist_name = str(key[2])
    else:                                # found more than 2 "by"s - what to do?
      music_name = str(key[0])

    # look for leading keywords in music_name
    key = re.split("^album |^record ", music_name)
    if len(key) == 2:                    # found first word "album" or "record"
      match_type = "album"
      music_name = str(key[1])
      if found_by == "yes":
        intent = "album_artist"
      else:
        intent = "album"
      self.log.debug("MpcClient.search_library() removed keyword album or record")
    else:                                # leading "album" not found
      key = re.split("^track |^song |^title |tracked", music_name) # track can be tracked
      if len(key) == 2:                  # leading "track", "song" or "title" found
        music_name = str(key[1])
        match_type = "song"
        if found_by == "yes":            # assume artist follows "by"
          intent = "track_artist"
        else:                            # assume track
          intent = "track"
        self.log.debug("MpcClient.search_library() removed keyword track, song or title")
      else:                              # leading keyword not found
        key = re.split("^artist |^band ", music_name) # remove "artist" or "band" if first word
        if len(key) == 2:                # leading "artist" or "band" found
          music_name = "all_music"       # play all the songs they have
          artist_name = str(key[1])
          match_type = "artist"
          intent = "artist"
          self.log.debug("MpcClient.search_library() removed keyword artist or band from music_name")
        else:                            # no leading keywords found yet
          self.log.debug("MpcClient.search_library() no keywords found: in last else clause")
          if found_by == "yes":
            intent = "unknown_artist"    # found artist but music could be track or album
    key = re.split("^artist |^band ", artist_name) # remove "artist" or "band" if first word
    if len(key) == 2:                    # leading "artist" or "band" found in artist name
      artist_name = str(key[1])
      self.log.debug("MpcClient.search_library() removed keyword artist or band from artist_name")
    self.log.debug(f"MpcClient.search_library() calling get_music with {intent}, {music_name} and {artist_name}")
    return self.get_music(intent, music_name, artist_name) 

  def get_album(self, album_name, album_id, artist_name):
    # Return a Music_info object with track file names for one album 
    self.log.debug(f"MpcClient.get_album() album_name: {album_name} artist_name: {artist_name}")
    artist_found = "none"
    if artist_name == "unknown_artist":    # artist is not a search term
      results = self.search_music("search", "album", album_name)
    else:                                  # artist is also a search term
      results = self.search_music("search", "album", album_name, "artist", artist_name)
    num_hits = len(results)
    self.log.debug(f"MpcClient.get_album() num_hits: {num_hits}")
    if num_hits == 0: 
      self.log.debug(f"MpcClient.get_album() _get() did not find an album matching {album_name}")
      mesg_info = {"album_name": album_name, "artist_name": artist_name}
      return Music_info("none", "music_not_found", mesg_info, [])
    tracks_or_urls = []                    # at least one hit
    correct_artist = True
    for artist_found, album_found, title, time_str, relative_path in results:
      next_track=f'"{relative_path}"'  
      self.log.debug(f"MpcClient.get_album() adding track: {next_track} to queue")     
      tracks_or_urls.append(next_track)    # add track to queue
      if artist_name != "unknown_artist" and artist_name != artist_found.lower(): # wrong artist  
        correct_artist = False  
    if correct_artist == False:    
      self.log.debug(f"MpcClient.get_album() playing album {album_name} by {artist_found} not by {artist_name}")
      mesg_file = "diff_album_artist"
      mesg_info = {"album_name": album_name, "artist_found": artist_found}
    else:   
      self.log.debug(f"MpcClient.get_album() found album: {album_name} by artist: {artist_found}")    
      mesg_file = "playing_album"
      mesg_info = {"album_name": album_found, "artist_name": artist_found}
    self.mpc_cmd("repeat", "off")          # do not keep playing album after last track
    return Music_info("album", mesg_file, mesg_info, tracks_or_urls)

  def get_artist(self, artist_name):
    # Return tracks for the requested artist  
    self.log.debug(f"MpcClient.get_artist() called with artist_name: {artist_name}")
    results = self.search_music("search", "artist", artist_name)    
    num_hits = len(results)
    self.log.debug(f"MpcClient.get_artist() num_hits: {num_hits}")
    random.shuffle(results)                # shuffle tracks
    tracks_or_urls = []
    i = 0                                  # counter
    for artist_found, album_found, title, time_str, relative_path in results:
      if artist_found.lower() != artist_name: # not an exact match
        self.log.debug(f"MpcClient.get_artist() skipping artist found that does not match: {artist_found.lower()}")
        continue   
      next_track=f'"{relative_path}"'  
      self.log.debug(f"MpcClient.get_artist() adding track {next_track} to queue")     
      tracks_or_urls.append(next_track)    # add track to queue
      i += 1                               # increment counter
      if i == self.max_queued:             # that"s enough 
        self.log.debug(f"MpcClient.get_artist() reached maximum number of tracks to queue: {self.max_queued}")
        break
    mesg_info = {"artist_name": artist_name}    
    if i == 0:                             # no hits
      self.log.debug(f"MpcClient.get_artist() _get() did not find an artist matching {artist_name}")
      return Music_info("none", "artist_not_found", mesg_info, [])
    else:
      self.mpc_cmd("repeat", "on")         # keep playing artist after last track
      return Music_info("artist", "playing_artist", mesg_info, tracks_or_urls)
 
  def get_music_info(self, match_type, mesg_file, mesg_info, results): 
    # Given the results of an mpc search. return a Music_info object 
    self.log.debug(f"MpcClient.get_music_info() match_type: {match_type} mesg_file: {mesg_file} mesg_info: {mesg_info}")
    tracks_or_urls = []   
    for artist_found, album_found, title, time_str, relative_path in results:
      next_track=f'"{relative_path}"'      # enclose file name in double quotes 
      self.log.debug(f"MpcClient.get_music_info() adding track: {next_track} to queue")     
      tracks_or_urls.append(next_track)    # add track to queue  
    return Music_info(match_type, mesg_file, mesg_info, tracks_or_urls) 

  def get_all_music(self):
    # Return up to max_queued random tracks from all music in the library
    self.log.debug("MpcClient.get_all_music() getting random tracks")
    results = self.search_music("listall") 
    if len(results) == 0:   
      self.log.debug("MpcClient.get_all_music() did not find any music")
      mesg_info = {"music_name": "all music"}
      return Music_info("none", "music_not_found", mesg_info, None)
    random.shuffle(results)                # shuffle tracks
    results = results[0:self.max_queued]   # prune to max number of tracks
    num_hits = len(results)
    self.log.debug(f"MpcClient.get_all_music() num_hits: {num_hits}")
    mesg_info = {"num_hits": num_hits}
    self.mpc_cmd("repeat", "on")           # keep playing random tracks 
    return self.get_music_info("random", "playing_random", mesg_info, results)
    
  def get_genre(self, genre_name):
    # Return up to max_queued tracks for a requested genre 
    self.log.debug(f"MpcClient.get_genre(): called with genre_name: {genre_name}")
    results = self.search_music("search", "genre", genre_name) 
    if len(results) == 0: 
      self.log.debug(f"MpcClient.get_genre() did not find genre_name: {genre_name}")
      return Music_info("none", "genre_not_found", {"genre_name": genre_name}, None)
    random.shuffle(results)                # shuffle tracks found
    results = results[0:self.max_queued]   # prune to max number of tracks
    mesg_info = {"genre_name": genre_name}
    self.mpc_cmd("repeat", "on")              # keep playing genre
    return self.get_music_info("song", "playing_genre", mesg_info, results)
    
  def get_track(self, track_name, artist_name):
    # Get track by name, optionally by a specific artist
    # If artist is not specified, it is passed in as "unknown_artist"
    self.log.debug(f"MpcClient.get_track() track_name: {track_name} artist_name: {artist_name}")
    if artist_name == "unknown_artist":    # artist is not a search term
      results = self.search_music("search", "title", track_name)
    else:                                  # artist is also a search term
      results = self.search_music("search", "title", track_name, "artist", artist_name)   
    num_recs = len(results)
    if num_recs == 0:                      # no hits
      self.log.debug(f"MpcClient.get_track(): did not find a track matching {track_name}")
      if artist_name == "unknown_artist":
        mesg_file = "track_not_found"
        mesg_info = {"track_name": track_name}
      else:
        mesg_file = "track_artist_not_found"
        mesg_info = {"track_name": track_name, "artist_name": artist_name}   
      return Music_info("none", mesg_file, mesg_info, None) 

    # matching music has been found   
    num_hits = 0
    mesg_file = ""
    mesg_info = {}
    tracks_or_urls = []                 
    for artist_found, album_found, track_found, time_str, relative_path in results:
      tracks_or_urls.append(f'"{relative_path}"')
      if track_found.lower() == track_name: # track name matches
        if artist_name != "unknown_artist" and artist_found.lower() == artist_name: # exact match
          # self.log.debug(f"MpcClient.get_track() exact match at index: {index}") 
          mesg_file = "playing_track"
          mesg_info = {"track_name": track_name, "artist_name": artist_found, "album_name": album_found}
          return Music_info("track", mesg_file, mesg_info, tracks_or_urls) # all done
        num_hits += 1
    self.log.debug(f"MpcClient.get_track(): num_hits: {num_hits}")    
    if num_hits == 1:                      # one track found
      self.mpc_cmd("repeat", "off")        # play just once      
      if artist_name != "unknown_artist" and artist_name != artist_found: # wrong artist _ speak correct artist before playing 
        self.log.debug(f"MpcClient.get_track() found track {track_name} by {artist_found} not by {artist_name}")
        mesg_file = "diff_artist"
        mesg_info = {"track_name": track_name, "album_name": album_found, "artist_found": artist_found}  
      else:  
        mesg_file = "playing_track"
        mesg_info = {"track_name": track_name, "artist_name": artist_found, "album_name": album_found}
    else:                                  # multiple hits
      self.mpc_cmd("repeat", "on")         # allow loop
      mesg_file = "found_tracks"
      mesg_info = {"track_name": track_name, "num_hits": num_hits}
    return Music_info("song", mesg_file, mesg_info, tracks_or_urls) 

  def get_unknown_music(self, music_name, artist_name):
    # Search on a music search term - could be album, artist or track
    self.log.debug(f"MpcClient.get_unknown_music() music_name: {music_name} artist_name: {artist_name}")
    tracks_or_urls = []                     # list of tracks to play
    for music_type in ["artist", "album", "title"]:
      results = self.search_music("search", music_type, music_name)    
      num_recs = len(results)
      if num_recs == 0:                  # no hit
        continue                         # iterate loop
      self.log.debug(f"MpcClient.get_unknown_music() found {num_recs} hits with music_type: {music_type}")  
      match music_type:
        case "artist":                   
          for artist, album, title, time_str, relative_path in results:
            if artist.lower() == music_name: # exact match
              tracks_or_urls.append(f'"{relative_path}"')
          num_exact = len(tracks_or_urls)
          if num_exact == 0:
            continue                     # iterate loop
          else:      
            mesg_info = {"artist_name": artist}
            music_info = Music_info("artist", "playing_artist", mesg_info, tracks_or_urls)
        case "album":                    # queue multiple tracks
          for artist, album, title, time_str, relative_path in results:
            tracks_or_urls.append(f'"{relative_path}"')
          mesg_info = {"album_name": album, "artist_name": artist}
          music_info = Music_info("album", "playing_album", mesg_info, tracks_or_urls)
        case "title":                    # queue one track
          index = random.randrange(num_recs) # choose a random track 
          self.log.debug(f"MpcClient.get_unknown_music() random track index: {index}")
          tracks_or_urls.append(f'"{results[index][4]}"') # relative path is fifth value 
          self.log.debug(f"MpcClient.get_unknown_music() tracks_or_urls: {tracks_or_urls}")
          mesg_info = {"track_name": results[index][2], "album_name": results[index][1], "artist_name": results[index][0]}
          music_info = Music_info("song", "playing_track", mesg_info, tracks_or_urls)
      return music_info   

    # if we fall through, no music was found 
    self.log.debug(f"MpcClient.get_unknown_music(): did not find music matching {music_name}") 
    return Music_info("none", "music_not_found", {"music_name": music_name}, None)
    
  def get_music(self, intent, music_name, artist_name):
    # Search for tracks_or_urls with one search terms and an optional artist name
    # intent can be: album, album_artist, artist, music, track, track_artist, unknown_artist or unknown
    # call one of:
    #   get_album()         play an album
    #   get_artist()        play an artist
    #   get_all_music()     play "full random" 
    #   get_genre()         play a music genre 
    #   get_playlist()      play a saved playlist
    #   get_track()         play a specific track
    #   get_unknown_music() play something that might be an album, an artist or a track 
    # Return: Music_info object  
    self.log.debug(f"MpcClient.get_music() intent: {intent} music_name: {music_name} artist_name: {artist_name}") 
    match intent:
      case "album":
        music_info = self.get_album(music_name, -1, "unknown_artist") # no album id
      case "album_artist":
        music_info = self.get_album(music_name, -1, artist_name) # no album id
      case "artist":
        music_info = self.get_artist(artist_name) # no artist_id 
      case "genre":                   
        music_info = self.get_genre(music_name) 
      case "music":                      # full random
        music_info = self.get_all_music()
      case "playlist": 
        music_info = self.get_playlist(music_name)  
      case "track":                      # call get_track with unknown track ID
        music_info = self.get_track(music_name, "unknown_artist")
      case "track_artist":           
        music_info = self.get_track(music_name, artist_name)
      case "unknown_artist":
        music_info = self.get_unknown_music(music_name, artist_name)
      case "unknown":
        music_info = self.get_unknown_music(music_name, "unknown_artist")
      case _:                            # unexpected
        self.log.debug(f"MpcClient.get_music() INTERNAL ERROR: intent is not supposed to be: {intent}")
        music_info = Music_info("none", None, None, None)      
    return music_info

  def manipulate_playlists(self, utterance):
    # List, create, add to, remove from and delete playlists
    # Playlist vocabulary:
    #   (create|make) playlist {playlist}
    #   (delete|remove) playlist {playlist}
    #   add (track|song|title) {track} to playlist {playlist}
    #   add (album|record) {album} to playlist {playlist}
    #   (remove|delete) (track|song|title) {track} from playlist {playlist}
    #   list (my|) playlists
    #   what playlists (do i have|are there)
    #   what are (my|the) playlists
    # return: Music_info object w/match_type = "playlist" and possibly mesg_file and mesg_info
    mesg_file = ""
    mesg_info = {}
    self.log.debug(f"MpcClient.manipulate_playlists() called with utterance {utterance}") 
    words = utterance.split()            # split request into words
    match words[0]:                      
      case "create" | "make":  
        phrase = words[2:]               # skip first word
        phrase = " ".join(phrase)        # convert to string
        self.log.debug(f"MpcClient.manipulate_playlists() phrase: {phrase}") 
        mesg_file, mesg_info = self.create_playlist(phrase) 
      case "remove" | "delete":      
        if words[1] == "playlist":
          phrase = words[2:]             # skip first word
          phrase = " ".join(phrase)      # convert to string
          mesg_file, mesg_info = self.delete_playlist(phrase) 
        else:                       
          mesg_file, mesg_info = self.delete_from_playlist(words[1:]) 
      case "add" | "ad" | "at":
        phrase = words[1:]               # delete first word
        phrase = " ".join(phrase)        # convert to string 
        mesg_file, mesg_info = self.add_to_playlist(phrase) 
      case "list"|"what":  
        mesg_file, mesg_info = self.list_playlists()
    self.log.debug(f"MpcClient.manipulate_playlists() returned mesg_file: {mesg_file} and mesg_info: {mesg_info}")
    return Music_info("playlist_op", mesg_file, mesg_info, [])

  def get_playlist(self, playlist_name):
    # Load file names of tracks in playlist and return a Music_info object
    # param 1: name of playlist
    # return: Music_info object with playlist"s tracks
    mesg_file = ""
    mesg_info = {}  
    tracks_or_urls = []
    playlist_name = playlist_name.replace(" ", "_") # replace spaces with underscores

    # clear the queue then load the playlist
    self.mpc_cmd("clear")
    self.log.debug(f"MpcClient.get_playlist(): playlist_name: {playlist_name}")
    cmd = f"/usr/bin/mpc load {playlist_name}"
    try:
      p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
      stdout, stderr = p.communicate()
    except subprocess.CalledProcessError as e:          
      self.log.error(f"MpcClient.get_playlist(): e.returncode: {e.returncode}")
      mesg_info = {"playlist_name": playlist_name}
      mesg_file = "playlists_not_found" 
      return Music_info("none", mesg_file, mesg_info, tracks_or_urls) 
         
    # get file names not track names of playlist
    cmd = f"mpc -f "%file%" playlist" 
    try:
      p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
      stdout, stderr = p.communicate()
      track_files = str(stdout.decode("utf-8"))
      self.log.debug(f"MpcClient.get_playlist(): track_files = {track_files}")
    except subprocess.CalledProcessError as e: # not expected        
      self.log.error(f"MpcClient.get_playlist(): cmd: {cmd} e.returncode: {e.returncode}")
      mesg_info = {"cmd": "playlist", "rc": e.returncode}
      mesg_file = "mpc_failed"
      return Music_info("none", mesg_file, mesg_info, tracks_or_urls)   
    if len(track_files) == 0:              # empty playlist
      mesg_info = {"playlist_name": playlist_name}
      mesg_file = "empty_playlist" 
      return Music_info("empty_playlist", mesg_file, mesg_info, tracks_or_urls)  
    else:                                  # track(s) found  
      for next_track in track_files.splitlines(): # add track files to list
        self.log.debug(f"MpcClient.get_playlist(): adding file {next_track}")
        tracks_or_urls.append(next_track)
      mesg_file = "playing_playlist"
      mesg_info = {"playlist_name": playlist_name}  
    return Music_info("playlist", mesg_file, mesg_info, tracks_or_urls)  

  def create_playlist(self, phrase): 
    # Create requires a playlist name and music name as Mpc playlists cannot be empty
    # Vocabulary: (create|make) playlist {playlist}
    # Return:     mesg_file, mesg_info
    self.log.debug(f"MpcClient.create_playlist() called with phrase {phrase}")
    playlist_name = phrase.replace(" ", "_").replace('"', "").lower() 
    music_info = self.get_playlist(playlist_name)  # check if playlist already exists
    self.log.debug(f"MpcClient.create_playlist() playlist_name: {playlist_name} music_info.mesg_file: {music_info.mesg_file}")
    if music_info.mesg_file != "playlists_not_found" and music_info.mesg_file != "empty_playlist": # already exists
      self.log.debug(f"MpcClient.create_playlist() playlist already exists: {playlist_name}")
      mesg_info = {"playlist_name": playlist_name}
      return "playlist_exists", mesg_info
        
    # create the playlist
    cmd = f"/usr/bin/mpc save {playlist_name}" 
    self.log.debug(f"MpcClient.create_playlist(): calling cmd: {cmd}")
    try:
      result = subprocess.check_output(cmd, shell=True) 
    except subprocess.CalledProcessError as e:     
      self.log.error(f"MpcClient.create_playlist(): mpc return code: {e.returncode}")     
      mesg_file = "mpc_failed"
      mesg_info = {"cmd": "save", "rc": e.returncode}
      return mesg_file, mesg_info
    mesg_info = {"playlist_name": phrase}
    mesg_file = "created_playlist"
    return mesg_file, mesg_info

  def delete_playlist(self, playlist_name):
    # Delete a playlist
    # Vocabulary: (delete|remove) playlist {playlist}
    # Return: mesg_file, mesg_info
    self.log.debug(f"MpcClient.delete_playlist() called with playlist_name: {playlist_name}")
    playlist_name = playlist_name.rstrip(" ").replace(" ", "_").replace('"', "") # replace spaces with underscores
    cmd = f"/usr/bin/mpc rm {playlist_name}"      # delete the playlist
    self.log.debug(f"MpcClient.delete_playlist(): calling cmd: {cmd}")
    try:
      p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
      stdout, stderr = p.communicate()
    except subprocess.CalledProcessError as e:          
      self.log.error(f"MpcClient.delete_playlist(): unexpected: e.returncode: {e.returncode}")
    mesg_info = {"playlist_name": playlist_name}  
    self.mpc_cmd("clear")                  # clear playlist in memory
    return "deleted_playlist", mesg_info

  def add_to_playlist(self, phrase):
    # Add a track or an album to an existing playlist
    # Params:
    #   phrase:     all text after "add"
    # Vocabulary:
    #   add (track|song|title) {track} to playlist {playlist}
    #   add (album|record) {album} to playlist {playlist}
    # Return: "mesg_file", {mesg_info}  
    self.mpc_cmd("clear")                  # clear the queue
    self.log.debug(f"MpcClient.add_to_playlist() phrase: {phrase}")
    key = re.split(" to playlist| two playlist| 2 playlist ", phrase)
    if len(key) == 1:                      # did not find "to playlist"
      self.log.debug("MpcClient.add_to_playlist() ERROR 'to playlist' not found in phrase")
      return "to_playlist_missing", {} 
    music_name = key[0]
    playlist_name = key[1].strip(" ").replace(" ", "_").replace('"', "") # replace spaces with underscores
    self.log.debug(f"MpcClient.add_to_playlist() music_name: {music_name} playlist_name: {playlist_name}")

    # get the tracks in the playlist
    existing_music_info = self.get_playlist(playlist_name) # verify playlist exists
    if existing_music_info.match_type == "none": # playlist not found 
      self.log.debug(f"MpcClient.add_to_playlist() did not find playlist_name: {playlist_name}")
      mesg_file = "playlist_not_found"
      mesg_info = {"playlist_name": playlist_name}
      return mesg_file, mesg_info
    self.log.debug(f"MpcClient.add_to_playlist(): playlist_name: {playlist_name} music_name: {music_name}")

    # find the tracks to add
    new_music_info = self.search_library(music_name) 
    if new_music_info.match_type == "none":    # did not find track/album
      self.log.debug(f"MpcClient.add_to_playlist() did not find music_name: {music_name}") 
      mesg_file = "music_not_found"
      mesg_info = {"music_name": music_name}
      return mesg_file, mesg_info
    self.log.debug(f"MpcClient.add_to_playlist() new_music_info.tracks_or_urls {new_music_info.tracks_or_urls}")
    # TO DO: should check for duplicates here because mpc will add them
    # However, files found are fully qaulified, with those in mpc are relative to the mount point (usually /media)
    for next_file in new_music_info.tracks_or_urls:
      self.log.debug(f"MpcClient.add_to_playlist() next_file: {next_file}")
      if self.mpc_cmd("add", next_file) != 0:
        self.log.error(f"MpcClient.add_to_playlist() unexpected: 'mpc add {next_file}' failed")
        mesg_file = "mpc_failed"
        mesg_info = {"cmd": "add", "rc": 1}
        return mesg_file, mesg_info   
    
    # to save a playlist, it first must be deleted - go figure
    cmd = f"/usr/bin/mpc rm {playlist_name}" 
    self.log.debug(f"MpcClient.add_to_playlist(): calling cmd: {cmd}")
    try:
      result = subprocess.check_output(cmd, shell=True) 
    except subprocess.CalledProcessError as e: 
      self.log.error(f"MpcClient.add_to_playlist(): cmd: {cmd} e.returncode: {e.returncode}")
      mesg_file = "mpc_failed"
      mesg_info = {"cmd": "remove", "rc": e.returncode}
      return mesg_file, mesg_info   

    # now save it  
    cmd = f"/usr/bin/mpc save {playlist_name}"  
    self.log.debug(f"MpcClient.add_to_playlist(): calling cmd: {cmd}")
    try:
      result = subprocess.check_output(cmd, shell=True) 
    except subprocess.CalledProcessError as e: 
      self.log.error(f"MpcClient.add_to_playlist(): cmd: {cmd} e.returncode: {e.returncode}")
      mesg_file = "mpc_failed"
      mesg_info = {"cmd": "save", "rc": e.returncode}
      return mesg_file, mesg_info   
    mesg_file = "added_to_playlist"  
    mesg_info = {"music_name": music_name, "playlist_name": playlist_name}
    return mesg_file, mesg_info
    
  def delete_from_playlist(self, phrase):
    # Delete a track from a playlist
    # Vocabulary:
    #   (remove|delete) (track|song|title) {track} from playlist {playlist}
    #   (remove|delete) (album|record) {album} from playlist {playlist}
    # Return: mesg_file (str), mesg_info (dict)  
    self.log.debug(f"MpcClient.delete_from_playlist() called with phrase: {phrase}")
    phrase = " ".join(phrase)            # convert list back to string
    key = re.split(" from playlist ", phrase)
    if len(key) == 1:                    # did not find "from playlist"
      self.log.debug("MpcClient.delete_from_playlist() ERROR 'from playlist' not found in phrase")
      return "to_playlist_missing", {} 
    music_name = key[0]
    playlist_name = key[1] 
    self.log.debug(f"MpcClient.delete_from_playlist() music_name: {music_name} playlist_name: {playlist_name}")

    # verify playlist exists
    rc = self.get_playlist(playlist_name) 
    if music_info.tracks_or_urls == []:    # playlist not found
      self.log.debug(f"MpcClient.delete_from_playlist() did not find playlist_name: {playlist_name}")
      mesg_info = {"playlist_name": playlist_name}
      return "missing_playlist", mesg_info
    
    # verify track or album exists  
    music_info = self.search_library(music_name) 
    if music_info.tracks_or_urls == None:
      self.log.debug(f"MpcClient.delete_from_playlist() did not find track or album: {music_name}")
      mesg_info = {"playlist_name": playlist_name, "music_name": music_name} 
      return "playlist_missing_track", mesg_info
    self.log.debug(f"MpcClient.delete_from_playlist() music_info.tracks_or_urls: {music_info.tracks_or_urls}")
    track_id = self.get_id_from_uri(music_info.tracks_or_urls)
    self.log.debug("MpcClient.delete_from_playlist() track_id = "+track_id)
    # TODO: finish code
    return "ok_its_done", {}

  def list_playlists(self):
    # Speak all saved playlists
    # Return: Music_info object  
    mesg_file = ""
    mesg_info = {}
    cmd = "/usr/bin/mpc lsplaylists"
    self.log.debug(f"MpcClient.list_playlists(): cmd: {cmd}")
    rc = 0
    try:
      p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
      stdout, stderr = p.communicate()
      playlists = str(stdout.decode("utf-8")).replace("\n", " ").strip()
      rc = p.returncode 
      self.log.debug(f"MpcClient.list_playlists(): playlists: {playlists} rc: {rc}")
    except subprocess.CalledProcessError as e:          
      self.log.error(f"MpcClient.list_playlists(): e.returncode: {e.returncode}")
    if len(playlists) == 0:                # no playlists found
      self.log.debug(f"MpcClient.list_playlists(): cmd: {cmd}")
      mesg_info = {}
      mesg_file = "playlists_not_found"
    else:                                  # found - add "and" before the last playlist name
      pos = playlists.rfind(" ")
      self.log.debug(f"MpcClient.list_playlists(): playlists found pos: {pos} len(playlists): {len(playlists)}")
      if pos > -1:                         # a space was found
        playlists =  playlists[:pos] + " and " + playlists[pos + 1:] # put "and" after the last space
        mesg_file = "list_playlists" 
      else:                                # just one playlist  
        mesg_file = "list_playlist"
      mesg_info = {"playlists": playlists}  
    return mesg_file, mesg_info 

  def get_matching_stations(self, field_index, search_name):
    # Search for radio stations by genre, country, or language
    # param: field_index: field number to search on 
    #        search_name: station, genre, language or country to search for
    # Sample line from radio.stations.csv:
    #   "radio paradise", "pop|top 40", "the united states", "english", "no ads", "http://stream.radioparadise.com/flac"
    # Return: list of URLs of station or None when not found   
    self.log.debug(f"MpcClient.get_matching_stations() field_index: {field_index} search_name: {search_name}")
    station_urls = []                      # reset list of station indexes that match
    num_hits = 0
    index = 0
    for next_line in self.list_lines:
      if search_name in next_line[field_index].strip():
        station_urls.append(next_line[5])  # append URL to list
        self.log.debug(f"MpcClient.get_matching_stations() matching URL: {next_line[5]}") 
        num_hits += 1
        if num_hits == 1:                  # first station is what will be playing
          self.station_name = next_line[0].strip()
          self.station_genre = next_line[1].strip()
          self.station_country = next_line[2].strip()
          self.station_language = next_line[3].strip()
          self.station_ads = next_line[4].strip()
          self.station_url = next_line[5].strip()
        elif num_hits == self.max_queued:  # that"s enough URLs
          self.log.debug(f"MpcClient.get_matching_stations() reached max_queued: {self.max_queued}")  
          break
      index += 1  
    if num_hits == 0:                      # music not found
      self.log.debug(f"MpcClient.get_matching_stations() did not find {self.request_type} {search_name} in field number {field_index}") 
      return None
    random.shuffle(station_urls)           # shuffle URLs
    return station_urls                    # list of matching station URLs

  def get_stations(self, search_name):
    # Return radio station URLs by genre, country, language, station name, or a random one
    # param: search_name: item to search for 
    # Return: music_info object  
    self.log.debug(f"MpcClient.get_stations() self.request_type: {self.request_type} search_name: {search_name}")
    mesg_info = {}
    tracks_or_urls = []
    stations_file = "f{self.base_dir}/skills/user_skills/mpc/radio.stations.csv"
    if not os.path.exists(f"{stations_file}"): # radio station file does not exist
      self.log.debug(f"MpcClient.get_stations() file {stations_file} not found")
      return Music_info("none", "file_not_found", {"file": "radio.stations.csv"}, None) 
    self.mpc_cmd("clear")                  # clear the queue
    input_file = open(f"{stations_file}", "r+")
    reader_file = csv.reader(input_file)
    self.list_lines = list(reader_file)    # convert to list
    num_lines = len(self.list_lines)       # number of saved radio stations
    self.log.debug(f"MpcClient.get_stations() num_lines: {num_lines}")
    match self.request_type:
      case "random":
        indices = random.sample(range(1, num_lines), self.max_queued)
        for next_index in indices:
          self.log.debug(f"MpcClient.get_stations() next_index: {next_index}")
          next_url = self.list_lines[next_index][5].strip()
          self.log.debug(f"MpcClient.get_stations() random next_url: {next_url}")
          tracks_or_urls.append(next_url)
        mesg_file = "playing_radio"  
      case "genre":
        self.log.debug(f"MpcClient.get_stations() searching for station by genre: {search_name}") 
        tracks_or_urls = self.get_matching_stations(1, search_name)
        if tracks_or_urls == None:         # station not found
          self.log.debug(f"MpcClient.get_stations() did not find genre: {search_name}") 
          mesg_file = "radio_not_found"
          mesg_info = {"request_type": self.request_type, "search_name": search_name}
        else:
          mesg_file = "playing_genre"  
          mesg_info = {"genre_name": search_name} 
      case "country":
        self.log.debug(f"MpcClient.get_stations() searching for station from country {search_name}") 
        tracks_or_urls = self.get_matching_stations(2, search_name)
        if tracks_or_urls == None:         # country not found
          self.log.debug(f"MpcClient.get_stations() did not find country: {search_name}") 
          mesg_file = "country_not_found"
          mesg_info = {"country": search_name}
        else:
          mesg_file = "playing_country"  
          mesg_info = {"station_name": self.station_name, "country": search_name}
      case "language":
        self.log.debug(f"MpcClient.get_stations() searching for station in language: {search_name}") 
        tracks_or_urls = self.get_matching_stations(3, search_name)
        if tracks_or_urls == None:         # language not found
          self.log.debug(f"MpcClient.get_stations() did not find language: {search_name}") 
          mesg_file = "language_not_found"
          mesg_info = {"language": search_name} 
        else:
          mesg_file = "playing_language"  
          mesg_info = {"station_name": self.station_name, "language": search_name}
      case "station":
        self.log.debug(f"MpcClient.get_stations() searching for station named: {search_name}") 
        tracks_or_urls = self.get_matching_stations(0, search_name)
        if tracks_or_urls == None:         # station not found
          self.log.debug(f"MpcClient.get_stations() did not find station named: {search_name}") 
          mesg_file = "station_not_found"
          mesg_info = {"station": search_name}
        else:
          mesg_file = "playing_country"  
          mesg_info = {"station_name": search_name}
      case _:                              # not expected
        self.log.debug(f"MpcClient.get_stations() INTERNAL ERROR: unexpected request_type: {self.request_type}")
        mesg_info = {"function": "mpcclient.get_stations"}
        mesg_file = "internal_error"
    return Music_info("radio", mesg_file, mesg_info, tracks_or_urls)  

  def parse_radio(self, utterance):
    # Parse the request to play a radio station
    # param: utterance from user
    # Vocabulary:
    #   play (the|) radio
    #   play music (on the|on my|) radio
    #   play genre {genre} (on the|on my|) radio
    #   play station {station} (on the|on my|) radio
    #   play (the|) (radio|) station {station}
    #   play (the|) radio (from|from country|from the country) {country}
    #   play (the|) radio (spoken|) (in|in language|in the language) {language}
    #   play (another|a different|next) (radio|) station
    #   (different|next) (radio|) station
    # Return: Music_info object 
    self.mpc_cmd("repeat", "on")              # never stop playing the radio
    self.log.debug(f"MpcClient.parse_radio() utterance: {utterance}")  
    utterance = utterance.replace("on the ", "") # remove unnecessary words
    utterance = utterance.replace("on my ", "")
    utterance = utterance.replace("the ", "")
    utterance = utterance.replace(" a ", " ")
    self.log.debug(f"MpcClient.parse_radio() cleaned up utterance: "+utterance)  
    words = utterance.split()              # split request into words
    num_words = len(words)
    self.log.debug(f"MpcClient.parse_radio() num_words: {num_words}")  
    intent = "None"
    search_name = "None" 
    mesg_info = {}    
    tracks_or_urls = []
    match words[0]:                      
      case "different" | "next":  
        return Music_info("next", "none", mesg_info, tracks_or_urls)
      case "previous" | "last":  
        return Music_info("prev", "none", mesg_info, tracks_or_urls)
      case "play":      
        match words[1]:
          case "radio":
            if num_words == 2:             # no more words
              self.request_type = "random"
            elif words[2] == "station":
              if num_words == 3:
                self.request_type = "random"
              elif words[3] == "from":
                self.request_type = "country"
                search_name = words[4]   
              else:
                self.request_type = "station"
                search_name = words[3]
            elif words[2] == "from":
              self.request_type = "country"
              search_name = words[3]   
            elif words[2] == "spoken" or words[2] == "in":
              self.request_type = "language"
              search_name = words[3]     
            else: 
              self.request_type = "random" 
          case "music"|"any":
            self.request_type = "random"
          case "genre":
            self.request_type = "genre"
            search_name = words[2]
          case "station":
            self.request_type = "station" 
            search_name = words[2]       
          case other:
            if words[2] == "radio" or words[2] == "station": 
               self.request_type = "genre"
               search_name = words[1]
            else:
              self.request_type = "random"   
    music_info = self.get_stations(search_name) 
    return music_info
     
  def search_internet(self, utterance):
    # Search for music on the internet and if found, return all URLs in Music_info object 
    # param:  search term
    # Return: Music_info object 
    # Vocabulary:
    #   play (track|artist|album|) {music} (from|on) (the|) internet
    self.mpc_cmd("clear")                  # clear the queue
    mesg_file = "" 
    mesg_info = {}
    tracks_or_urls = []
    self.log.debug(f"MpcClient.search_internet() utterance: {utterance}")
    phrase = utterance.split(" ", 1)[1]    # remove first word (always "play"?)
    phrase = phrase.lower()                # fold to lower case
    phrase = phrase.replace("on youtube", "") # remove unnecessary words
    phrase = phrase.replace("in youtube", "")
    phrase = phrase.replace("from youtube", "")
    phrase = phrase.replace("from the internet", "") 
    phrase = phrase.replace("from internet", "")
    phrase = phrase.replace("on the internet", "") 
    self.log.debug(f"MpcClient.search_internet() searching for phrase: {phrase}")

    # the ytadd script takes around 5 seconds to add a URL - so limit results to 3
    results = YoutubeSearch(phrase, max_results=2).to_dict() # return a dictionary
    num_hits = len(results)
    if num_hits == 0:
      self.log.info("MpcClient.search_internet() did not find any music on the internet")
      mesg_file = "music_not_found"
      mesg_info = {"music_name": utterance}
    else:                                  # found music - queue it up
      random.shuffle(results)              # shuffle tracks
      for next_track in results: 
        suffix = next_track["url_suffix"]
        next_url = "http://youtube.com"+suffix
        self.log.debug(f"MpcClient.search_internet(): adding url: {next_url}")
        tracks_or_urls.append(next_url)
      mesg_file = None
      mesg_info = None 
    return Music_info("internet", mesg_file, mesg_info, tracks_or_urls)

  def stream_internet_music(self, music_info):
    # Stream music from the Internet using mpc 
    # param: Music_info object 
    self.log.debug("MpcClient.stream_internet_music() streaming all tracks from the Internet")
    for next_url in music_info.tracks_or_urls: # queue up tracks in mpc
      self.log.debug(f"MpcClient.stream_internet_music() streaming from URL: {next_url}")
      cmd = "/usr/local/sbin/ytadd "+next_url # add URL to mpc queue
      try:
        self.log.debug(f"MpcClient.stream_internet_music(): running command: {cmd}")
        result = subprocess.check_output(cmd, shell=True)
        self.log.debug(f"MpcClient.stream_internet_music(): result: {result}")
      except subprocess.CalledProcessError as e:
        self.log.error(f"MpcClient.stream_internet_music() e.returncode: {e.returncode}")
        return False
    if self.mpc_cmd("play") != True:        # Now play the queued up tracks
        self.log.debug("MpcClient.start_music(): mpc_cmd(play) failed")
        return False 

  def search_news(self, utterance):
    # search for NPR news 
    # param: text of the request
    # return: Music_info object
    url = "https://www.npr.org/podcasts/500005/npr-news-now"
    self.log.debug(f"MpcClient.search_news() utterance: {utterance} url: {url}") 
    mesg_info = {}
    mesg_file = "playing_npr"
    res = requests.get(url)
    page = res.text
    start_indx = page.find("audioUrl")
    if start_indx == -1:
      self.log.debug(f"MpcClient.search_news() cannot find NPR news URL") 
      mesg_file = "cannot_play_npr"
      return Music_info("none", mesg_file, {}, [])
    end_indx = start_indx + len("audioUrl")
    page = page[end_indx + 3:]
    end_indx = page.find("?")
    if end_indx == -1:
      self.log.debug(f"MpcClient.search_news() Parse error")
      mesg_file = "cannot_parse_npr"
      return Music_info("none", mesg_file, {}, [])
    self.log.debug(f"MpcClient.search_news() start_indx: {start_indx} end_indx: {end_indx} ")       
    new_url = page[:end_indx]
    new_url = new_url.replace("\\","")
    os.chdir(self.music_dir)               # write file to music directory
    cmd = f"wget {new_url}"
    self.log.debug(f"MpcClient.search_news() cwd: {os.getcwd()} cmd: {cmd}")
    os.system(cmd)                         # get the file with wget
    file_name = new_url.rsplit('/', 1)[-1]
    self.log.debug(f"MpcClient.search_news() mp3 file_name: {file_name}")
    self.mpc_cmd("update")                 # update so mpc can see new file
    return Music_info("news", mesg_file, mesg_info, [file_name])

