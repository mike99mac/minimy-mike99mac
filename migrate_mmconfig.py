#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

import yaml


DEFAULT_CONFIG = {
  "Advanced": {
    "CrappyAEC": "n",
    "InputDeviceId": "0",
    "InputLevelControlName": "",
    "LogLevel": "i",
    "AWSId": "",
    "AWSKey": "",
    "GoogleApiKeyPath": "install/my_google_key.json",
  },
  "Basic": {
    "NLP": {
      "UseRemote": "n",
    },
    "STT": {
      "UseRemote": "y",
      "Model": "base.en",
    },
    "TTS": {
      "Local": "m",
      "Remote": "p",
      "UseRemote": "y",
      "LocalVoice": "en_US-hfc_male-medium",
    },
    "OutputDeviceName": "",
    "OutputLevelControlName": "",
    "Platform": "l",
    "BaseDir": "",
    "Hub": "localhost",
    "MusicDir": None,
    "WakeWords": ["computer", "internet"],
    "RoomToHost": None,
  },
}


def deep_copy_yaml(data):
  return yaml.safe_load(yaml.safe_dump(data))


def merge_dict(target, source):
  for key, value in source.items():
    if isinstance(value, dict) and isinstance(target.get(key), dict):
      merge_dict(target[key], value)
    else:
      target[key] = value


def flatten_sections(raw_cfg):
  if isinstance(raw_cfg, list):
    merged = {}
    for item in raw_cfg:
      if isinstance(item, dict):
        merged.update(item)
    return merged
  if isinstance(raw_cfg, dict):
    return raw_cfg
  raise ValueError("Config must be a YAML dict or a list of dict sections")


def migrate_stt_config(config):
  basic = config.setdefault("Basic", {})
  stt = basic.setdefault("STT", {})
  default_model = DEFAULT_CONFIG["Basic"]["STT"]["Model"]

  legacy_hub_model = stt.pop("HubModel", None)
  legacy_spoke_model = stt.pop("SpokeModel", None)
  top_level_hub_model = basic.pop("HubModel", None)
  top_level_spoke_model = basic.pop("SpokeModel", None)

  for candidate in (
    legacy_hub_model,
    legacy_spoke_model,
    top_level_hub_model,
    top_level_spoke_model,
  ):
    if candidate and ("Model" not in stt or stt["Model"] == default_model):
      stt["Model"] = candidate
      break


def migrate_key_locations(config):
  advanced = config.setdefault("Advanced", {})
  basic = config.setdefault("Basic", {})

  for key in ("AWSId", "AWSKey", "GoogleApiKeyPath"):
    if key in basic:
      advanced[key] = basic.pop(key)

  for key in ("Platform", "OutputDeviceName", "OutputLevelControlName"):
    if key in advanced:
      basic[key] = advanced.pop(key)

  for old_path, new_path in (
    (("Advanced", "STT", "UseRemote"), ("Basic", "STT", "UseRemote")),
    (("Advanced", "TTS", "UseRemote"), ("Basic", "TTS", "UseRemote")),
    (("Advanced", "TTS", "Local"), ("Basic", "TTS", "Local")),
    (("Advanced", "TTS", "Remote"), ("Basic", "TTS", "Remote")),
    (("Advanced", "TTS", "LocalVoice"), ("Basic", "TTS", "LocalVoice")),
    (("Advanced", "NLP", "UseRemote"), ("Basic", "NLP", "UseRemote")),
  ):
    move_nested_value(config, old_path, new_path)


def move_nested_value(config, old_path, new_path):
  old_parent = config
  for key in old_path[:-1]:
    if not isinstance(old_parent, dict) or key not in old_parent:
      return
    old_parent = old_parent[key]

  old_leaf = old_path[-1]
  if not isinstance(old_parent, dict) or old_leaf not in old_parent:
    return

  value = old_parent.pop(old_leaf)
  if old_parent == {}:
    cleanup_empty_parents(config, old_path[:-1])

  new_parent = config
  for key in new_path[:-1]:
    if key not in new_parent or not isinstance(new_parent[key], dict):
      new_parent[key] = {}
    new_parent = new_parent[key]

  new_leaf = new_path[-1]
  new_parent[new_leaf] = value


def cleanup_empty_parents(config, path):
  while path:
    parent = config
    for key in path[:-1]:
      parent = parent.get(key, {})
      if not isinstance(parent, dict):
        return
    leaf = path[-1]
    child = parent.get(leaf)
    if isinstance(child, dict) and not child:
      parent.pop(leaf, None)
      path = path[:-1]
      continue
    return


def migrate(raw_cfg):
  config = deep_copy_yaml(DEFAULT_CONFIG)
  merge_dict(config, flatten_sections(raw_cfg))
  migrate_key_locations(config)
  migrate_stt_config(config)
  return [
    {"Advanced": config["Advanced"]},
    {"Basic": config["Basic"]},
  ]


def main():
  parser = argparse.ArgumentParser(
    description="Migrate an mmconfig.yml file to the current Minimy config format."
  )
  parser.add_argument(
    "config",
    nargs="?",
    default="install/mmconfig.yml",
    help="Path to the mmconfig.yml file to migrate",
  )
  parser.add_argument(
    "--stdout",
    action="store_true",
    help="Write migrated YAML to stdout instead of overwriting the file",
  )
  args = parser.parse_args()

  config_path = Path(args.config)
  if not config_path.exists():
    print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
    return 1

  with config_path.open("r") as handle:
    raw_cfg = yaml.safe_load(handle)

  migrated = migrate(raw_cfg)
  rendered = yaml.safe_dump(migrated, sort_keys=False)

  if args.stdout:
    sys.stdout.write(rendered)
  else:
    with config_path.open("w") as handle:
      handle.write(rendered)
    print(f"Migrated config written to {config_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
