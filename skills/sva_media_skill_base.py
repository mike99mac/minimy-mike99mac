from skills.sva_base import SimpleVoiceAssistant
from bus.Message import Message
from bus.MsgBusClient import MsgBusClient
from framework.message_types import MSG_SKILL
import time

class MediaSkill(SimpleVoiceAssistant):
    def __init__(self, skill_id=None, skill_category=None, bus=None, timeout=5):
        """
        All user media skills inheret from the MediaSkill. A user media
        skill must have at least two methods defined; get_media_confidence()
        and media_play(). A media skill is called first to return the 
        confidence level it has regarding a media play request. If its 
        confidence is the highest it is later called to play that media. 
        See the youtube skill for an example of a media skill.
        """
        super().__init__(msg_handler=self.handle_message, skill_id=skill_id, skill_category=skill_category)
        time.sleep(1) # give fall back skill a chance to initialize

        # register with the system media skill
        info = {
            'subtype': 'media_register_request',
            'skill_id': 'media_skill',
            'media_skill_id': skill_id
            }
        self.bus.send(MSG_SKILL, 'media_skill', info)


    def handle_message(self,msg):
        if msg.data['subtype'] == 'media_get_confidence':
            skill_data = self.get_media_confidence(msg)
            message = {'subtype':'media_confidence_response','skill_id':'media_skill', 'skill_data':skill_data}
            self.send_message('media_skill', message)

        if msg.data['subtype'] == 'media_play':
            self.media_play(msg)
        pass

    def get_media_confidence(self,msg):
        print("Error - unimplemented method: get_media_confidence(self,msg)!")
        pass

    def media_play(self,msg):
        print("Error - unimplemented method: media_play(self,msg)!")
        pass

