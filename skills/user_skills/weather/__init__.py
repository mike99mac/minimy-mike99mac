#!/usr/bin/env python3
"""
WeatherSkill - US weather via weather.gov + Open-Meteo + Nominatim fallback,
international via Open-Meteo + Nominatim. No API keys needed.
Run by the bash loader: cd skills/user_skills/weather && python3 __init__.py "$PWD"
"""

import re
import time
import threading
import requests

from skills.sva_base import SimpleVoiceAssistant
from framework.util.utils import us_abbrev_to_state


# Open‑Meteo weather codes to spoken description
WMO_CODES = {
  0: "clear sky",
  1: "mainly clear", 2: "partly cloudy", 3: "overcast",
  45: "fog", 48: "depositing rime fog",
  51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
  56: "light freezing drizzle", 57: "dense freezing drizzle",
  61: "slight rain", 63: "moderate rain", 65: "heavy rain",
  66: "light freezing rain", 67: "heavy freezing rain",
  71: "slight snowfall", 73: "moderate snowfall", 75: "heavy snowfall",
  77: "snow grains",
  80: "slight rain showers", 81: "moderate rain showers",
  82: "violent rain showers",
  85: "slight snow showers", 86: "heavy snow showers",
  95: "thunderstorm", 96: "thunderstorm with slight hail",
  99: "thunderstorm with heavy hail",
}

# State capitals used for state‑only queries
STATE_CAPITALS = {
  "alabama": "Montgomery, Alabama",
  "alaska": "Juneau, Alaska",
  "arizona": "Phoenix, Arizona",
  "arkansas": "Little Rock, Arkansas",
  "california": "Sacramento, California",
  "colorado": "Denver, Colorado",
  "connecticut": "Hartford, Connecticut",
  "delaware": "Dover, Delaware",
  "florida": "Tallahassee, Florida",
  "georgia": "Atlanta, Georgia",
  "hawaii": "Honolulu, Hawaii",
  "idaho": "Boise, Idaho",
  "illinois": "Springfield, Illinois",
  "indiana": "Indianapolis, Indiana",
  "iowa": "Des Moines, Iowa",
  "kansas": "Topeka, Kansas",
  "kentucky": "Frankfort, Kentucky",
  "louisiana": "Baton Rouge, Louisiana",
  "maine": "Augusta, Maine",
  "maryland": "Annapolis, Maryland",
  "massachusetts": "Boston, Massachusetts",
  "michigan": "Lansing, Michigan",
  "minnesota": "St. Paul, Minnesota",
  "mississippi": "Jackson, Mississippi",
  "missouri": "Jefferson City, Missouri",
  "montana": "Helena, Montana",
  "nebraska": "Lincoln, Nebraska",
  "nevada": "Carson City, Nevada",
  "new hampshire": "Concord, New Hampshire",
  "new jersey": "Trenton, New Jersey",
  "new mexico": "Santa Fe, New Mexico",
  "new york": "Albany, New York",
  "north carolina": "Raleigh, North Carolina",
  "north dakota": "Bismarck, North Dakota",
  "ohio": "Columbus, Ohio",
  "oklahoma": "Oklahoma City, Oklahoma",
  "oregon": "Salem, Oregon",
  "pennsylvania": "Harrisburg, Pennsylvania",
  "rhode island": "Providence, Rhode Island",
  "south carolina": "Columbia, South Carolina",
  "south dakota": "Pierre, South Dakota",
  "tennessee": "Nashville, Tennessee",
  "texas": "Austin, Texas",
  "utah": "Salt Lake City, Utah",
  "vermont": "Montpelier, Vermont",
  "virginia": "Richmond, Virginia",
  "washington": "Olympia, Washington",
  "west virginia": "Charleston, West Virginia",
  "wisconsin": "Madison, Wisconsin",
  "wyoming": "Cheyenne, Wyoming",
}

