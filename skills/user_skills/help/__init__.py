from skills.sva_base import SimpleVoiceAssistant
from bus.Message import Message
from threading import Event
import time
from framework.message_types import MSG_SYSTEM

class HelpSkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        self.skill_id = 'help_skill'
        super().__init__(msg_handler=self.handle_message, skill_id='help_skill', skill_category='user')

        # register OOBs 
        info = {
                'subtype':'reserve_oob',
                'skill_id':'system_skill',
                'from_skill_id':self.skill_id,
                'verb':'help'
                }
        #self.bus.emit(Message(MSG_SYSTEM, info))
        self.bus.send(MSG_SYSTEM, 'system_skill', info)



    def handle_message(self, message):
        data = message.data
        if data['subtype'] == 'oob_detect':
            print("\n\nHELP REQUESTED\n\n")
            self.speak("What can I help you with?")
            self.speak("You can say things like general help, or help with alarms or ask me for a list of topics.", wait=True)
            topic = self.get_raw_input()
            prompt = "Playing help for %s" % (topic,)
            self.speak(prompt)



    def stop(self):
        pass


if __name__ == '__main__':
    hlp = HelpSkill()
    Event().wait()  # Wait forever
