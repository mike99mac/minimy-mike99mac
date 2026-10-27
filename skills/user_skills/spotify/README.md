# Spotify skill

Manages a headless **go-librespot** Spotify Connect receiver for Minimy.
Settings are read from `install/config.yml` (read-only); go-librespot manages
its own state and credentials in `StateDir`.

## Configuration

Add a `Spotify` section under `Basic` in `install/config.yml`:

```yaml
- Basic:
    Spotify:
      Bin: go-librespot
      Name: Minimy
      ApiPort: 3678
      CacheDir: /home/<user>/.cache/go-librespot
      StateDir: /home/<user>/.config/go-librespot