# Translate common non‑English country names to their English equivalents
COUNTRY_TRANSLATIONS = {
  "deutschland": "Germany",
  "france": "France",
  "italia": "Italy",
  "españa": "Spain",
  "日本": "Japan",
  "中国": "China",
  "россия": "Russia",
  "brasil": "Brazil",
  "méxico": "Mexico",
  "canada": "Canada",
  "australia": "Australia",
  "united kingdom": "United Kingdom",
  # Add others as needed
}


class WeatherSkill(SimpleVoiceAssistant):

  def __init__(self, bus=None, timeout=5):
    super().__init__(skill_id="weather_skill", skill_category="user")
    self.timeout = timeout
    self.busy = False

    self.register_intent("Q", "weather",     "what", self.handle_msg)
    self.register_intent("Q", "forecast",    "what", self.handle_msg)
    for verb in ("what", "is", "will", "did"):
      self.register_intent("Q", "temperature", verb, self.handle_msg)

    self.default_lat, self.default_lon, self.default_name = self._get_default_location()
    self.default_state = None
    if self.default_name:
      parts = self.default_name.split(", ")
      if len(parts) >= 2:
        state_name = parts[-2]
        reverse_abbrev = {v.lower(): k for k, v in us_abbrev_to_state.items()}
        self.default_state = reverse_abbrev.get(state_name.lower())
        if not self.default_state:
          self.default_state = state_name.upper()

    self.us_states = set()
    for abbr, full in us_abbrev_to_state.items():
      self.us_states.add(abbr.lower())
      self.us_states.add(full.lower())

    self.log.info("WeatherSkill ready. Default: %s", self.default_name)

  # ------------------------------------------------------------
  # Default location via ipinfo.io
  # ------------------------------------------------------------
  def _get_default_location(self):
    try:
      resp = requests.get("https://ipinfo.io/json", timeout=self.timeout)
      data = resp.json()
      city = data.get("city", "")
      region = data.get("region", "")
      country = data.get("country", "")
      lat, lon = map(float, data.get("loc", "0,0").split(","))

      country_name = "United States" if country == "US" else country
      parts = [p for p in (city, region, country_name) if p]
      name = ", ".join(parts) if parts else "unknown location"
      self.log.debug("Geo-IP default: %s (%s, %s)", name, lat, lon)
      return lat, lon, name
    except Exception as e:
      self.log.warning("Could not determine default location: %s", e)
      return None, None, "unknown location"

  # ------------------------------------------------------------
  # Intent handler
  # ------------------------------------------------------------
  def handle_msg(self, msg):
    if self.busy:
      self.log.warning("WeatherSkill is busy – ignoring request")
      return

    self.busy = True
    try:
      sentence = msg["payload"]["utt"]["sentence"]
      self.log.debug("Processing: %s", sentence)

      location_str = self._extract_location(sentence)
      if location_str:
        lat, lon, name = self._geocode(location_str)
        if lat is None:
          self.speak(f"Sorry, I couldn't find {location_str}.")
          return
      else:
        lat, lon, name = self.default_lat, self.default_lon, self.default_name
        if lat is None:
          self.speak("I don't have a default location. Please set one.")
          return

      current_desc, current_temp, daily_summary = self._get_weather(lat, lon)

      parts = name.split(", ")
      if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].isalpha():
        full = us_abbrev_to_state.get(parts[-1].upper())
        if full:
          parts[-1] = full
          name = ", ".join(parts)

      say1 = f"It is currently {current_desc} and {current_temp} degrees in {name}."
      say2 = f"The forecast: {daily_summary}."
      say2 = say2.replace("mph", "miles per hour")

      self.speak(f"{say1} {say2}")

    except Exception as e:
      self.log.error("WeatherSkill failed: %s", e, exc_info=True)
      self.speak("I'm sorry, I couldn't fetch the weather right now.")
    finally:
      self.busy = False
      time.sleep(0.5)

  # ------------------------------------------------------------
  # Location extraction
  # ------------------------------------------------------------
  def _extract_location(self, sentence):
    for prep in [" in ", " for ", " at ", " near "]:
      idx = sentence.lower().find(prep)
      if idx != -1:
        loc = sentence[idx + len(prep):].strip().rstrip("?")
        if loc:
          return loc

    words = sentence.split()
    starters = {"what's", "what", "how's", "how", "is", "will", "did",
                "temperature", "weather", "forecast", "the"}
    while words and words[0].lower() in starters:
      words.pop(0)
    if words:
      return " ".join(words)
    return None

  # ------------------------------------------------------------
  # Geocoding – routes to US or international, with fallback for city‑only
  # ------------------------------------------------------------
  def _geocode(self, location):
    for conj in (" and ", " & "):
      if conj in location:
        a, b = location.split(conj, 1)
        if b.strip().lower() in self.us_states:
          location = a.strip() + " " + b.strip()
          break

    loc_lower = location.lower().strip()

    if loc_lower in self.us_states:
      capital = STATE_CAPITALS.get(loc_lower)
      if capital:
        self.log.debug("State-only query, using capital: %s -> %s", location, capital)
        location = capital
        loc_lower = location.lower()

    parts = location.split()
    last_word = parts[-1].lower() if parts else ""
    is_us = (last_word in self.us_states)
    if not is_us and loc_lower in self.us_states:
      is_us = True

    # Single word, not a state → try international first, then US
    if not is_us and len(parts) == 1 and self.default_state:
      lat, lon, name = self._geocode_international(location)
      if lat is not None:
        # If the result is in the US, force the US path so we get the correct state
        if name and name.endswith("United States"):
          self.log.debug("International match found a US city, falling back to US path")
          return self._geocode_us(f"{location}, {self.default_state}")
        return lat, lon, name

      # International failed or returned non‑US, try US with default state
      us_location = f"{location}, {self.default_state}"
      lat, lon, name = self._geocode_us(us_location)
      if lat is not None:
        return lat, lon, name
      self.log.warning("No geocoding results for '%s'", location)
      return None, None, location

    if is_us:
      return self._geocode_us(location)

    return self._geocode_international(location)

  # ------------------------------------------------------------
  # US geocoding – weather.gov → Open‑Meteo (US) → Nominatim (US)
  # ------------------------------------------------------------
  def _geocode_us(self, location):
    if "," not in location:
      words = location.split()
      if len(words) >= 2:
        city = " ".join(words[:-1])
        state = words[-1]
      else:
        city = location
        state = self.default_state or ""
    else:
      parts = location.split(",")
      city = parts[0].strip()
      state = parts[1].strip()

    if len(state) == 2 and state.isalpha():
      state_abbr = state.upper()
      state_full = us_abbrev_to_state.get(state_abbr, state)
    else:
      reverse_abbrev = {v.lower(): k for k, v in us_abbrev_to_state.items()}
      state_abbr = reverse_abbrev.get(state.lower(), state.upper())
      state_full = state

    city_variants = [city]
    if " " in city:
      city_variants.append(city.replace(" ", ""))

    for city_variant in city_variants:
      query = f"{city_variant}, {state_abbr}"
      display_name = f"{city_variant.title()}, {state_full.title()}, United States"

      lat, lon = self._geocode_us_weather_gov(query)
      if lat is not None:
        return lat, lon, display_name

      lat, lon = self._geocode_openmeteo(query, us_only=True)
      if lat is not None:
        return lat, lon, display_name

      lat, lon = self._geocode_nominatim(query, country_code="us")
      if lat is not None:
        return lat, lon, display_name

    # If all variants fail, try just the city
    lat, lon = self._geocode_openmeteo(city, us_only=True)
    if lat is not None:
      return lat, lon, display_name

    self.log.warning("No US geocoding results for '%s'", location)
    return None, None, location

  def _geocode_us_weather_gov(self, query):
    try:
      resp = requests.get(
        "https://forecast.weather.gov/zipcity.php",
        params={"inputstring": query, "btnSearch": "Go"},
        timeout=8,
        allow_redirects=True,
      )
      final_url = resp.url
      match = re.search(r"[?&]lat=([0-9.]+)&lon=(-?[0-9.]+)", final_url)
      if match:
        return float(match.group(1)), float(match.group(2))
      match = re.search(r"textField1=([0-9.]+)&textField2=(-?[0-9.]+)", final_url)
      if match:
        return float(match.group(1)), float(match.group(2))
      self.log.warning("weather.gov URL didn't contain coordinates: %s", final_url)
    except Exception as e:
      self.log.warning("weather.gov geocoding error: %s", e)
    return None, None

  # ------------------------------------------------------------
  # International geocoding – Open‑Meteo → comma fallback (no Nominatim for single words)
  # ------------------------------------------------------------
  def _geocode_international(self, location):
    parts = location.split()
    is_single_word = len(parts) == 1

    lat, lon = self._geocode_openmeteo(location, us_only=False)
    if lat is not None:
      name = self._build_international_name(lat, lon, location)
      return lat, lon, name

    if not is_single_word and " " in location and "," not in location:
      comma_loc = re.sub(r"\s+", ", ", location, 1)
      lat, lon = self._geocode_openmeteo(comma_loc, us_only=False)
      if lat is not None:
        name = self._build_international_name(lat, lon, comma_loc)
        return lat, lon, name

    # Do not fall back to Nominatim for single‑word queries (too many false positives)
    if is_single_word:
      return None, None, location

    lat, lon = self._geocode_nominatim(location, country_code=None)
    if lat is not None:
      name = self._build_international_name(lat, lon, location)
      return lat, lon, name

    return None, None, location

  def _build_international_name(self, lat, lon, fallback_query):
    country = self._get_country_from_geocoding(lat, lon)
    # Translate non‑English country names
    if country and country.lower() in COUNTRY_TRANSLATIONS:
      country = COUNTRY_TRANSLATIONS[country.lower()]

    parts = fallback_query.split(",")
    if len(parts) >= 2:
      city = parts[0].strip()
    else:
      words = fallback_query.split()
      if len(words) >= 2:
        city = " ".join(words[:-1])
      else:
        city = fallback_query

    city = city.title()
    if country:
      return f"{city}, {country}"
    return fallback_query.title()

  def _get_country_from_geocoding(self, lat, lon):
    # Try Open-Meteo reverse
    name = self._reverse_geocode(lat, lon)
    if name:
      parts = name.split(", ")
      if parts:
        return parts[-1]

    # Try Nominatim reverse
    name = self._nominatim_reverse_geocode(lat, lon)
    if name:
      parts = name.split(", ")
      if parts:
        return parts[-1]
    return None

  # ------------------------------------------------------------
  # Open-Meteo helper (returns lat, lon or None)
  # ------------------------------------------------------------
  def _geocode_openmeteo(self, query, us_only=False):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": query, "count": 1, "language": "en", "format": "json"}
    if us_only:
      params["country"] = "US"
    try:
      resp = requests.get(url, params=params, timeout=self.timeout)
      resp.raise_for_status()
      data = resp.json()
      if "results" in data and data["results"]:
        r = data["results"][0]
        return r["latitude"], r["longitude"]
    except Exception as e:
      self.log.warning("Open-Meteo geocoding failed for '%s': %s", query, e)
    return None, None

  # ------------------------------------------------------------
  # Nominatim helper (forward geocoding)
  # ------------------------------------------------------------
  def _geocode_nominatim(self, query, country_code=None):
    try:
      params = {
        "q": query,
        "format": "json",
        "limit": 1,
      }
      if country_code:
        params["countrycodes"] = country_code
      headers = {"User-Agent": "Minimy/1.0"}
      resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params=params,
        headers=headers,
        timeout=self.timeout,
      )
      resp.raise_for_status()
      data = resp.json()
      if data:
        r = data[0]
        return float(r["lat"]), float(r["lon"])
    except Exception as e:
      self.log.warning("Nominatim geocoding failed for '%s': %s", query, e)
    return None, None

  # ------------------------------------------------------------
  # Nominatim reverse geocoding (lat/lon → display name)
  # ------------------------------------------------------------
  def _nominatim_reverse_geocode(self, lat, lon):
    try:
      params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,
        "addressdetails": 1,
      }
      headers = {"User-Agent": "Minimy/1.0"}
      resp = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params=params,
        headers=headers,
        timeout=self.timeout,
      )
      resp.raise_for_status()
      data = resp.json()
      if data:
        addr = data.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
        state = addr.get("state")
        country = addr.get("country")
        parts = [city, state, country]
        return ", ".join(p for p in parts if p)
    except Exception as e:
      self.log.warning("Nominatim reverse geocoding failed: %s", e)
    return None

  # ------------------------------------------------------------
  # Reverse geocode (lat/lon → display name) using Open-Meteo
  # ------------------------------------------------------------
  def _reverse_geocode(self, lat, lon):
    try:
      url = "https://geocoding-api.open-meteo.com/v1/search"
      params = {"name": f"{lat},{lon}", "count": 1, "language": "en", "format": "json"}
      resp = requests.get(url, params=params, timeout=self.timeout)
      resp.raise_for_status()
      data = resp.json()
      if "results" in data and data["results"]:
        r = data["results"][0]
        name_parts = [r.get("name", ""), r.get("admin1", ""), r.get("country", "")]
        return ", ".join(p for p in name_parts if p)
    except Exception:
      pass
    return None

  # ------------------------------------------------------------
  # Weather fetching (Open-Meteo)
  # ------------------------------------------------------------
  def _get_weather(self, lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
      "latitude": lat,
      "longitude": lon,
      "current_weather": "true",
      "daily": "temperature_2m_max,temperature_2m_min,weathercode",
      "temperature_unit": "fahrenheit",
      "timezone": "auto",
      "forecast_days": 2,
    }
    try:
      resp = requests.get(url, params=params, timeout=self.timeout)
      resp.raise_for_status()
      data = resp.json()

      cur = data["current_weather"]
      desc = WMO_CODES.get(cur["weathercode"], f"code {cur['weathercode']}")
      temp = round(cur["temperature"])

      daily = data["daily"]
      today_code = daily["weathercode"][0]
      today_desc = WMO_CODES.get(today_code, f"code {today_code}")
      today_max = round(daily["temperature_2m_max"][0])
      today_min = round(daily["temperature_2m_min"][0])

      if len(daily["weathercode"]) > 1:
        tomorrow_code = daily["weathercode"][1]
        tomorrow_desc = WMO_CODES.get(tomorrow_code, f"code {tomorrow_code}")
        tomorrow_max = round(daily["temperature_2m_max"][1])
        tomorrow_min = round(daily["temperature_2m_min"][1])
      else:
        tomorrow_desc, tomorrow_max, tomorrow_min = today_desc, today_max, today_min

      summary = (f"today {today_desc} with a high of {today_max} and low of {today_min}. "
                 f"Tomorrow {tomorrow_desc} with a high of {tomorrow_max} and low of {tomorrow_min}.")
      return desc, temp, summary

    except Exception as e:
      self.log.error("Weather fetch failed: %s", e)
      raise

  # ------------------------------------------------------------
  # Framework stop method
  # ------------------------------------------------------------
  def stop(self, msg=None):
    self.log.debug("WeatherSkill stop() called (no action needed).")


if __name__ == "__main__":
  import sys, traceback
  try:
    ws = WeatherSkill()
    threading.Event().wait()
  except Exception:
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
