from skills.sva_media_skill_base import MediaSkill
from threading import Event
import requests, time, json, glob, os
from framework.message_types import MSG_MEDIA

media_verbs = ['play', 'watch', 'listen']

class YouTubeSkill(MediaSkill):

    def __init__(self, bus=None, timeout=5):
        self.skill_id = 'youtube_skill'
        super().__init__(skill_id=self.skill_id, skill_category='media')
        self.url = ''
        self.log.debug("** YouTube skill initialized, skill base dir is %s" % (self.skill_base_dir,))


    def get_url(self):
        # returns video url from search results
        fh = open("/tmp/search_results.html")
        for line in fh:
            if line.find("videoId") > 0:
                start_pos = line.find("videoId") + 10
                end_pos = line.find('"', start_pos)
                fh.close()
                return( line[start_pos:end_pos] )


    def get_media_confidence(self,msg):
        # I am being asked if I can answer this question
        sentence = msg.data['msg_sentence']
        self.log.debug("\nyoutube handle query sentence=%s" % (sentence,))
        sa = sentence.split(" ")
        vrb = sa[0].lower()
        if vrb in media_verbs:
            sentence = sentence[len(vrb):]

        search_term = sentence.replace(" ", "+")  # url encode it :-)
        cmd = "wget -O /tmp/search_results.html https://www.youtube.com/results?search_query=%s" % (search_term,)
        os.system(cmd)
        self.url = self.get_url()

        confidence = 0
        if self.url:
            confidence = 100

        return {'confidence':confidence, 'correlator':0, 'sentence':sentence, 'url':self.url}


    def media_play(self,msg):
        # I am being asked to play this media
        self.log.debug("\n** youtube being asked to play this media ** %s" % (msg.data,))
        #self.play_media(self.skill_base_dir + '/assets/car_door_ajar.mp3')

        sentence = msg.data['skill_data']['sentence']
        url = msg.data['skill_data']['url']
        cmd = "pytube https://www.youtube.com/watch?v=%s" % (url,)
        os.system(cmd)

        self.log.debug("Converting from mp4 to mp3")
        # find the downloaded file
        fnames = glob.glob("*.mp4")
        fname = fnames[0]

        # rename it
        input_filename = 'input.mp4'
        output_filename = 'output.mp3'
        cmd = "mv \"%s\" %s" % (fname,input_filename)
        os.system(cmd)

        cmd = "rm %s" % (output_filename,)
        os.system(cmd)

        # convert 
        cmd = "ffmpeg -i %s -q:a 0 -map a %s" % (input_filename, output_filename)
        os.system(cmd)
        os.system("rm %s" % (input_filename,))  # clean up

        self.play_media(self.skill_base_dir + '/' + output_filename, delete_on_complete=True)


    def stop(self, msg):
        self.log.info("Youtube skill, stop() hit")


if __name__ == '__main__':
    yts = YouTubeSkill()
    Event().wait()  # Wait forever
