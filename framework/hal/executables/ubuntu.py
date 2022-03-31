from .HalAbc import HalAbc
from framework.util.utils import execute_command
import os

class Platform(HalAbc):
    """ standard linux ubuntu type hardware support. Note
        additional mute/unmute support is also provided """
    def __init__(self, input_device_id, input_level_control_name, output_device_name, output_level_control_name):
        self.type = 'Ubuntu'
        self.input_device_id = input_device_id

        #self.input_level_control_name = input_level_control_name
        self.input_level_control_name = "Mic Boost"

        self.output_device_name = output_device_name

        #self.output_level_control_name = output_level_control_name
        self.output_level_control_name = "Master"

        os.system("amixer sset Capture 100%")
        os.system("amixer sset 'Mic Boost' 100%")
        os.system("amixer sset Master 100%")
        os.system("amixer sset Speaker 100%")

    def set_input_level(self, new_level):
        cmd = "amixer sset '%s' %s%%" % (self.input_level_control_name, new_level)
        os.system(cmd)

    def get_input_level(self):
        cmd = "amixer sget '%s'" % (self.input_level_control_name,)
        res = execute_command(cmd)
        res = res.split("\n")

        for line in res:
            if line.find("Limits") == -1:
                start_indx = line.find("[")
                if start_indx > -1:
                    line = line[start_indx + len("["):]
                    start_indx = line.find("]")
                    if start_indx != -1:
                        end_indx = line.find("]")
                        current_volume = line[:end_indx].replace("%","")
                        return current_volume

    def set_output_level(self, new_level):
        cmd = "amixer sset %s %s%%" % (self.output_level_control_name, new_level)
        os.system(cmd)

    def get_output_level(self):
        cmd = "amixer sget %s" % (self.output_level_control_name,)
        res = execute_command(cmd)
        res = res.split("\n")

        for line in res:
            if line.find("Limits") == -1:
                start_indx = line.find("Playback ")
                if start_indx > -1:
                    line = line[start_indx + len("Playback "):]
                    start_indx = line.find("[")
                    if start_indx != -1:
                        end_indx = line.find("]")
                        current_volume = line[start_indx+1:end_indx].replace("%","")
                        return current_volume

    def get_input_device_id(self):
        return self.input_device_id

    def get_output_device_name(self):
        return self.output_device_name

    def get_input_level_control_name(self):
        return input_level_control_name

    def get_output_level_control_name(self):
        return output_level_control_name

    def mute_master(self, new_level):
        os.system("amixer -q -D pulse sset Master mute")

    def unmute_master(self, new_level):
        os.system("amixer -q -D pulse sset Master unmute")

