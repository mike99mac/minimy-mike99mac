date
#
# should be run from sva base dir
# Example:
#     install/linux_install.sh
# will install using default python 3.8
#
#     install/linux_install.sh 3.9
# will install using python 3.9
#
echo 'Begin Installation, MiniMy Version 1.0.0'
if [ "$1" ]; then
  sudo apt install python$1-venv
  sudo apt install python$1-dev
else
  sudo apt install python3.8-venv
  sudo apt install python3.8-dev
fi

python3 -m venv venv_ngv
source venv_ngv/bin/activate
pip install --upgrade pip
pip install --upgrade wheel setuptools
pip install setuptools -U
sudo apt install python-dev
sudo apt install build-essential
sudo apt install portaudio19-dev
sudo apt install ffmpeg
sudo apt install curl
sudo apt install wget
sudo apt install mpg123
pip install -r install/requirements.txt

deactivate

echo 'Installing Local NLP'
cd framework/services/intent/nlp/local
tar xzfv cmu_link-4.1b.tar.gz
cd link-4.1b
make
cd ../../../../../..

echo 'Installing Local STT'
# fetch stt model 
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
