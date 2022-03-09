from skills.sva_qna_skill_base import QuestionAnswerSkill
from threading import Event
import requests, json


class WikiSkill(QuestionAnswerSkill):
    def __init__(self, bus=None, timeout=5):
        super().__init__(skill_id='wiki_skill', skill_category='qna')

    def get_qna_confidence(self,msg):
        # I am being asked if I can answer this question
        print("\nwiki handle query")

        search_term = msg.data['msg_sentence']
        search_term = search_term.replace(" ", "+") # TODO use encode!

        # Get the page id:
        # TODO BUG need to catch exceptions
        try:
            search_url = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=%s&format=json&srlimit=1" % (search_term,)
            r = requests.get(search_url)
            r = json.loads(r.text)
            page_id = r['query']['search'][0]['pageid']

            # if we get back a page id we can answer this question
            return {'confidence':100, 'page_id':page_id, 'correlator':0}
        except:
            return {'confidence':0, 'page_id':0, 'correlator':0}



    def qna_answer_question(self,msg):
        # I am being asked to answer this question
        print("\nwiki answer! %s" % (msg.data,))

        # note skill_data is echo'ed in the answer_question message
        page_id = str( msg.data['skill_data']['page_id'] )

        # get the actual page
        results_url = "https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro&explaintext&redirects=1&pageids=" + page_id
        r = requests.get(results_url)
        r = json.loads(r.text)
        extract = r['query']['pages'][page_id]['extract']
        sa = extract.split("\n")
        answer = sa[0]

        print("wiki, call speak, answer = %s" % (answer,))
        self.speak(answer)

    def stop(self,msg):
        print("\n*** Do nothing wiki stop hit ***\n")


if __name__ == '__main__':
    ws = WikiSkill()
    Event().wait()  # Wait forever

