"""
Home Assistant Client
Uses REST API
"""
import json
import time
from requests import get, post

# Timeout time for HA requests
TIMEOUT = 10

class HomeAssistantClient:
    """Home Assistant client class"""
    def __init__(self, config):
        self.ssl = False
        token = config['token']
        ip_address = config['ip_address']
        port_number = config['port_number']
        self.url = f"http://{ip_address}"
        if port_number:
            self.url = f"{self.url}:{port_number}"
        self.headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': 'application/json'
        }
        self.tts_uom={
                '°F':'degrees farenheight',
                '°C':'degrees celsius',
                'lx':'lumens',
                '%':'percent',
                }

    def _get_state(self) -> json:
        if self.ssl:
            req = get(f"{self.url}/api/states", headers=self.headers,
                      verify=self.verify, timeout=TIMEOUT)
        else:
            req = get(f"{self.url}/api/states", headers=self.headers,
                      timeout=TIMEOUT)
        req.raise_for_status()
        return req.json()

    def connected(self) -> bool:
        try:
            self._get_state()
            return True
        except:
            return False

    def execute_service(self, domain: str, service: str, data: dict):
        if self.ssl:
            req = post(f"{self.url}/api/services/{domain}/{service}",
                       headers=self.headers, data=json.dumps(data),
                       verify=self.verify, timeout=TIMEOUT)
        else:
            req = post(f"{self.url}/api/services/{domain}/{service}",
                       headers=self.headers, data=json.dumps(data),
                       timeout=TIMEOUT)
        req.raise_for_status()
        return req

    def get_entity_id_for_alias(self, alias):
        entity_id = None
        res = self._get_state()
        for r in res:
            if r['entity_id'].startswith('switch'):
                if r['attributes']['friendly_name'] == alias:
                    entity_id = r['entity_id']
                    break
        return entity_id

    def get_entity_state_for_alias(self, alias):
        err_response = "I could not get the current state of the device"
        entity_id = None
        res = self._get_state()
        for r in res:
            entity_id = r.get('entity_id', None)
            current_state = r.get('state',None)
            if entity_id is None:
                #self.log.warning("Device has no entity_id. %s" % (r,))
                break

            attributes = r.get('attributes',None)
            if attributes is None:
                #self.log.warning("Device has no attributes. %s" % (r,))
                break

            name = attributes.get('friendly_name',None)
            if name == alias:
                device_class = attributes.get('device_class',None)
                unit_of_measurement = attributes.get('unit_of_measurement',None)
                speakable_current_state = current_state.replace(".", " point ")
                spoken_uom = ''
                if unit_of_measurement and unit_of_measurement in self.tts_uom:
                    spoken_uom = self.tts_uom[unit_of_measurement]
                return "the %s reports %s %s" % (name, speakable_current_state, spoken_uom)

        return err_response

