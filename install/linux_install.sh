#!/bin/bash
#
# should be run from minimy base dir
# Example:
#     install/linux_install.sh
#
date
echo 'Begin Installation, MiniMy Version 1.0.2'
sudo apt install python3-venv
sudo apt install python3-dev
python3 -m venv venv_ngv
source venv_ngv/bin/activate
pip install --upgrade pip
pip install --upgrade wheel setuptools
pip install setuptools -U
sudo apt install python-dev
sudo apt install build-essential
sudo apt install portaudio19-dev
# try skipping these
#sudo apt install ffmpeg
#sudo apt install curl
#sudo apt install wget
sudo apt install mpg123
pip install -r install/requirements.txt

deactivate

echo 'Installing Internet music tools'
pip install youtube-search 
sudo curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl
sudo chmod a+rx /usr/local/bin/yotube-dl

echo 'Installing Local NLP'
cd framework/services/intent/nlp/local
tar xzfv cmu_link-4.1b.tar.gz
cd link-4.1b
make
cd ../../../../../..

echo 'Installing Local STT'
cd framework/services/stt/local/CoquiSTT/ds_model
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/huge-vocabulary.scorer
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/alphabet.txt
wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/model.tflite
cd ..
bash install_linux.sh
cd ../../../../..

echo 'Installing Local TTS'
cd framework/services/tts/local
wget http://rioespana.com/images/mimic3.tgz
tar xzfv mimic3.tgz
cd mimic3
make install
cd ../../../../..

# fix bug in mimic3 install mia dependency
deactivate
source framework/services/tts/local/mimic3/.venv/bin/activate
pip install importlib-resources
deactivate

source venv_ngv/bin/activate
echo ' '
echo 'Install Complete'
echo ' '
cat doc/final_instructions.txt
date
