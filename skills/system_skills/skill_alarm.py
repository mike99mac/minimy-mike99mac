import re, time, datetime
import lingua_franca
import inflect
import pytz
import os
from skills.sva_base import SimpleVoiceAssistant
from threading import Thread, Event
from datetime import timedelta
from framework.util.utils import get_raw, get_hour_min, get_ampm, get_time_from_utterance
from bus.Message import Message
from framework.message_types import MSG_SYSTEM


class AlarmActiveThread(Thread):
    def __init__(self, cb):
        super(AlarmActiveThread, self).__init__()
        self._terminated = False
        self.active = False
        self.cb = cb

    def run(self):
        while not self._terminated:
            # this value should come from a config file
            time.sleep(15)
            if self.active:
                if self.cb is not None:
                    self.cb()


class AlarmDetectThread(Thread):
    def __init__(self, alarms, cb, log):
        super(AlarmDetectThread, self).__init__()
        self.alarms = alarms
        self.cb = cb
        self.log = log
        self._terminated = False

    def run(self):
        while not self._terminated:
            time.sleep(17)
            time_now = datetime.datetime.now()
            self.log.debug("Checking for expired alarms: %s" % (time_now,))
            tmp_alarms = self.alarms
            if len(tmp_alarms) == 0:
                self.log.debug("No alarms found in the database")
                pass
            for alarm in tmp_alarms:
                aa = alarm.split(",")
                expires_at = aa[0]
                expires_at =  datetime.datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                expires_at = expires_at.replace(second=0, microsecond=0)
                self.log.debug("db alm expires: %s" % (expires_at,))
                if expires_at <= time_now:
                    self.cb(alarm)


