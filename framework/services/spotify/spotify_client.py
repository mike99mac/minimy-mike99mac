"""
Spotify Web API + Spotify Connect helper for MpcClient.
Search via spotipy; play by transferring playback to the go-librespot device.
"""
import logging
import os
import socket
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheFileHandler

from framework.util.music_info import Music_info

SCOPE = "user-modify-playback-state user-read-playback-state"
REDIRECT = "http://127.0.0.1:8888/callback"
LIBRESPOT_PORT = 3678


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

  # ---------- Internal ----------

  def _service_running(self) -> bool:
    try:
      with socket.create_connection(("localhost", LIBRESPOT_PORT), timeout=2):
        return True
    except OSError:
      return False

  def _device_id(self):
    try:
      devices = self.sp.devices()
    except Exception as e:
      self.log.error(f"Spotify: devices() failed: {e}")
      return None
    for d in devices.get("devices", []):
      if d.get("name") == self.device_name:
        return d["id"]
    self.log.warning(
      f"Spotify: device '{self.device_name}' not found in Connect list. "
      f"Open Spotify on your phone, tap the device once to pair, then retry."
    )
    return None

  # ---------- Search ----------

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

  # ---------- Playback ----------

  def _play(self, track_uri=None, context_uri=None) -> bool:
    device_id = self._device_id()
    if not device_id:
      return False
    try:
      self.sp.transfer_playback(device_id=device_id, force_play=False)
      time.sleep(0.4)
      if context_uri:
        self.sp.start_playback(device_id=device_id, context_uri=context_uri)
      else:
        self.sp.start_playback(device_id=device_id, uris=[track_uri])
      return True
    except Exception as e:
      self.log.error(f"Spotify: playback failed: {e}")
      return False

  # ---------- Public ----------

  def find_and_play(self, name, artist, kind):
    """kind: 'track' | 'artist' | 'album'. Returns Music_info or None."""
    if not self.enabled:
      return None
    if not self._service_running():
      self.log.warning("Spotify: go-librespot is not running on port 3678")
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
