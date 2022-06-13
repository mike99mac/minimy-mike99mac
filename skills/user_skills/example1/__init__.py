from skills.sva_base import SimpleVoiceAssistant
from threading import Event

class Example1Skill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        super().__init__(skill_id='example1_skill', skill_category='user')
        self.callback = None
        self.state = 'idle'

        # register intents
        self.register_intent('C', 'run example', 'one', self.start)
        self.register_intent('C', 'test example', 'one', self.start)
        self.register_intent('C', 'execute example', 'one', self.start)

    def handle_timeout(self):
        self.state = 'idle'
        self.play_media(self.skill_base_dir + '/assets/fail.mp3')

    def handle_user_confirmation_input(self, user_confirmation):
        self.state = 'idle'
        media_file = '/assets/fail.mp3'
        if user_confirmation == 'yes':
            media_file = '/assets/success.mp3'
        self.play_media(self.skill_base_dir + media_file)

    def handle_user_location_input(self, user_input):
        self.state = 'get_confirmation'
        self.get_user_confirmation(self.handle_user_confirmation_input, 
                                   "You said %s, is that correct?" % (user_input,), 
                                   self.handle_timeout)

    def start(self, message):
        self.state = 'get_location'
        self.get_user_input( self.handle_user_location_input,
                             "Please tell me where you are located", 
                             self.handle_timeout )

    def stop(self):
        self.log.info("Do nothing stop method hit")

if __name__ == '__main__':
    ex1 = Example1Skill()
    Event().wait()  # Wait forever
