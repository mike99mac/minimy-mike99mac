import os

# TODO should probably get these
# names from a common place 

print("HAL: Linux initializer called")

os.system("amixer sset Capture 100%")
os.system("amixer sset Master 100%")
os.system("amixer sset 'Mic Boost' 100%")
os.system("amixer sset Speaker 100%")
