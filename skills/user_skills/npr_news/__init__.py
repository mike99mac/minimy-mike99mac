from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import requests, time, glob, sys, os

# TODO this is actually a media skill and needs to be converted
class NPRNewsSkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        super().__init__(skill_id='nprnews_skill', skill_category='media')
        self.terminate_flag = False

        # match phrase ---> "wake word, {run|test} example" 
        self.register_intent('Q', 'what', 'new', self.handle_msg)
        self.register_intent('C', 'play', 'news', self.handle_msg)
        self.register_intent('C', 'listen', 'news', self.handle_msg)
        self.register_intent('C', 'play', 'npr', self.handle_msg)
        self.register_intent('C', 'listen', 'npr', self.handle_msg)

    def handle_msg(self, message):
        self.speak("Getting the latest news from N.P.R news")
        print("CKPT1")

        url = "https://www.npr.org/podcasts/500005/npr-news-now"
        res = requests.get(url)
        print("CKPT2")
        page = res.text
        start_indx = page.find('audioUrl')

        print("CKPT3")
        if start_indx == -1:
            print("Error cant find url")
            return

        end_indx = start_indx + len('audioUrl')
        page = page[end_indx+3:]
        end_indx = page.find('?')
        print("CKPT4")

        if end_indx == -1:
            print("Parse error")
            return
        print("CKPT5")

        new_url = page[:end_indx]
        new_url = new_url.replace("\\","")
        print("CKPT6")

        cmd = "wget %s" % (new_url,)
        os.system(cmd)

        print("CKPT7")
        #find the downloaded file
        fnames = glob.glob("*.mp3")
        fname = fnames[0]
        cmd = "mpg123 %s" % (fname,)
        print("CKPT8")

        #os.system(cmd)
        self.play_media(self.skill_base_dir + '/' + fname, delete_on_complete=True)

    def stop(self):
        self.terminate_flag = True

if __name__ == '__main__':
    npr = NPRNewsSkill()
    Event().wait()  # Wait forever
