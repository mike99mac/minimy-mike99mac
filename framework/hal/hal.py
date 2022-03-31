import importlib
from framework.util.utils import Config

class Hal:
    """ the Hal class represents the platform.
        it determines which module to use from
        the system config file. it also provides
        the module constructor with the default
        values contained in the system config file""" 
    def __init__(self):
        cfg = Config()
        # get module name from config file
        
        # import the module
        module_name = cfg.get_cfg_val('Advanced.Platform')
        module_filename = "framework.hal.executables." + module_name
        module = importlib.import_module(module_filename, package=None)

        # get default values from config file
        input_device_id = cfg.get_cfg_val('Advanced.InputDeviceId')
        output_device_name = cfg.get_cfg_val('Advanced.OutputDeviceName')
        input_level_control_name = cfg.get_cfg_val('Advanced.InputLevelControlName')
        output_level_control_name = cfg.get_cfg_val('Advanced.OutputLevelControlName')
        self.platform = module.Platform(input_device_id, input_level_control_name, output_device_name, output_level_control_name)

