
from threading import Event
from skills.sva_base import SimpleVoiceAssistant
from bus.Message import Message
from framework.message_types import MSG_SKILL, MSG_SYSTEM
# import subprocess

class SVAMediaSkill(SimpleVoiceAssistant):
    """
    determine who should handle a media request when tell that skill to handle it 
    """
    def __init__(self, bus=None, timeout=5):
        super().__init__(msg_handler=self.handle_message, skill_id='media_skill', skill_category='media')
        self.skill_id = 'media_skill'
        self.log.debug(f"SVAMediaSkill.__init__() skill_id = {self.skill_id} skill_base_dir = {self.skill_base_dir}") 
        self.media_skills = []             # array of registered media skill handlers
        self.active_media_skill = None

        # register OOBs
        info = {
                'subtype':'reserve_oob', 
                'skill_id':'system_skill', 
                'from_skill_id':self.skill_id, 
                'verb':'pause'
               }
        self.bus.send(MSG_SYSTEM, 'system_skill', info)
        info['verb'] = 'resume'
        self.bus.send(MSG_SYSTEM, 'system_skill', info)
        info['verb'] = 'previous'
        self.bus.send(MSG_SYSTEM, 'system_skill', info)
        info['verb'] = 'next'
        self.bus.send(MSG_SYSTEM, 'system_skill', info)
        info['verb'] = 'stop'
        self.bus.send(MSG_SYSTEM, 'system_skill', info)
        self.log.debug("SVAMediaSkill.__init__(): registering OOB intents") 
        self.register_intent('O', 'next', 'song', self.handle_next)
        self.register_intent('O', 'next', 'station', self.handle_next)
        self.register_intent('O', 'next', 'title', self.handle_next)
        self.register_intent('O', 'next', 'track', self.handle_next)
        self.register_intent('O', 'previous', 'song', self.handle_prev)
        self.register_intent('O', 'previous', 'station', self.handle_prev)
        self.register_intent('O', 'previous', 'title', self.handle_prev)
        self.register_intent('O', 'previous', 'track', self.handle_prev)
        self.register_intent('O', 'pause', 'music', self.handle_pause)
        self.register_intent('O', 'resume', 'music', self.handle_resume)
        self.register_intent('O', 'stop', 'music', self.handle_stop)

    def handle_oob_detected(self, msg):
        self.log.debug(f"SVAMediaSkill.handle_oob_detected() OOB detected - msg: {msg}")
        if self.active_media_skill == None: # no music playing
            self.speak_lang(f"{self.skill_base_dir}/skills/user_skills/mpc", "no_music_playing", None) # tell user  
        else:
            oob_type = msg.data['verb']
            self.log.debug(f"SVAMediaSkill.handle_oob_detected(): oob_type = {oob_type}")
            match oob_type:
                case "previous":
                    self.handle_prev(msg)
                case "next":
                    self.handle_next(msg)
                case "pause":
                    self.handle_pause(msg)
                case "resume":
                    self.handle_resume(msg)
                case "stop":
                    self.handle_stop(msg)
                case _:
                    self.log.error(f"SVAMediaSkill.handle_oob_detected() unexpected OOB: {oob_type}")

    def handle_register_media(self, msg):
        data = msg.data
        skill_id = data['media_skill_id']
        self.log.debug(f"SVAMediaSkill.handle_register_media() {skill_id} registered as a Media skill")
        if skill_id not in self.media_skills:
            self.media_skills.append(skill_id)

    def handle_media_response(self, msg):
        self.log.debug(f"SVAMediaSkill.handle_media_response() msg: {msg.data}")
        # gather responses and decide who will handle the media then send message to that skill_id to play the media
        # if error play default fail earcon.
        message = {'subtype':'media_play', 
                   'skill_id':msg.data['from_skill_id'], 
                   'from_skill_id':self.skill_id, 
                   'skill_data':msg.data['skill_data']
                  }

        # for now assume the only skill to answer gets it  and we don't allow stacked media sessions
        self.active_media_skill = msg.data['from_skill_id']
        self.send_message(msg.data['from_skill_id'], message)
        # figure out when done here :-)
        # probably when the media player service tells the skill id the session has ended!
        self.log.info(f"SVAMediaSkill.handle_media_response() media skill {msg.data['from_skill_id']} going active")

    def handle_query(self, msg):
        self.log.debug("SVAMediaSkill.handle_query() hit!")
        data = msg.data
        # send out message to all media skills saying you got 3 seconds to give me 
        # your confidence level. all media skills need to respond to the 'get_confidence'
        # message and the 'media_play' message
        for skill_id in self.media_skills:
            self.log.debug("SVAMediaSkill.handle_query(): sending media_get_confidence to %s" % (skill_id))
            info = {
                'subtype': 'media_get_confidence',
                'skill_id': skill_id,
                'from_skill_id':self.skill_id,
                'msg_sentence':data['sentence']
                }
            self.bus.send(MSG_SKILL, skill_id, info)

    def handle_command(self, msg):
        self.log.debug(f"SVAMediaSkill.handle_command(): active media is {self.active_media_skill}")
        data = msg.data
        data['skill_id'] = 'media_player_service'
        data['subtype'] = 'media_player_command'
        self.send_message('media_player_service', data)

    def handle_message(self,msg):
        self.log.debug(f"SVAMediaSkill.handle_message(): active media is {self.active_media_skill}")
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
            self.log.debug(f"SVAMediaSkill.handle_message() media session ended for {self.active_media_skill}")
            self.active_media_skill = None
        else:
            self.log.warning(f"SVAMediaSkill.handle_message() unrecognized subtype = {msg.data['subtype']}")

    def handle_prev(self, message):
        """
        Play previous track or station
        """
        self.log.debug("SVAMediaSkill.handle_prev() - calling mpc_cmd(prev)")
        self.mpc_cmd("prev")

    def handle_next(self, message):
        """
        Play next track or station - called by the playback control skill
        """
        self.log.debug("SVAMediaSkill.handle_next() - calling mpc_cmd(next)")
        self.mpc_cmd("next")

    def handle_pause(self, msg):
        """
        Pause what is playing
        """
        self.log.info("SVAMediaSkill.handle_pause() - calling mpc_cmd(toggle)")
        self.mpc_cmd("toggle")      # toggle between play and pause

    def handle_resume(self, msg):
        """
        Resume what was playing
        """
        self.log.info("SVAMediaSkill.handle_resume() - calling mpc_cmd(toggle)")
        self.mpc_cmd("toggle")      # toggle between play and pause

    def handle_stop(self, msg):
        """
        Clear the mpc queue 
        """
        self.log.info("SVAMediaSkill.handle_resume() - calling mpc_cmd(clear)")
        self.mpc_cmd("clear") 

    def stop(self, message):
        self.log.info("SVAMediaSkill.stop() - pausing music")
        self.mpc_cmd("pause")      

if __name__ == '__main__':
    sva_ms = SVAMediaSkill()
    Event().wait()                         # Wait forever

