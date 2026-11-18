#!/usr/bin/env python3
import sys

from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheFileHandler

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-modify-playback-state user-read-playback-state"


def main():
  if len(sys.argv) != 4:
    print(__doc__.strip())
    sys.exit(2)

  client_id, client_secret, cache_path = sys.argv[1], sys.argv[2], sys.argv[3]
  auth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_handler=CacheFileHandler(cache_path=cache_path),
    open_browser=False,
  )

  print()
  print("=" * 72)
  print("SPOTIFY AUTHORIZATION")
  print("=" * 72)
  print("Open this URL in a browser on any device:")
  print()
  print(auth.get_authorize_url())
  print()
  print(f"Your browser redirects to: {REDIRECT_URI}?code=...")
  print("The page will fail to load — that is normal.")
  print("Copy the FULL URL from the address bar and paste it below.")
  print("=" * 72)

  url = input("\nPaste the redirected URL: ").strip()
  if "code=" in url:
    url = url.split("code=")[1].split("&")[0]

  auth.get_access_token(url, check_cache=False, as_dict=False)
  print(f"\nRefresh token cached at {cache_path}")


if __name__ == "__main__":
  main()
