#!/bin/bash
#
# should be run from minimy base dir
# Example:
#     install/linux_install.sh
#
#+--------------------------------------------------------------------------+
function runCmd
# run a command, report time spent and exit if it failes
#+--------------------------------------------------------------------------+
 {
  : SOURCE: ${BASH_SOURCE}
  : STACK:  ${FUNCNAME[@]}

  local timeStamp=`date +"%y-%m-%d-%H:%M:%S"`      # YY-MM-DD-HH:MM:SS
  cmd="$@"                                 # get all args
  let stepNum=$stepNum+1
  echo | tee -a $logFile
  echo "$timeStamp - Step $stepNum: $cmd ..." 2>&1 | tee -a $logFile # show the command and send to output file
  eval $cmd | tee -a $logFile 2>&1         # run command and log output
  rc=$?
  if [ "$rc" != 0 ]; then                  # it failed
    echo "ERROR: $cmd returned $rc" | tee -a $logFile
    exit 1
  fi
  let curSecs=$SECONDS
  let et=$curSecs-$lastSecs
  echo "Step took $et seconds"
  lastSecs=$curSecs
 }                                         # runCmd()

function doIt                              # do all the work
 {
  echo
  echo "Begin installation of minimy ..." | tee -a $logFile
  echo; echo "cd to $HOME/minimy ..." | tee -a $logFile
  cd $HOME/minimy
  runCmd sudo apt-get -qq install python3-venv
  runCmd sudo apt-get -qq install python3-dev
  runCmd python3 -m venv venv_ngv
  source venv_ngv/bin/activate
  echo; echo "Upgrading pip ..." | tee -a $logFile
  runCmd pip install --upgrade pip
  echo; echo "Upgrading wheel and setuptools ..." | tee -a $logFile
  runCmd pip install --upgrade wheel setuptools
  runCmd sudo apt-get -qq install -y python3-dev
  runCmd sudo apt-get -qq install -y build-essential
  runCmd sudo apt-get -qq install -y portaudio19-dev
  runCmd sudo apt-get -qq install -y mpg123
  runCmd sudo apt-get -qq install -y ffmpeg
  runCmd sudo apt-get -qq install -y curl
  runCmd sudo apt-get -qq install -y wget
  echo; echo "Installing yt-dlp and requirements.txt ..." | tee -a $logFile
  runCmd python3 -m pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz
  runCmd pip install -r install/requirements.txt
  runCmd pip install lingua_franca
  runCmd pip install youtube-search 
  runCmd pip install pyee 
  runCmd pip install faster-whisper
  echo; echo "Installing faster-whisper and downloading model ..." | tee -a $logFile
  runCmd python3 $HOME/minimy-mike99mac/fw.py
  runCmd pip install keyboard 
  runCmd pip install pyyaml
  runCmd pip install pytz
  runCmd pip install inflect
  runCmd pip install websockets --upgrade
  runCmd pip install faster-whisper 
  runCmd pip install youtube-search-python
  echo; echo "Installing local ytplay/ytadd in /usr/local/sbin ..." | tee -a $logFile
  runCmd sudo cp install/ytplay /usr/local/sbin
  runCmd sudo ln -s /usr/local/sbin/ytplay /usr/local/sbin/ytadd
  echo; echo "Deactivating virtual environment ..." | tee -a $logFile
  runCmd deactivate
  runCmd sudo apt install -y libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev
  echo; echo "cd to $HOME/minimy/framework/services/intent/nlp/local ..." | tee -a $logFile
  cd $HOME/minimy/framework/services/intent/nlp/local
  echo; echo "Building CMU link grammar ..." | tee -a $logFile
  runCmd tar xzfv cmu_link-4.1b.tar.gz
  echo; echo "cd to link-4.1b ..." | tee -a $logFile
  cd link-4.1b
  runCmd make
  echo; echo "cd to $HOME/minimy/framework/services/stt/local/CoquiSTT/ds_model ..." | tee -a $logFile
  cd $HOME/minimy/framework/services/stt/local/CoquiSTT/ds_model
  echo; echo "Installing Local STT ..." | tee -a $logFile
  runCmd wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/huge-vocabulary.scorer
  runCmd wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/alphabet.txt
  runCmd wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/model.tflite
  echo; echo "Installing Local TTS ..."| tee -a $logFile
  echo; echo "cd to framework/services/tts/local ..." | tee -a $logFile
  cd framework/services/tts/local
  runCmd wget http://rioespana.com/images/mimic3.tgz
  runCmd tar xzf mimic3.tgz
  echo; echo "cd to mimic3 and run make install ..." | tee -a $logFile
  cd mimic3
  runCmd make install
  echo; echo "cd to $HOME/minimy ..." | tee -a $logFile
  cd $HOME/minimy
  runCmd source framework/services/tts/local/mimic3/.venv/bin/activate
  runCmd pip install importlib-resources
  runCmd deactivate
  echo; echo "Copying and enabling systemd .mount and .service files ..." | tee -a $logFile 
  runCmd sudo cp install/home-pi-minimy-logs.mount /etc/systemd/system 
  runCmd sudo systemctl enable home-pi-minimy-logs.mount 
  runCmd sudo cp install/home-pi-minimy-tmp.mount /etc/systemd/system 
  runCmd sudo systemctl enable home-pi-minimy-tmp.mount 
  runCmd sudo cp install/minimy.service /etc/systemd/system 
  runCmd sudo systemctl enable minimy
  echo; echo "Copying Minimy scripts to /usr/local/sbin ..."| tee -a $logFile
  minimyScripts="startminimy stopminimy restartminimy grm cmpcode countminimy minimyver"
  echo; echo "cd to $HOME/minimy/install ..." | tee -a $logFile
  cd $HOME/minimy/install
  runCmd sudo cp $minimyScripts /usr/local/sbin 
  echo; echo "cd to /usr/local/sbin ..." | tee -a $logFile
  cd /usr/local/sbin
  runCmd sudo chown $USER:$USER $minimyScripts
  runCmd sudo cp $HOME/minimy/install/great_songs.m3u /var/lib/mpd/playlists
  echo; echo "Starting virtual environment ..." | tee -a $logFile
  source $HOME/minimy/venv_ngv/bin/activate
  echo " "
  echo "Install Complete at `date`" | tee -a $logFile
 }                                         # doIt()

# main()
let stepNum=0
let lastSecs=$SECONDS
timeStamp=`date +"%y-%m-%d-%H-%M-%S"`   
logFile="$HOME/$timeStamp-linux_install.out" # output file
echo "Running linux_install.sh on $timeStamp ..." > $logFile # create a new log file
doIt                                       # do the work
let min=$SECONDS/60
let sec=$SECONDS%60
if [ $sec -lt 10 ]; then                   # add a leading 0
  sec="0$sec"
fi
echo "Successfully installed Minimy in $min:$sec" | tee -a $logFile
echo "Log file: $logFile"

