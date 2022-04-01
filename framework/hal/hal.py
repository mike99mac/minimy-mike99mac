import abc

class Hal:
    """ this represents the minimum functionality
    a hal must provide. a voice system consists 
    of an audio input device and audio output
    device and the ability to control their levels """
    __metaclass__ = abc.ABCMeta
    @abc.abstractmethod
    def __init__(self, input_device_id, input_level_control_name, output_device_name, output_level_control_name):
        self.input_device_id = input_device_id
        self.input_level_control_name = input_level_control_name
        self.output_device_name = output_device_name
        self.output_level_control_name = output_level_control_name 

    @abc.abstractmethod
    def get_input_device_id(self):
        """returns an int """
        return self.input_device_id

    @abc.abstractmethod
    def get_output_device_name(self):
        """returns a string suitable for use with aplay and mpg123 """
        return self.output_device_name

    @abc.abstractmethod
    def get_input_level_control_name(self):
        """returns a string suitable for use with amixer """
        return input_level_control_name

    @abc.abstractmethod
    def get_output_level_control_name(self):
        """returns a string suitable for use with amixer """
        return output_level_control_name

    @abc.abstractmethod
    def get_input_level(self):
        """returns a value between 0-100% """
        return -1

    @abc.abstractmethod
    def get_output_level(self):
        """returns a value between 0-100% """
        return -1

    @abc.abstractmethod
    def set_input_level(self, new_level):
        return

    @abc.abstractmethod
    def set_output_level(self, new_level):
        return

