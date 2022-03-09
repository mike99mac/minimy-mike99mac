from skills.sva_base import SimpleVoiceAssistant
from framework.util.utils import us_abbrev_to_state 
from framework.util.utils import execute_command
from threading import Event
import requests, time, json

class WeatherSkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        super().__init__(skill_id='weather_skill', skill_category='user')
        self.busy = False

        # register intents
        self.register_intent('Q', 'what', 'weather', self.handle_msg)
        self.register_intent('Q', 'what', 'forecast', self.handle_msg)


        # these should really come from a 
        # config file but for now ...

        # get your public ip
        response = execute_command('curl ifconfig.me')
        ra = response.split("\n")
        start_indx = ra[0].find(":") + 1

        self.my_public_ip = ra[0][start_indx:]

        # get geo data associated with public ip
        response = execute_command('curl https://ipinfo.io/' + self.my_public_ip)
        start_indx = response.find(":") + 1
        end_indx = response.find("}") + 1

        self.geo_info = {}
        self.my_city = ''
        self.my_state = ''
        self.my_zip = ''
        try:
            self.geo_info = json.loads(response[start_indx:end_indx].replace("\n",""))
            self.my_city = self.geo_info['city']
            self.my_state = self.geo_info['region']
            self.my_zip = self.geo_info['postal']
        except:
            self.log.warning("Weather skill exception in init()!")

        self.log.debug("WeatherSkill: My Public IP:%s, My City:%s, My State:%s My Zip:%s" % (self.my_public_ip, self.my_city, self.my_state, self.my_zip))


    def handle_msg(self, message):
        if self.busy:
            self.log.warning("Weather BUSY?")
            return

        # if we did not get a location in the request we will use our default location
        loc_city = ''
        loc_state = ''
        sentence = message.data['utt']['sentence']
        tag = 'for '
        start_indx = sentence.find(tag)
        if start_indx > -1:
            # we have a location in the request
            start_indx += len(tag)
            location = sentence[start_indx:]
            la = location.split(" ")

            if len(la) < 2:
                self.log.warning("Invalid location!")
                return
            elif len(la) == 2:
                loc_city = la[0]
                loc_state = la[1]
            elif len(la) > 2:
                # last is always state
                loc_state = la[len(la)-1]
                la = la[:-1]
                loc_city = " ".join(la)


        url = "https://forecast.weather.gov/zipcity.php?inputstring=%s&btnSearch=Go" % (self.my_zip,)
        if loc_city != '' and loc_state != '':
            loc = loc_city + ',' + loc_state
            url = "https://forecast.weather.gov/zipcity.php?inputstring=%s&btnSearch=Go" % (loc,)


        res = requests.get(url)
        page = res.text

        tag= '<p class="myforecast-current">'
        fcast = self.get_tag_data(page, tag, "<", 1)

        tag = '<p class="myforecast-current-lrg">'
        temp = self.get_tag_data(page, tag, "&", 1)

        tag = "seven-day-forecast-list"
        start_indx = page.find(tag)
        if start_indx == -1:
            self.log.warning("WeatherSkill Parse Error")
            return
        start_indx += len(tag)

        tag = 'title="'
        extended = self.get_tag_data(page, tag, '"', start_indx)

        tag = "<b>Extended Forecast for</b>"
        start_indx = page.find(tag)
        if start_indx == -1:
            self.log.warning("WeatherSkill Parse Error")
            return
        start_indx += len(tag)

        tag = '<h2 class="panel-title">'


        #debug
        si = page.find(tag, start_indx)

        #location_name = self.get_tag_data(page, tag, "</h2>", start_indx)
        location_name = self.get_tag_data(page, tag, "<", start_indx+2)
        location_name = location_name.replace("\n","")
        location_name = location_name.strip()

        # convert state abbreviation to state name
        state_abbrev = location_name[len(location_name) -2:]
        location_name = location_name[:-3]
        state_name = us_abbrev_to_state[state_abbrev]
        location_name = location_name + ', ' + state_name

        say1 = "It is currently %s and %s degrees in %s." % (fcast, temp, location_name)

        start_indx = extended.find(":") + 2
        term = extended[:start_indx-2]

        say2 = "The forecast for %s is %s." % (term, extended[start_indx:])
        say2 = say2.replace("mph", "miles per hour")

        self.speak(say1 + ' ' + say2)
        time.sleep(0.5)
        self.busy = False


    def get_tag_data(self, page, tag, tag_end_str, start_indx):
        start_indx = page.find(tag, start_indx)
        if start_indx == -1:
            self.log.warning("GTD:Parse Error")
            return

        start_indx += len(tag)
        end_indx = page.find(tag_end_str, start_indx)

        if end_indx == -1:
            self.log.warning("GTD:Parse Error")
            return

        return page[start_indx:end_indx]


    def stop(self):
        self.log.debug("Do nothing stop for weather skill hit")

if __name__ == '__main__':
    ws = WeatherSkill()
    Event().wait()  # Wait forever