class AlarmSkill(SimpleVoiceAssistant):
    def __init__(self, bus=None, timeout=5):
        self.skill_id = 'alarm_skill'
        super().__init__(msg_handler=self.handle_message, skill_id='alarm_skill', skill_category='system')
        lingua_franca.load_language('en')
        self.inflect_thing = inflect.engine()

        self.cancel_converse_words = [
                'stop',
                'cancel',
                'abort',
                'terminate',
                'nevermind',
                'forget it',
                ]

        # intent stuff
        self.register_intent('C', 'set', 'alarm', self.handle_create)
        self.register_intent('C', 'create', 'alarm', self.handle_create)
        self.register_intent('C', 'new', 'alarm', self.handle_create)

        self.register_intent('C', 'show', 'alarms', self.handle_show)
        self.register_intent('C', 'display', 'alarms', self.handle_show)
        self.register_intent('C', 'list', 'alarms', self.handle_show)

        self.register_intent('C', 'delete', 'alarm', self.handle_delete)
        self.register_intent('C', 'delete', 'alarms', self.handle_delete)
        self.register_intent('C', 'remove', 'alarm', self.handle_delete)
        self.register_intent('C', 'remove', 'alarms', self.handle_delete)

        self.register_intent('C', 'stop', 'alarm', self.handle_stop)
        self.register_intent('C', 'stop', 'alarms', self.handle_stop)
        self.register_intent('C', 'cancel', 'alarm', self.handle_stop)
        self.register_intent('C', 'cancel', 'alarms', self.handle_stop)

        base_dir = os.getenv('SVA_BASE_DIR')

        # reset alarm database
        self.db_filename = base_dir + '/skills/system_skills/' + 'alarms.db'
        self.alarms = []

        try:
            fh = open(self.db_filename)
            self.alarms = fh.readlines()
            fh.close()
        except:
            # no file, create one
            self.log.warning("Warning, no alarms database found, creating a new one! %s" % (self.db_filename,))
            fh = open(self.db_filename, 'w')
            fh.close()

        self.alarms = self.remove_expired_alarms(self.alarms)
        self.update_alarm_db()

        # spawn detect expired alarms thread
        self.alarm_detect = AlarmDetectThread(self.alarms, self.handle_expired_alarm, self.log)
        self.alarm_detect.start()

        # spawn expired alarm handler thread
        self.beep_filename = "%s/framework/assets/alarm_clock.mp3" % (base_dir,)
        self.alarm_active = AlarmActiveThread(self.play_beep)
        self.alarm_active.start()

        self.log.info("Alarm Skill Initialized\n%s" % (self.alarms,))


    def handle_message(self, msg):
        if msg.data['subtype'] == 'oob_detect' and msg.data['verb'] == 'snooze':
            # snooze means we create a new alarm for 
            # 5 minutes from now and then we go dead
            now = datetime.datetime.now()
            now_plus_5m = now + datetime.timedelta(minutes = 5)
            response = self.add_alarm(now_plus_5m, 'tbd')
            self.alarm_active.active = False
            self.send_release_message()


    def send_reserve_message(self):
        # acquire the oob verbs 'stop' and 'snooze'
        info = {
                'subtype':'reserve_oob',
                'skill_id':'system_skill',
                'from_skill_id':self.skill_id,
                'verb':'stop'
                }
        #self.bus.emit(Message(MSG_SYSTEM, info))
        self.bus.send(MSG_SYSTEM, 'system_skill', info)
        info['verb'] = 'snooze'
        #self.bus.emit(Message(MSG_SYSTEM, info))
        self.bus.send(MSG_SYSTEM, 'system_skill', info)


    def send_release_message(self):
        # release the oob verbs 'stop' and 'snooze'
        info = {
                'subtype':'release_oob',
                'skill_id':'system_skill',
                'from_skill_id':self.skill_id,
                'verb':'stop'
                }
        #self.bus.emit(Message(MSG_SYSTEM, info))
        self.bus.send(MSG_SYSTEM, 'system_skill', info)
        info['verb'] = 'snooze'
        #self.bus.emit(Message(MSG_SYSTEM, info))
        self.bus.send(MSG_SYSTEM, 'system_skill', info)


    def play_beep(self):
        self.play_media(self.beep_filename, delete_on_complete=False)


    def get_time(self, sentence):
        # given an utterance returns ...
        # '' if can not extract time from sentence
        # 'abort' if the user spoke a terminate alias
        # or a valid date time 
        have_date, have_time, hour, minute, dt = get_time_from_utterance(sentence)

        if have_date:
            if have_time:
                return dt
            else:
                return self.have_date_no_time(dt)
        else:
            if have_time:
                # have no date but have a time?
                user_prompt = 'Wow, we have a time but not a date. You got me! No alarm created.'
                self.speak(user_prompt)
                return ''
            else:
                # have no date or time
                return self.have_no_date_and_no_time(dt)

        return ''


    def handle_expired_alarm(self, alarm):
        # we have an expired alarm. we need to 
        # set up a recurring timer to play our
        # alarm sound until told to stop.
        self.alarms.remove(alarm)
        self.update_alarm_db()
        self.alarm_active.active = True
        # go live
        self.send_reserve_message()


    def remove_expired_alarms(self, alarms):
        now = datetime.datetime.now()
        now = now + timedelta(minutes=3)
        nowd = now.strftime("%Y-%m-%d %H:%M:%S")

        new_alarms = []
        for alarm in alarms:
            alarm = alarm.strip()
            if len(alarm) > 0:
                aa = alarm.split(",")
                expires_at = aa[0]
                expires_at =  datetime.datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                if expires_at > now:
                    new_alarms.append(alarm)
                else:
                    self.log.info("expired alarm excluded = %s" % (alarm,))

        return new_alarms


    def update_alarm_db(self):
        # we always just overwrite
        fh = open(self.db_filename, 'w')
        for alarm in self.alarms:
            fh.write(alarm + '\n')
        fh.close()


    def get_alarm_from_db(self, alarm):
        fh = open(self.db_filename)
        alarms = fh.readlines()
        fh.close()
        for alm in alarms:
            aa = alm.split(",")
            expires_at = aa[0]
            self.log.debug("get from db, alm:%s, expires:%s" % (alarm, expires_at))
            if expires_at == alarm:
                return True
        return False


    def remove_alarm(self, alarm_time, alarm_name):
        self.alarms.remove(alarm_time)
        self.update_alarm_db()


    def add_alarm(self, alarm_time, alarm_name):
        self.log.debug("add alarm to db. time:%s, name:%s" % (alarm_time, alarm_name))
        alarm_time = alarm_time.replace(second=0, microsecond=0)
        alarm_time = alarm_time.strftime("%Y-%m-%d %H:%M:%S")
        self.log.error("alarm after adjustment ---> %s" % (alarm_time,))
        if self.get_alarm_from_db(alarm_time):
            self.log.warning("Error - duplicate alarm %s" % (alarm_time,))
            return False

        new_alarm = "%s,%s" % (alarm_time, alarm_name) 
        self.alarms.append( new_alarm )
        self.update_alarm_db()
        return True


    def cancel_converse(self, user_input):
        for word in self.cancel_converse_words:
            if word in user_input:
                return True
        return False


    def handle_user_confirmation_input(self, user_response):
        # handle bail out 
        if self.cancel_converse(confirmation):
            self.speak('No alarm created')
            return False

        if confirmation == 'yes':
            user_prompt = "Created new alarm for %s" % (speakable_date_time)
            self.speak(user_prompt)
            return True
        else:
            self.speak('No alarm created')
            return False

    def have_date_and_time(self, dt):
        # Have date and time
        dom = int( dt.strftime("%d") )
        spoken_dom = self.inflect_thing.ordinal(dom)
        tail = dt.strftime("at %I %M %p")
        speakable_date_time = dt.strftime("%A %B") + ' ' + spoken_dom + ' ' + tail
        speakable_date_time = speakable_date_time.replace(" 00","")
        speakable_date_time = re.sub(r'0+(.+)', r'\1', speakable_date_time)
        confirmation_prompt = "Confirm create new alarm for %s. Is that correct?" % (speakable_date_time)
        self.get_user_confirmation(self.handle_user_confirmation_input, confirmation_prompt, self.handle_datetime_timeout)

    def handle_datetime_timeout(self):
        self.speak('No alarm created.')

    def handle_datetime_input(self, user_response):
        have_date, have_time, hour, minute, dt = get_time_from_utterance(user_response)
        self.speak("got date time input.")

    def handle_time_input(self, user_response):
        self.speak("got time input.")

        """
        unused, hour, minute = get_raw(user_response)

        ampm = get_ampm(user_response)

        if hour != 0:
            have_time = True
            # dt hour is in 24 hour format so we need 
            # to handle that. also note lf assumes utc
            # unless you overide it by passing in an
            # anchorDate.
            if ampm is not None:
                if ampm == 'pm':
                    hour += 12
            dt = dt.replace(hour=hour, minute=minute)
            return dt

        # otherwise we could not get a complete 
        # date and time - missing valid time!
        return ''
        """

    def have_no_date_and_no_time(self, dt):
        user_prompt = 'Create an alarm for when?'
        self.get_user_input(self.handle_datetime_input, user_prompt, self.handle_datetime_timeout)


    def have_date_no_time(self, dt):
        # otherwise have date but no time
        hour = 0
        minute = 0

        dom = int( dt.strftime("%d") )
        spoken_dom = self.inflect_thing.ordinal(dom)
        speakable_date = dt.strftime("%A %B") + ' ' + spoken_dom
        speakable_date = speakable_date.replace(" 00","")
        speakable_date = re.sub(r'0+(.+)', r'\1', speakable_date)

        user_prompt = "Create an alarm at what time on %s?" % (speakable_date)
        self.get_user_input(self.handle_time_input, user_prompt, self.handle_datetime_timeout)


    def get_speakable(self, date_string):
        date_string = str(date_string)
        dt = datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S%z")
        dom = int( dt.strftime("%d") )
        spoken_dom = self.inflect_thing.ordinal(dom)
        s = dt.strftime("%A, %B ")
        s += spoken_dom
        hr = int( dt.strftime("%I") )
        mi = int( dt.strftime("%M") )
        spoken_minute = str(mi)
        if mi < 10:
            spoken_minute = ' oh ' + str(mi)
        ampm = dt.strftime("%p")
        t = " at %s %s %s" % (hr, spoken_minute, ampm)
        s += t
        return s


    def handle_delete(self, message):
        sentence = message.data['utt']['sentence']
        del_all = False
        if sentence.find(" all ") > -1:
            del_all = True
        alarm_time = self.get_time(sentence)
        for alarm in self.alarms:
            aa = alarm.split(",")
            alm = aa[0]
            alm = datetime.datetime.strptime(alm, "%Y-%m-%d %H:%M:%S")
            alm = alm.astimezone()
            if alm == alarm_time or del_all:
                self.remove_alarm(alarm,'tbd')
                self.speak("Alarm deleted.")
                return True

        self.speak("No alarm deleted.")
        return False


    def handle_show(self, message):
        if len(self.alarms) == 0:
            self.speak("You have no alarms.")
            return False

        self.speak("You have the following alarms")
        for alarm in self.alarms:
            aa = alarm.split(",")
            alm = aa[0]
            alm = datetime.datetime.strptime(alm, "%Y-%m-%d %H:%M:%S")
            alm = pytz.utc.localize(alm)
            alm = self.get_speakable(alm)
            self.speak(alm)
        return True


    def handle_create(self, message):
        self.log.debug("Alarm Skill Create Called: %s" % (message.data,))

        sentence = message.data['utt']['sentence']
        prompt = 'I am sorry but I did not understand'

        new_alarm_time = self.get_time(sentence)

        self.log.error("XXXX Create Alarm, detect past, new_alarm_time:%s, now:%s" % (new_alarm_time, datetime.datetime.now(new_alarm_time.tzinfo)))
        if new_alarm_time <= datetime.datetime.now(new_alarm_time.tzinfo):
            self.log.error("XXXX Create Alarm, new alarm is in the past!")
            self.speak("Can not create an alarm in the past")
            return False

        if new_alarm_time == '':
            self.speak(prompt)

        elif new_alarm_time == 'abort':
            self.speak('Create alarm aborted')

        else:
            if new_alarm_time is not None:
                response = self.add_alarm(new_alarm_time, 'tbd')
                if response:
                    speakable_date = self.get_speakable(new_alarm_time)
                    resp = "Alarm created for %s" % (speakable_date,)
                    self.speak(resp)
                    return True
                else:
                    # if error probably duplicate so inform the user
                    self.speak("Duplicate alarm. No alarm created.")
            else:
                self.speak("Alarm for when not supported yet.")

        return False


    def stop(self,msg=None):
        self.log.error("Do Nothing Alarm stop() hit !, alarm_active=%s, alarms=%s" % (self.alarm_active.active,self.alarms))
        self.alarm_active.active = False
        #self.send_release_message()


    def handle_stop(self, msg):
        self.log.error("Alarm handle_stop() hit !, alarm_active=%s, sending release msg, alarms=%s" % (self.alarm_active.active,self.alarms))
        self.alarm_active.active = False
        self.send_release_message()


if __name__ == '__main__':
    my_alarm_skill = AlarmSkill()
    Event().wait()  # Wait forever

