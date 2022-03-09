from threading import Event
from skills.sva_base import SimpleVoiceAssistant
from bus.Message import Message
from framework.message_types import MSG_SKILL, MSG_SYSTEM

class SVAMediaSkill(SimpleVoiceAssistant):
    # the media skill figures out who should handle
    # a media request and then tells that skill to
    # handle the request
    def __init__(self, bus=None, timeout=5):
        super().__init__(msg_handler=self.handle_message, skill_id='media_skill', skill_category='media')
        self.skill_id = 'media_skill'

        # array of registered media skill handlers
        self.media_skills = []
        self.active_media_skill = None


        """
        # register OOBs  
        # don't do this until a media skill goes active
        info = {
                'subtype':'reserve_oob', 
                'skill_id':'system_skill', 
                'from_skill_id':self.skill_id, 
                'verb':'pause'
                }
        self.bus.emit(Message(MSG_SYSTEM, info))

        info['verb'] = 'resume'
        self.bus.emit(Message(MSG_SYSTEM, info))

        info['verb'] = 'previous'
        self.bus.emit(Message(MSG_SYSTEM, info))

        info['verb'] = 'next'
        self.bus.emit(Message(MSG_SYSTEM, info))
        """


    def handle_oob_detected(self,msg):
        self.log.debug("OOB detected by media base %s" % (msg.data,))


    def handle_register_media(self,msg):
        data = msg.data
        skill_id = data['media_skill_id']
        self.log.info("[%s] Registered as a Media skill" % (skill_id,))
        if skill_id not in self.media_skills:
            self.media_skills.append(skill_id)


    def handle_media_response(self,msg):
        # gather responses and decide who to handle the media
        # then send message to that skill_id to play the media
        # if error play default fail earcon.
        message = {'subtype':'media_play', 
                'skill_id':msg.data['from_skill_id'], 
                'from_skill_id':self.skill_id, 
                'skill_data':msg.data['skill_data']}

        # for now assume the only skill to answer gets it
        # and we don't allow stacked media sessions
        self.active_media_skill = msg.data['from_skill_id']
        self.send_message(msg.data['from_skill_id'], message)
        # figure out when done here :-)
        # probably when the media player service tells the 
        # skill id the session has ended!
        self.log.info("media skill %s going active" % (msg.data['from_skill_id'],))


    def handle_query(self,msg):
        self.log.debug("SVA-Media: handle_query() hit!")
        data = msg.data
        # send out message to all media skills
        # saying you got 3 seconds to give me 
        # your confidence level. all media skills
        # need to respond to the 'get_confidence'
        # message and the 'media_play' message
        for skill_id in self.media_skills:
            self.log.debug("SVA-Media: sending media_get_confidence to %s" % (skill_id,))
            """
            self.bus.emit(Message(MSG_SKILL, {
                'subtype': 'media_get_confidence',
                'skill_id': skill_id,
                'from_skill_id':self.skill_id, 
                'msg_sentence':data['sentence']
                }))
            """
            info = {
                'subtype': 'media_get_confidence',
                'skill_id': skill_id,
                'from_skill_id':self.skill_id,
                'msg_sentence':data['sentence']
                }
            self.bus.send(MSG_SKILL, skill_id, info)


    def handle_command(self,msg):
        data = msg.data
        data['skill_id'] = 'media_player_service'
        data['subtype'] = 'media_player_command'
        self.send_message('media_player_service', data)

    def handle_message(self,msg):
        self.log.debug("media handle message currently active media is %s" % (self.active_media_skill,))
        #print("SVA-Media:handle_message() %s" % (msg.data,))
        if msg.data['subtype'] == 'media_register_request':
            return self.handle_register_media(msg)

        elif msg.data['subtype'] == 'media_confidence_response':
            return self.handle_media_response(msg)

        elif msg.data['subtype'] == 'media_query':
            return self.handle_query(msg)

        elif msg.data['subtype'] == 'media_command':
            return self.handle_command(msg)

        elif msg.data['subtype'] == 'oob_detect':
            return self.handle_oob_detected(msg)

        elif msg.data['from_skill_id'] == 'media_player_service' and msg.data['subtype'] == 'media_player_command_response' and msg.data['response'] == 'session_ended' and self.active_media_skill == msg.data['skill_id']:
            # if media player announcing session ended for my active media session owner
            # {"type": "skill", "data": {"error": "", "subtype": "media_player_command_response", "response": "session_ended", "session_id": 1, "skill_id": "tts_service", "from_skill_id": "media_player_service"}, "context": {}}
            self.log.debug("media session ended for %s" % (self.active_media_skill,))
            self.active_media_skill = None

        else:
            self.log.warning("SVA-Media: Error - unrecognized subtype = %s" % (msg.data['subtype'],))


if __name__ == '__main__':
    sva_ms = SVAMediaSkill()
    Event().wait()  # Wait forever

