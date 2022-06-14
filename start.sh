echo '** System Starting ... **'
echo 'Note - you may see some warnings here, dont worry about them'
cat install/mmconfig.yml | grep -v "AWS" | grep -v "Goog"

echo ' '
echo 'Start Local STT Server'
deactivate
cd framework/services/stt/local/CoquiSTT
source venv_coqui/bin/activate
python server.py --model-dir ds_model  > coqui_stt.log 2>&1 &
deactivate

cd ../../../../..

echo 'Start Local TTS Server'
cd framework/services/tts/local/mimic3
deactivate
source .venv/bin/activate
bin/mimic3 --model-dir voices/apope  > mimic3_tts.log 2>&1 &
deactivate

cd ../../../../..

source venv_ngv/bin/activate

export PYTHONPATH=`pwd`
export SVA_BASE_DIR=`pwd`

export GOOGLE_APPLICATION_CREDENTIALS=$PWD/install/my-google-speech-key.json

rm tmp/save_audio/*
rm tmp/save_text/*
rm tmp/save_tts/*

echo ' '
echo 'Starting Voice Framework'
echo ' '
echo 'Start Message Bus'
cd bus
python MsgBus.py &
cd ..
sleep 2

echo 'Start System Skill'
cd skills/system_skills
python skill_system.py &
sleep 1
cd ../../

echo 'Start Services'
echo ' '
echo 'Intent Service'
python framework/services/intent/intent.py &
sleep 2 

echo ' '
echo 'Media Service'
python framework/services/output/media_player.py &
python framework/services/tts/tts.py &
python framework/services/stt/stt.py &
sleep 1

echo ' '
echo 'Start System Skills'
#cd ../../skills/system_skills

python skills/system_skills/skill_fallback.py &
python skills/system_skills/skill_media.py &
python skills/system_skills/skill_volume.py &
python skills/system_skills/skill_alarm.py &
sleep 2 

echo ' '
echo 'Start User Skills'
cd skills/user_skills

# TODO automate this


cd help
echo 'Load Help Skill'
python __init__.py $PWD &

echo 'Loading RFM skill!'
cd ../rfm
python __init__.py $PWD &

echo 'Warning! NOT loading youtube music skill!'
#cd ../youtube
#python __init__.py $PWD &

echo 'Load Email Skill'
cd ../email
python __init__.py $PWD &

echo 'Load Wiki Skill'
cd ../wiki
python __init__.py $PWD &

echo 'Load TimeDate Skill'
cd ../timedate
python __init__.py $PWD &

echo 'Load Example 1 Skill'
cd ../example1
python __init__.py $PWD &

echo 'Load NPR News Skill'
cd ../npr_news
python __init__.py $PWD &

echo 'Load Weather Skill'
cd ../weather
python __init__.py $PWD &

echo 'Warning! NOT loading Home Assistant skill!'
#cd ../ha_skill
#python __init__.py $PWD &

echo 'Load Connectivity Skill'
cd ../connectivity
python __init__.py $PWD &

cd ../../..

echo ' '
echo 'Wait Skills Init'
echo ' '
sleep 3
echo 'Finally, start the mic'
source venv_ngv/bin/activate
python framework/services/input/mic.py &
echo ' '
echo '** System Started **'
