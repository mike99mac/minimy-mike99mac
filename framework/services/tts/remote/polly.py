import boto3, wave
from framework.util.utils import Config

class remote_tts:
    def __init__(self):
        cfg = Config()
        self.cfg_aws_id = cfg.get_cfg_val('Basic.AWSId')
        self.cfg_aws_key = cfg.get_cfg_val('Basic.AWSKey') 

    def remote_speak(self, text, filename, wait_q):
        status = 'fail'
        CHANNELS = 1 #Polly's output is a mono audio stream
        RATE = 16000 #Polly supports 16000Hz and 8000Hz output for PCM format
        FRAMES = []
        WAV_SAMPLE_WIDTH_BYTES = 2 # Polly's output is a stream of 16-bits (2 bytes) samples

        try:
            polly = boto3.Session(
                aws_access_key_id=self.cfg_aws_id,
                aws_secret_access_key=self.cfg_aws_key,
                region_name='us-west-2').client('polly')
        except:
            print("TTS Polly Remote request failed on connect!")
        try:
            response = polly.synthesize_speech(Text=text, TextType="text", OutputFormat="pcm",VoiceId="Matthew", SampleRate="16000")
            #response = polly.synthesize_speech(Text=text, TextType="text", OutputFormat="pcm",VoiceId="Amy", SampleRate="16000")
            status = 'success'
        except:
            print("TTS Polly Remote request failed on synth!")

        if status == 'success':
            STREAM = response.get("AudioStream")
            FRAMES.append(STREAM.read())
            WAVEFORMAT = wave.open(filename,'wb')
            WAVEFORMAT.setnchannels(CHANNELS)
            WAVEFORMAT.setsampwidth(WAV_SAMPLE_WIDTH_BYTES)
            WAVEFORMAT.setframerate(RATE)
            WAVEFORMAT.writeframes(b''.join(FRAMES))
            WAVEFORMAT.close()

        wait_q.put({'service':'remote', 'status':status})

