"""
Spotify Web API + Spotify Connect helper for MpcClient.
Search via spotipy, play via calling soloist ctl on the local Soloist daemon.
"""
import logging
import os
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheFileHandler
from framework.util.music_info import Music_info

SCOPE = "user-modify-playback-state user-read-playback-state"
REDIRECT = "http://127.0.0.1:8888/callback"


class SpotifyClient:
  def __init__(self, cfg, base_dir: str):
    self.log = logging.getLogger(__name__)
    self.base_dir = base_dir
    self.enabled = False
    self.sp = None
    self.device_name = cfg.get_cfg_val("Basic.Spotify.DeviceName") or "Minimy"

    client_id = cfg.get_cfg_val("Basic.Spotify.ClientId") or ""
    client_secret = cfg.get_cfg_val("Basic.Spotify.ClientSecret") or ""
    if not client_id or not client_secret:
      self.log.info("Spotify: credentials absent — disabled")
      return

    cache_path = os.path.expanduser("~/.config/spotify/credentials")
    if not os.path.exists(cache_path):
      self.log.warning(f"Spotify: OAuth cache missing at {cache_path} — disabled")
      return

    try:
      auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT,
        scope=SCOPE,
        cache_handler=CacheFileHandler(cache_path=cache_path),
        open_browser=False,
      )
      self.sp = spotipy.Spotify(auth_manager=auth)
      self.enabled = True
      self.log.info(f"Spotify: enabled (device='{self.device_name}')")
    except Exception as e:
      self.log.error(f"Spotify: init failed: {e}")

  # Search

  def _search_track(self, name, artist):
    q = name if not artist or artist == "unknown_artist" else f"{name} artist:{artist}"
    r = self.sp.search(q=q, type="track", limit=1)
    items = r.get("tracks", {}).get("items", [])
    return items[0] if items else None

  def _search_artist(self, name):
    r = self.sp.search(q=name, type="artist", limit=1)
    items = r.get("artists", {}).get("items", [])
    return items[0] if items else None

  def _search_album(self, name, artist):
    q = name if not artist or artist == "unknown_artist" else f"{name} artist:{artist}"
    r = self.sp.search(q=q, type="album", limit=1)
    items = r.get("albums", {}).get("items", [])
    return items[0] if items else None

  # Playback

  def _play(self, track_uri=None, context_uri=None) -> bool:
    uri = track_uri or context_uri
    if not uri:
      return False
    try:
      subprocess.run(
        ["soloist", "ctl", "play", uri],
        check=True,
        timeout=10
      )
      return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
      self.log.error(f"soloist ctl play failed: {e}")
      return False

  # Public

  def find_and_play(self, name, artist, kind):
    """kind: 'track' | 'artist' | 'album'. Returns Music_info or None."""
    if not self.enabled:
      return None

    try:
      if kind == "track":
        item = self._search_track(name, artist)
        if item and self._play(track_uri=item["uri"]):
          return Music_info("spotify", "playing_track", {
            "track_name": item["name"],
            "artist_name": item["artists"][0]["name"],
            "album_name": item["album"]["name"],
          }, [])
      elif kind == "artist":
        item = self._search_artist(name)
        if item and self._play(context_uri=item["uri"]):
          return Music_info("spotify", "playing_artist", {
            "artist_name": item["name"],
          }, [])
      elif kind == "album":
        item = self._search_album(name, artist)
        if item and self._play(context_uri=item["uri"]):
          return Music_info("spotify", "playing_album", {
            "album_name": item["name"],
            "artist_name": item["artists"][0]["name"],
          }, [])
    except Exception as e:
      self.log.error(f"Spotify: search/play error: {e}")
    return None
