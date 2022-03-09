from skills.sva_base import SimpleVoiceAssistant
from bus.Message import Message
from bus.MsgBusClient import MsgBusClient
from framework.message_types import MSG_SKILL
import time

class QuestionAnswerSkill(SimpleVoiceAssistant):
    def __init__(self, skill_id=None, skill_category=None, bus=None, timeout=5):
        super().__init__(msg_handler=self.handle_message, skill_id=skill_id, skill_category=skill_category)
        time.sleep(1) # give fall back skill a chance to initialize

        # register with the fallback skill
        info = {
            'subtype': 'qna_register_request',
            'skill_id': 'fallback_skill',
            'qna_skill_id': skill_id
            }
        self.bus.send(MSG_SKILL, 'fallback_skill', info)

    def handle_message(self,msg):
        #print("Q&A handle_message() %s" % (msg.data,))
        skill_data = {'confidence':0, 'page_id':'', 'correlator':0}
        if msg.data['subtype'] == 'qna_get_confidence':
            try:
                skill_data = self.get_qna_confidence(msg)
            except:
                pass

            message = {'subtype':'qna_confidence_response','skill_id':'fallback_skill', 'skill_data':skill_data}
            self.send_message('fallback_skill', message)

        if msg.data['subtype'] == 'qna_answer_question':
            self.qna_answer_question(msg)

        if msg.data['subtype'] == 'stop':
            print("\nGOT STOP IN Q&A HANDLE MSG!!!\n")
            self.stop(msg)

    def get_qna_confidence(self,msg):
        print("Error - unimplemented method: handle_get_qna_confidence(self,msg)!")
        pass

    def qna_answer_question(self,msg):
        print("Error - unimplemented method: handle_qna_answer_question(self,msg)!")
        pass

    def stop(self,msg):
        print("Error - in qna base, unimplemented method: stop(self,msg)!")
        pass
