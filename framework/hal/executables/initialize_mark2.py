import os

# TODO should probably get these
# names from a common place 

base_dir = os.getenv('SVA_BASE_DIR')
print("HAL: Mark2 initializer called")

os.system("amixer sset Record 100%")
os.system("amixer sset Playback 100%")
os.system("python %s/hal/executables/set_mark2_hardware_volume.py 100" % (base_dir,))
