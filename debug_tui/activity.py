"""Translates raw minimy bus messages into short, human-readable activity
lines - "what's happening right now", distinct from the verbose raw
logs. Deliberately curated: most message types return None (skipped),
since the whole point is a simplified summary, not a second log feed.

Pure function, no UI/bus dependency, so it's testable without a real
connection - see bus.py's on_activity() for how this gets wired up.
"""

def summarize_message(msg_type, data=None):
    """Returns a short status string for a bus message worth surfacing
    in the activity pane, or None if this message type should be
    skipped (the vast majority - this is a curated summary, not a
    second log)."""
    data = data or {}

    if msg_type == "recognizer_loop:utterance":
        utterances = data.get("utterances") or [""]
        return f'→ heard: "{utterances[0]}"'

    if msg_type == "speak":
        utterance = data.get("utterance", "")
        return f'← spoke: "{utterance}"'

    if msg_type == "skill.execution.start":
        skill_id = data.get("skill_id", "unknown")
        return f"▶ {skill_id} handling"

    if msg_type == "skill.execution.complete":
        skill_id = data.get("skill_id", "unknown")
        return f"✓ {skill_id} complete"

    if msg_type == "skill.execution.failed":
        skill_id = data.get("skill_id", "unknown")
        return f"✗ {skill_id} failed"

    if msg_type == "audio.playing":
        return "🔊 playing audio"

    if msg_type == "audio.stopped":
        return "🔇 audio stopped"

    if msg_type == "wakeword.detected":
        return "👂 wake word detected"

    return None
