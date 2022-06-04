from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import time

class Example1Skill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        super().__init__(skill_id='example1_skill', skill_category='user')
        self.callback = None
        self.state = 'idle'

        # match phrase ---> "wake word, {run|test|execute} example" 
        self.register_intent('C', 'run example', 'one', self.start)
        self.register_intent('C', 'test example', 'one', self.start)
        self.register_intent('C', 'execute example', 'one', self.start)


    def handle_timeout(self):
        print("State=%s, timed out !" % (self.state,))
        self.state = 'idle'
        self.play_media(self.skill_base_dir + '/assets/fail.mp3')

    def handle_user_confirmation_input(self, user_confirmation):
        if user_confirmation == 'yes':
            self.play_media(self.skill_base_dir + '/assets/success.mp3')
        else:
            self.play_media(self.skill_base_dir + '/assets/fail.mp3')
        self.state = 'idle'

    def handle_user_location_input(self, user_input):
        self.state = 'get_confirmation'
        confirmation_prompt = "You said %s, is that correct?" % (user_input,)
        self.get_user_confirmation(self.handle_user_confirmation_input, confirmation_prompt, self.handle_timeout)

    def start(self, message):
        self.state = 'get_location'
        location_prompt = "Please tell me where you are located?"
        self.get_user_input(self.handle_user_location_input, location_prompt, self.handle_timeout)

    def stop(self):
        pass

if __name__ == '__main__':
    ex1 = Example1Skill()
    Event().wait()  # Wait forever
