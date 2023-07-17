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
sudo apt install python3-venv
sudo apt install python3-dev
python3 -m venv venv_ngv
source venv_ngv/bin/activate
pip install --upgrade pip
pip install --upgrade wheel setuptools
pip install setuptools -U
sudo apt install -y python3-dev
sudo apt install -y build-essential
sudo apt install -y portaudio19-dev
sudo apt install -y mpg123
sudo apt install -y ffmpeg
sudo apt install -y curl
sudo apt install -y wget
python3 -m pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz
pip install -r install/requirements.txt
pip install lingua_franca
pip install youtube-search 
pip install pyee 
pip install RPi.GPIO
pip install keyboard 
pip install PyDictionary 
deactivate

echo
echo "Installing Internet music tools"
pip install youtube-search-python
sudo cp install/ytplay /usr/local/sbin
sudo ln -s /usr/local/sbin/ytplay /usr/local/sbin/ytadd
# try skipping youtube-dl - is it no longer used?
# sudo curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl
#sudo chmod a+rx /usr/local/bin/yotube-dl

echo
echo "Installing Local NLP"
cd framework/services/intent/nlp/local
tar xzfv cmu_link-4.1b.tar.gz
cd link-4.1b
make
cd ../../../../../..

echo
echo "Installing Local STT"
cd framework/services/stt/local/CoquiSTT/ds_model
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/huge-vocabulary.scorer
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/alphabet.txt
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/model.tflite
cd ..
bash install_linux.sh
cd ../../../../..

echo
echo "Installing Local TTS"
cd framework/services/tts/local
wget http://rioespana.com/images/mimic3.tgz
tar xzfv mimic3.tgz
cd mimic3
make install
cd ../../../../..

# deactivate was not found in the PATH
# deactivate
source framework/services/tts/local/mimic3/.venv/bin/activate
pip install importlib-resources
deactivate

echo
echo "Copying and enabling systemd .mount files to create in-memory file systems"
sudo cp install/home-pi-minimy-logs.mount /etc/systemd/system 
sudo cp install/home-pi-minimy-tmp.mount /etc/systemd/system 
sudo systemctl enable home-pi-minimy-logs.mount 
sudo systemctl enable home-pi-minimy-tmp.mount 

source venv_ngv/bin/activate
echo " "
echo "Install Complete"
echo " "
# out of date:
# cat doc/final_instructions.txt
date
