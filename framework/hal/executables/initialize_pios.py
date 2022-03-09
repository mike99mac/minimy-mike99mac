import os

# TODO should probably get these
# names from a common place 

print("HAL: Pi OS 64bit initializer called")

os.system("amixer sset Capture 100%")
os.system("amixer sset Master 100%")
