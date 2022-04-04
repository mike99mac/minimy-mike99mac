from threading import Event
from skills.sva_base import SimpleVoiceAssistant
from haclient import HomeAssistantClient

class HALightSwitch(SimpleVoiceAssistant):
    """
    simple home assistant skill supporting switches and sensors
    user must make sure home assistant friendly names are set
    as well as any aliases for the device. this skill will auto
    discover switches and sensors and auto register the intents
    """
    def __init__(self, bus=None, timeout=5):
        self.skill_id = 'ha_skill'
        super().__init__(skill_id=self.skill_id, skill_category='user')

        # TODO stuff in a skill config file
        # for now user must manually edit these
        # ha long lived access token 
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJiYjE1ZDU2NTYyYzI0NmVkOTcyMWM2MWU1ZGZjYmQzOCIsImlhdCI6MTY0ODUxNTg3OSwiZXhwIjoxOTYzODc1ODc5fQ.H82X0YNFEh210lKzNK-GOi7Woxl3VbaPPZi7ZwizQkE"
        # could be localhost
        host = "10.0.0.198"
        port = 8123

        config = {'ip_address': host,
                       'token': token,
                       'port_number': port,
                       }

        self.ha_client = HomeAssistantClient(config)

        # we support switches and sensors
        switches = []
        sensors = []
        entity_id = None

        # get list of entities from home assistant
        res = self.ha_client._get_state()
        for r in res:
            entity_id = r['entity_id']
            if entity_id.startswith('switch'):
                switch_name = r['attributes']['friendly_name']
                if switch_name:
                    switches.append(switch_name)

            if entity_id.startswith('sensor'):
                sensor_name = r['attributes']['friendly_name']
                if sensor_name:
                    sensors.append(sensor_name)

        questions = ['what', 'how', 'is']
        commands = ['set', 'turn', 'change', 'modify']

        # register switch command intents
        for switch in switches:
            for command in commands:
                self.register_intent('C', command, switch, self.handle_command_switch)
        # register switch question intents
        for switch in switches:
            for question in questions:
                self.register_intent('Q', question, switch, self.handle_query_switch)
        # register sensor question intents
        for sensor in sensors:
            for question in questions:
                self.register_intent('Q', question, sensor, self.handle_query_sensor)

    def handle_command_switch(self,msg):
        val = msg.data['utt']['value']
        switch_alias = msg.data['utt']['subject']

        # TODO shouldn't have to do this here
        switch_alias = switch_alias.replace("the ","")
        switch_alias = switch_alias.strip()
        switch_alias = switch_alias.lower()

        entity_id = self.ha_client.get_entity_id_for_alias(switch_alias)
        new_state = 'turn_' + val
        res = self.ha_client.execute_service("homeassistant", new_state, {"entity_id": entity_id})
        text = "I have turned the %s %s" % (switch_alias,val)
        self.speak(text)

    def handle_query_switch(self, message):
        switch_alias = message.data['utt']['subject']
        switch_state = self.ha_client.get_entity_state_for_alias(switch_alias)
        self.speak(switch_state)

    def handle_query_sensor(self, message):
        sensor_alias = message.data['utt']['subject']
        sensor_state = self.ha_client.get_entity_state_for_alias(sensor_alias)
        self.speak(sensor_state)

    def stop(self,msg):
        pass

    def stop(self):
        pass

if __name__ == '__main__':
    has = HALightSwitch()
    Event().wait()  # Wait forever
