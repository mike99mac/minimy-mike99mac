from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import requests, time
from framework.message_types import MSG_SYSTEM

class ConnectivitySkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        self.skill_id = 'connectivity_skill'
        super().__init__(msg_handler=self.handle_message, skill_id='connectivity_skill', skill_category='system')
        self.is_running = False
        self.log.info("Connectivity Skill Activated")


    def handle_message(self, message):
        data = message.data
        self.log.error("Connectivity Skill got a message")


    def run(self):
        self.is_running = True
        while self.is_running:
            # this is a long running skill. it needs to maintain state 
            # because you do not want to keep bothering the user every 
            # 90 seconds because you are still down, but you also want 
            # to periodically retry to establish connectivity. For now
            # audibly notify the user when you change state in either
            # direction.
            MAX_FAILS_ALLOWED = 3
            SLEEP_DELAY_IN_SECONDS = 90
            pass_fail = 0

            while pass_fail < MAX_FAILS_ALLOWED:
                time.sleep(SLEEP_DELAY_IN_SECONDS)
                try:
                    res = requests.get('https://amazon.com')
                    pass_fail = 0
                except Exception as e:
                    #print(e)
                    pass_fail += 1
                    print(pass_fail)

            print("I suspect I have lost internet connectivity.")
            print("Would you like me to switch to local mode?")

            # if yes, change config file and stop and start 


    def stop(self):
        self.log.error("Connectivity Skill got a stop request")
        self.is_running = False
        pass


if __name__ == '__main__':
    conn = ConnectivitySkill()
    conn.run()
    Event().wait()  # Wait forever
