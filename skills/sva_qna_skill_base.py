from skills.sva_base import SimpleVoiceAssistant
import time

class QuestionAnswerSkill(SimpleVoiceAssistant):
  def __init__(self, skill_id=None, skill_category=None, bus=None, timeout=5):
    super().__init__(msg_handler=self.handle_message, skill_id=skill_id, skill_category=skill_category)
    time.sleep(1)                          # give fallback skill a chance to initialize
    info = {
      "subtype": "qna_register_request",
      "skill_id": "fallback_skill",
      "qna_skill_id": skill_id
      }
    self.bus.send("skill", "fallback_skill", info) # register with the fallback skill

  def handle_message(self,msg):
    skill_data = {"confidence":0, "page_id":"", "correlator":0}
    subtype = msg["payload"]["subtype"]
    if subtype == "qna_get_confidence":
      try:
        skill_data = self.get_qna_confidence(msg)
      except:
        pass
      message = {"subtype":"qna_confidence_response","skill_id":"fallback_skill", "skill_data":skill_data}
      self.send_message("fallback_skill", message)
    if subtype == "qna_answer_question":
      self.qna_answer_question(msg)
    if subtype == "stop":
      print("\nGOT STOP IN Q&A HANDLE MSG!!!\n")
      self.stop(msg)

  def get_qna_confidence(self, msg):
    print("QuestionAnswerSkill.get_qna_confidence() Error - unimplemented method: handle_get_qna_confidence(self,msg)!")
 
  def qna_answer_question(self, msg):
    print("QuestionAnswerSkill.qna_answer_question() Error: unimplemented method: handle_qna_answer_question(self,msg)!")

  def stop(self,msg):
    print("QuestionAnswerSkill.stop()  Error - in qna base, unimplemented method: stop(self,msg)!")
