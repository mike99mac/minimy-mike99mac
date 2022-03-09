from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import time

class EmailSkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        super().__init__(skill_id='email_skill', skill_category='user')
        self.callback = None
        self.letters = []
        self.body = []
        self.state = 'idle'

        # match phrase ---> "wake word, {create|start|send} email" 
        self.register_intent('C', 'create', 'email', self.start)
        self.register_intent('C', 'start', 'email', self.start)
        self.register_intent('C', 'send', 'email', self.start)
        self.register_intent('C', 'new', 'email', self.start)
        self.register_intent('C', 'compose', 'email', self.start)
        self.log.error("Email intents registered")


    def handle_timeout(self):
        print("State=%s, timed out !" % (self.state,))
        self.state = 'idle'
        self.play_media(self.skill_base_dir + '/assets/fail.mp3')



    def handle_review_confirmation_input(self, user_confirmation):
        if user_confirmation == 'yes':
            self.speak("Read email here.")
            self.state = 'idle'
        else:
            self.speak("Send email here.")
            self.state = 'idle'


    def handle_body_input(self, user_input):
        if user_input.find("stop") > -1:
            self.state = 'idle'
            self.log.error("XXXXXXXXXXXXXXXXXXX RECIPIENT %s" % (self.letters,))
            self.log.error("XXXXXXXXXXXXXXXXXXX BODY %s" % (self.body,))
            prompt = "Email ready to send. Would you like to review it before it is sent?"
            self.get_user_confirmation(self.handle_review_confirmation_input, prompt, self.handle_timeout)
            return 
        if user_input.find("no") > -1:
            prompt = "Not saved."
            self.get_user_input(self.handle_body_input, prompt, self.handle_timeout)
        else:
            self.body.append(user_input)
            self.log.error("XXXXXXX EMAIL body sentence = %s, body = %s" % (user_input,self.body))
            prompt = user_input
            self.get_user_input(self.handle_body_input, prompt, self.handle_timeout)

    def handle_spell_input(self, user_input):
        if user_input.find("stop") > -1:
            self.log.error("XXXXXXX EMAIL spell END. letters = %s" % (self.letters,))
            self.state = 'composing'
            self.body = []
            prompt = "Ready for message body. I will echo each sentence. To disregard a sentence say no. When finished say stop."
            self.get_user_input(self.handle_body_input, prompt, self.handle_timeout)
            return

        if user_input.find("no") > -1:
            prompt = "%s not saved." % (user_input,)
            self.get_user_input(self.handle_spell_input, prompt, self.handle_timeout)
        else:
            self.letters.append(user_input)
            self.log.error("XXXXXXX EMAIL spell - letter = %s, letters = %s" % (user_input,self.letters))
            prompt = "%s" % (user_input.replace(".","dot")) 
            self.get_user_input(self.handle_spell_input, prompt, self.handle_timeout)

    def handle_user_spell_confirmation_input(self, user_confirmation):
        if user_confirmation == 'yes':
            self.state = 'spelling'
            self.letters = []
            prompt = "O K, I will echo your input. If I say the wrong letter just say no. What is the first letter?"
            self.get_user_input(self.handle_spell_input, prompt, self.handle_timeout)
        else:
            self.play_media(self.skill_base_dir + '/assets/fail.mp3')
        self.state = 'idle'

    def handle_recipient_confirmation(self, user_confirmation):
        if user_confirmation == 'yes':
            self.play_media(self.skill_base_dir + '/assets/confirm.wav')
            prompt = "Ready for message body. I will echo each sentence. To disregard a sentence say no. When finished say stop."
            self.get_user_input(self.handle_body_input, prompt, self.handle_timeout)
        else:
            prompt = "Would you prefer to spell it?"
            self.get_user_confirmation(self.handle_user_spell_confirmation_input, prompt, self.handle_timeout)

    def handle_recipient_input(self, user_input):
        if user_input.find("never") > -1 or user_input.find("spell") > -1:
            return self.handle_user_spell_confirmation_input('yes')

        speakable_user_input = user_input.replace(".", " dot ")
        email_address = user_input.replace("at","@")
        email_address = email_address.replace(" ","")
        self.log.error("XXXXXXX email:%s, speakable:%s" % (email_address,speakable_user_input))
        self.state = 'get_confirmation'
        confirmation_prompt = "You said %s, is that correct?" % (speakable_user_input,)
        self.get_user_confirmation(self.handle_recipient_confirmation, confirmation_prompt, self.handle_timeout)

    def start(self, message):
        self.recipient = ''
        get_email_address_prompt = "Email to who?"
        self.get_user_input(self.handle_recipient_input, get_email_address_prompt, self.handle_timeout)

    def stop(self, msg):
        pass

if __name__ == '__main__':
    em1 = EmailSkill()
    Event().wait()  # Wait forever
