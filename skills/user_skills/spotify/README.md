# Spotify skill

This skill manages a headless librespot Spotify Connect receiver for Minimy.
It is intended to start and pair a local receiver instance, without storing
Spotify credentials in the Minimy repository.

## What the skill does

- starts librespot with the device name `Minimy`
- keeps credentials in `~/.cache/librespot`
- supports a one-time device-auth pairing flow
- can stop or report the status of the receiver

## Environment variables

Set these before starting Minimy if you need different defaults:

```bash
export LIBRESPOT_BIN="$HOME/.cargo/bin/librespot"
export LIBRESPOT_CACHE="$HOME/.cache/librespot"
export LIBRESPOT_NAME="Minimy"
```

## Initial pairing (headless Raspberry Pi)

From the Pi terminal, run:

```bash
$LIBRESPOT_BIN --name "$LIBRESPOT_NAME" \
  --enable-device-auth \
  --cache "$LIBRESPOT_CACHE"
```

Then open the printed URL in a browser on any machine:

```text
https://spotify.com/pair
```

Enter the provided code and approve the pairing. Once the browser reports that
pairing succeeded, stop librespot with Ctrl-C. After that, Minimy can start it
again without repeated authentication.

## Voice commands

The skill responds to simple commands such as:

- “start Spotify”
- “stop Spotify”
- “pair Spotify”
- “what is Spotify”

This is a receiver-management skill. It does not perform Spotify catalog
searching or playback control by itself; librespot handles the local receiver,
and a separate Spotify controller/API layer would be needed for full music
selection and playback.

## Logs

The skill logs output to:

```text
$SVA_BASE_DIR/logs/spotify.log
```

For example:

```bash
tail -f "$SVA_BASE_DIR/logs/spotify.log"
```

## Files created

- `skills/user_skills/spotify/__init__.py`
- `skills/user_skills/spotify/README.md`
