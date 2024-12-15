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
  eval $cmd 2>&1 | tee -a $logFile         # run command and log output
  rc=$?
  if [ "$rc" != 0 ]; then                  # it failed
    echo "ERROR: $cmd returned $rc" | tee -a $logFile
    exit 1
  fi
  let curSecs=$SECONDS
  let et=$curSecs-$lastSecs
  echo "Step took $et seconds" | tee -a $logFile
  lastSecs=$curSecs
 }                                         # runCmd()

function doIt                              # do all the work
 {
  echo
  echo "Begin installation of minimy ..." | tee -a $logFile
  echo | tee -a $logFile
  echo "cd to $HOME/minimy ..." | tee -a $logFile
  cd $HOME/minimy
  echo | tee -a $logFile
  echo "Installing virtual environment ..." | tee -a $logFile
  runCmd sudo apt-get -qq install python3-venv
  runCmd sudo apt-get -qq install python3-dev
  runCmd python3 -m venv venv
  echo | tee -a $logFile
  echo "Upgrading pip ..." | tee -a $logFile
  local pipCmd="$HOME/minimy/venv/bin/pip"       # use pip from the venv
  runCmd $pipCmd install --upgrade pip
  echo | tee -a $logFile
  echo "Activating virtual environment ..." | tee -a $logFile
  runCmd source venv/bin/activate          # start virtual environment
  # runCmd "echo $VIRTUAL_ENV" - of course it is /home/pi/minimy/venv
  echo | tee -a $logFile
  echo "Upgrading wheel and setuptools ..." | tee -a $logFile
  runCmd $pipCmd install --upgrade wheel setuptools
  runCmd sudo apt-get -qq install -y python3-dev build-essential portaudio19-dev mpg123 ffmpeg curl wget
  runCmd sudo apt-get -qq install -y libavcodec-dev libavformat-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev
  echo | tee -a $logFile
  echo "Installing yt-dlp and requirements.txt ..." | tee -a $logFile
  local pythonVer=`python -V | awk '{print $2}' | awk -F'.' '{print $1"."$2}'`
  local pythonCmd="$HOME/minimy/venv/bin/python$pythonVer" # use python from the venv
  runCmd $pythonCmd -m pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz
  runCmd $pipCmd install -r install/requirements.txt
  runCmd $pipCmd install lingua_franca
  runCmd $pipCmd install youtube-search 
  runCmd $pipCmd install pyee 
  echo | tee -a $logFile
  echo "Installing whisper ..." | tee -a $logFile
  runCmd $pipCmd install git+https://github.com/openai/whisper.git
  runCmd $pipCmd install whisper
  runCmd $pipCmd install numpy
  runCmd $pipCmd install pyaudio
  runCmd $pipCmd install quart
  runCmd $pipCmd install keyboard 
  runCmd $pipCmd install torch
  runCmd $pipCmd install torchaudio
  runCmd $pipCmd install transformers
  runCmd $pipCmd install datasets
  runCmd $pipCmd install optimum
  runCmd $pipCmd install --upgrade --upgrade-strategy eager "optimum[neural-compressor]"

  echo | tee -a $logFile
  echo "Installing local ytplay/ytadd in /usr/local/sbin ..." | tee -a $logFile
  runCmd sudo cp install/ytplay /usr/local/sbin
  runCmd sudo ln -s /usr/local/sbin/ytplay /usr/local/sbin/ytadd
  runCmd $pipCmd install youtube-search-python
  echo | tee -a $logFile
  echo "Deactivating virtual environment ..." | tee -a $logFile
  deactivate                        # getting error: line 20: deactivate: command not found
  echo | tee -a $logFile
  nextDir=$HOME/minimy/framework/services/intent/nlp/local
  echo "cd to $nextDir ..." | tee -a $logFile
  cd $nextDir
  echo "current working directory:" | tee -a $logFile 
  pwd | tee -a $logFile
  echo "ls -la cmu*" | tee -a $logFile
  ls -la cmu* | tee -a $logFile
  echo | tee -a $logFile
  echo "Building CMU link grammar ..." | tee -a $logFile
  runCmd tar xzf cmu_link-4.1b.tar.gz
  echo | tee -a $logFile
  echo "cd to link-4.1b ..." | tee -a $logFile
  cd link-4.1b
  runCmd make
  #echo | tee -a $logFile
  #nextDir=$HOME/minimy/framework/services/stt/local/CoquiSTT/ds_model
  #iecho "cd to $nextDir ..." | tee -a $logFile
  #cd $nextDir
  #echo | tee -a $logFile
  #echo "Installing Local STT ..." | tee -a $logFile
  # don't use runCmd on 1st and 3rd wget - too much stdout
  #runCmd wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/huge-vocabulary.scorer
  #echo | tee -a $logFile
  #echo "getting github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/huge-vocabulary.scorer ..." | tee -a $logFile
  #wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/huge-vocabulary.scorer
  #runCmd wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/alphabet.txt
  #echo | tee -a $logFile
  #echo "getting github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/model.tflite ..." | tee -a $logFile
  #wget https://github.com/coqui-ai/STT-models/releases/download/english/coqui/v1.0.0-huge-vocab/model.tflite
  #echo | tee -a $logFile
  #echo "Installing Coqui ..."| tee -a $logFile
  #runCmd bash $HOME/minimy/framework/services/stt/local/CoquiSTT/install_linux.sh
  echo | tee -a $logFile
  echo "Installing Local TTS ..."| tee -a $logFile
  echo | tee -a $logFile
  nextDir=
  echo "cd to framework/services/tts/local ..." | tee -a $logFile
  cd framework/services/tts/local
  echo | tee -a $logFile
  echo "Running command: wget http://rioespana.com/images/mimic3.tgz" | tee -a $logFile
  wget http://rioespana.com/images/mimic3.tgz
  runCmd tar xzf mimic3.tgz
  echo | tee -a $logFile
  echo "cd to mimic3 and run make install ..." | tee -a $logFile
  cd mimic3
  runCmd make install
  echo | tee -a $logFile
  echo "cd to $HOME/minimy ..." | tee -a $logFile
  cd $HOME/minimy
  runCmd source framework/services/tts/local/mimic3/.venv/bin/activate
  runCmd $pipCmd install importlib-resources
  runCmd deactivate
  echo | tee -a $logFile
  echo "Copying and enabling systemd .mount and .service files ..." | tee -a $logFile 
  runCmd sudo cp install/home-pi-minimy-logs.mount /etc/systemd/system 
  runCmd sudo systemctl enable home-pi-minimy-logs.mount 
  runCmd sudo cp install/home-pi-minimy-tmp.mount /etc/systemd/system 
  runCmd sudo systemctl enable home-pi-minimy-tmp.mount 
  runCmd sudo cp install/minimy.service /etc/systemd/system 
  runCmd sudo systemctl enable minimy
  echo | tee -a $logFile
  echo "Copying Minimy scripts to /usr/local/sbin ..."| tee -a $logFile
  minimyScripts="startminimy stopminimy restartminimy grm cmpcode countminimy minimyver"
  echo | tee -a $logFile
  echo "cd to $HOME/minimy/install ..." | tee -a $logFile
  cd $HOME/minimy/install
  runCmd sudo cp $minimyScripts /usr/local/sbin 
  echo | tee -a $logFile
  echo "cd to /usr/local/sbin ..." | tee -a $logFile
  cd /usr/local/sbin
  runCmd sudo chown $USER:$USER $minimyScripts
  runCmd sudo cp $HOME/minimy/install/great_songs.m3u /var/lib/mpd/playlists
  echo | tee -a $logFile
  echo "Starting virtual environment ..." | tee -a $logFile
  source $HOME/minimy/venv/bin/activate
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

