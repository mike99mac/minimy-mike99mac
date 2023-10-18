#!/bin/bash
#
# should be run from minimy base dir
# Example:
#     install/linux_install.sh
#
echo
date
version=`cat ../version`
echo "Begin Installation, MiniMy Version $version"
echo; echo "Step 1): installing python3-venv..." 
sudo apt install python3-venv
echo; echo "Step 2): installing python3-dev..." 
sudo apt install python3-dev
python3 -m venv venv_ngv
source venv_ngv/bin/activate
echo; echo "Step 3): upgrading pip ..." 
pip install --upgrade pip
echo; echo "Step 4): upgrading wheel and setuptools..." 
pip install --upgrade wheel setuptools
pip install setuptools -U
echo; echo "Step 5): installing python3-dev..." 
sudo apt install -y python3-dev
echo; echo "Step 6): installing build-essential..." 
sudo apt install -y build-essential
echo; echo "Step 7): installing portaudio19-dev..." 
sudo apt install -y portaudio19-dev
echo; echo "Step 8): installing mpg123..." 
sudo apt install -y mpg123
echo; echo "Step 9): installing ffmpeg..." 
sudo apt install -y ffmpeg
echo; echo "Step 10): installing curl..." 
sudo apt install -y curl
echo; echo "Step 11): installing wget..." 
sudo apt install -y wget
echo; echo "Step 12): installing yt-dlp..." 
python3 -m pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz
pip install -r install/requirements.txt
echo; echo "Step 13): installing ...lingua_franca" 
pip install lingua_franca
echo; echo "Step 14): installing youtube-search..." 
pip install youtube-search 
echo; echo "Step 15): installing pyee..." 
pip install pyee 
echo; echo "Step 16): installing RPi.GPIO..." 
pip install RPi.GPIO
echo; echo "Step 17): installing keyboard..." 
pip install keyboard 
# PyDictionary seems to pull in 'futures' which causes problems...
# echo; echo "installing ..." 
# pip install PyDictionary 
deactivate
echo; echo "Step 18): installing Internet music tools"
pip install youtube-search-python
sudo cp install/ytplay /usr/local/sbin
sudo ln -s /usr/local/sbin/ytplay /usr/local/sbin/ytadd
# try skipping youtube-dl - is it no longer used?
# sudo curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl
#sudo chmod a+rx /usr/local/bin/yotube-dl

echo
echo "Step 19) installing Local NLP"
cd framework/services/intent/nlp/local
tar xzfv cmu_link-4.1b.tar.gz
cd link-4.1b
make
cd ../../../../../..

echo
echo "Step 20) installing Local STT"
cd framework/services/stt/local/CoquiSTT/ds_model
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/huge-vocabulary.scorer
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/alphabet.txt
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/model.tflite
cd ..
bash install_linux.sh
cd ../../../../..

echo
echo "Step 21) installing Local TTS"
cd framework/services/tts/local
wget http://rioespana.com/images/mimic3.tgz
tar xzfv mimic3.tgz
cd mimic3
make install
cd ../../../../..

source framework/services/tts/local/mimic3/.venv/bin/activate
pip install importlib-resources
deactivate

echo
echo "Step 22) copying and enabling systemd .mount files to create in-memory file systems"
sudo cp install/home-pi-minimy-logs.mount /etc/systemd/system 
sudo cp install/home-pi-minimy-tmp.mount /etc/systemd/system 
sudo systemctl enable home-pi-minimy-logs.mount 
sudo systemctl enable home-pi-minimy-tmp.mount 

source venv_ngv/bin/activate
echo " "
echo "Install Complete!"
echo " "
date
