import json
import time
from threading import Event

from skills.sva_base import SimpleVoiceAssistant


class HelpSkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        self.skill_id = "help_skill"
        super().__init__(
            msg_handler=self.handle_message,
            skill_id="help_skill",
            skill_category="user",
        )
        info = {
            "subtype": "reserve_oob",
            "skill_id": "system_skill",
            "from_skill_id": self.skill_id,
            "verb": "help",
        }

        # register OOBs
        self.bus.send("system", "system_skill", info)
        self.bus.send("system", "intent_service", info)

        # Dictionary of available features and their help descriptions
        self.help_topics = {
            "music": "For music, you can ask me to play a song, artist, album, or genre. You can also say pause, resume, next track, or stop.",
            "radio": "For radio, you can ask me to play a station by name, like 'play NPR' or 'play BBC radio'.",
            "weather": "For weather, you can ask 'what is the weather', or ask for the forecast in a specific city like 'what is the weather in Chicago'.",
            "time": "You can ask me 'what time is it', 'what is today's date', or 'what day is it'.",
            "alarm": "For alarms, you can say 'set an alarm for 7 AM', 'list my alarms', or 'cancel all alarms'.",
            "volume": "To control the volume, you can say 'volume up', 'volume down', or 'set volume to 8'.",
            "home assistant": "If Home Assistant is set up, you can ask me to control devices, like 'turn on the living room lights'.",
            "email": "You can ask me to check your messages by saying 'do I have any new email'.",
            "internet": "You can check my network connection by asking 'are you connected to the internet'.",
        }

    def handle_message(self, msg):
        if msg["payload"]["subtype"] == "oob_detect":
            print("\n\nHELP REQUESTED\n\n")
            self.speak("What can I help you with?")
            self.speak(
                "You can ask for help with music, radio, weather, time, alarms, volume, or ask me for a list of topics."
            )
            self.get_user_input(self.handle_help_topic)

    def handle_help_topic(self, user_response):
        # user_response is passed back as a JSON string from the raw STT output
        if not user_response:
            self.speak("I didn't hear anything. You can ask for help again later.")
            return

        try:
            response_dict = json.loads(user_response)
            spoken_text = response_dict.get("text", "").lower()
        except json.JSONDecodeError:
            self.speak(
                "Sorry, I had trouble understanding that. Please try asking for help again."
            )
            return

        # Check if the user just wants to hear the available topics
        if (
            "list" in spoken_text
            or "topics" in spoken_text
            or "everything" in spoken_text
        ):
            topic_list = ", ".join(self.help_topics.keys())
            self.speak(
                f"I can provide help for the following topics: {topic_list}. Which one would you like to hear about?"
            )
            self.get_user_input(self.handle_help_topic)
            return

        # Find matching topics in the user's response
        matched_topics = []
        for topic in self.help_topics.keys():
            if topic in spoken_text:
                matched_topics.append(topic)

        # Check for common aliases
        if "date" in spoken_text and "time" not in matched_topics:
            matched_topics.append("time")
        if "lights" in spoken_text and "home assistant" not in matched_topics:
            matched_topics.append("home assistant")
        if "media" in spoken_text and "music" not in matched_topics:
            matched_topics.append("music")

        # Formulate a response based on the matches
        if len(matched_topics) == 0:
            self.speak(
                "Sorry, I couldn't find any help for that topic. You can ask for a list of topics, or try asking about something else."
            )
            self.get_user_input(self.handle_help_topic)
        elif len(matched_topics) > 1:
            self.speak(
                "I found multiple topics in your response. Please clarify which one you want help with."
            )
            self.get_user_input(self.handle_help_topic)
        else:
            # Exactly one match was found
            topic = matched_topics[0]
            self.speak(self.help_topics[topic])

    def stop(self):
        pass


if __name__ == "__main__":
    hlp = HelpSkill()
    Event().wait()  # wait forever
