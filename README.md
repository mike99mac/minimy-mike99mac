# Minimy

This is a fork of Ken-Mycroft's code at: https://github.com/ken-mycroft/minimy

## Overview
**From Ken Smith - the original author:**

"The goal of this project is to provide a run-time environment which facilitates the development of 
voice enabled applications. These voice enabled applications take the form of a 'skill' and are
simply python programs which may do normal python things as well as call speak() and listen() and
get called asynchronously when an utterance is matched to an intent the skill has previously registered."  

**From Mike Mac - author of this fork:**

This code enables a device to play music by voice. 

I worked with Mycroft since 2019, but the company went bankrupt in 2023, so had to move on. :((  Thanks for all the hard work the Mycroft employees and contributors did to get us this far.

OVOS is a fork of Mycroft. I tried it but was not able to get a music skill working after a couple weeks.  I still haven't given up on it - no doubt it will only get better and easier to install.

Then I found Minimy, and was able to get it running in a few hours. Apparently, it was a project that hoped to save Mycroft from the fire but wasn't well received. Thankfully, Ken Smith put it on github, it was forked, and here we are.  Ken has been a great help in answering my many questions - **Thanks Dude!** 
So I continue to try to *give back to the community* while *standing on the shoulders* of so many others.

This document focuses on how to get the solution running, and starts from the very beginning.

## The build

The environment used to develop the code and write this document is a RasPi 4B with 4 GB of memory, running Ubuntu Desktop 22.04 inside an *enclosure* that is a retro-looking boombox. However, this code and these steps should be relatively portable to any hardware that can run any Linux. 

The overall steps to build a *Smart Boombox* are:

- Acquire the hardware 
- Flash Linux to a memory device
- Connect the hardware
- Install and configure Linux
- Install and use mycroft-tools
- Test microphone and speakers
- Install and configure Minimy
- Start Minimy and use it!

This document  is based on *The smart boombox cookbook* which has more details on the construction of the enclosure and a parts list. 
See: https://github.com/mike99mac/mycroft-tools/blob/master/smartBoombox.pdf 

## Acquire the hardware
The recommended hardware is a Raspberry Pi (RasPi) 4B with 4 or 8 GB of memory.  Yes, they're still hard to get, but not impossible. 

A Rasberry Pi 400 is another option.  It allows the CPU to be *offboard* which frees up space onboard to house lithium-ion batteries.

Hopefully the RasPi 5 will be out soon and will be more powerful and easier to procure.

For a microphone, a flat, disk type with a mute/unmute switch for visible privacy is recommended.  Don't use a cheap one.
It is best to move the microphone away from the speakers and closer to the center of the room.

You can start with just about any speaker(s) with a 3.5mm jack that will plug into the RasPi.  We could talk about DAC HATs and audio quality, but that's outside the scope of this document.

## Flash Linux to a memory device
The RasPi boots from a micro-SD card that plugs into its underside. A 32 GB card or larger is recommended. You need to *prime the pump* and copy a Linux distribution to it. 

You will need another computer running Linux or another OS to copy the Linux image to the memory card.

### Prepare on Linux

If you have a Linux box with an SD card port, you can use **``rpi-imager``** to copy the Linux image. To do so, perform the following tasks.
- Put a micro-SD card into an SD adapter.
- Plug the SD adapter into the card reader.
- If you don't have it already, install the tool.

    **``$ sudo apt-get install -y rpi-imager``**

- Run the tool.

    **``$ rpi-imager``**
    
    You should see a window as shown in the following figure. **TODO**: add a screenshot

- To flash a Linux image to the card, perform the following steps:

    - Select your preferred *Operating System*. **Ubuntu Desktop 22.04 LTS** is recommended. It's a solid operating system, that combined with the RasPi, is capable of being a general purpose computer. LTS stands for *Long Term Support* - Canonical promises to support it for at least five years. 

    - Select the *Storage* device. You should see just one micro-SD card in the dropdown menu.

    - Click **Write**.

    - Enter the password of the current user.

You should see a progress indicator as the image is copied to the SD card. It should take around 5 minutes.

### Prepare an SD card on Windows
If you only have access to a Windows system Install the *Win 32 disk imager* from https://sourceforge.net/projects/win32diskimager/

No further details are provided.

## Connect the hardware

For the initial setup, a keyboard, monitor and mouse are needed. You can access the Internet using either Wi-Fi or with an Ethernet cable.

To connect all the computer hardware, perform the following steps:

- Plug the micro-SD card into the back underside of the RasPi.
- If you have wired ethernet, plug it in to the RJ-45 connector on the RasPi.
- Connect the mouse and keyboard to the USB slots.
- Connect the monitor to the RasPi with an appropriate micro-HDMI cable.  The RasPi 4 two micro HDMI ports - use the left one.
- If you have a USB drive with music files on it, plug it in to a USB slot.
- Now that all the other hardware is connected, plug the 5v power supply with a USB-C end into the RasPi 4. An official RasPi power supply is recommended to avoid *undervoltage* warnings.  If you have an inline switch, turn it on.

## Install and configure Linux

To install and configure Ubuntu Desktop Linux, perform the following sections.

- Boot the RasPi
- Initial Ubuntu Desktop configuration
- Install the SSH server
- Start a terminal or SSH session
- Update and upgrade your system

### Boot the RasPi

When you supply power to the RasPi, it should start booting.  On the top, back, left side of the RasPi there are two LEDs:

- The LED to the left should glow solid red. This signifies it has 5V DC power.
- The LED to the right should flicker green. This signifies that there is communicaiton with the CPU. If there is a red light, but no green one, it's likely the micro-SD card does not have Linux properly installed.
- You should see a rainbow colored splash screen on the monitor, then the Ubuntu desktop should initialize.

**IMPORTANT**: Never turn the RasPi off without first shutting Linux down with the **``halt``** or similar command. Doing so can damage the operating system and possibly even the RasPi itself.

### Initial Ubuntu Desktop configuration

A welcome screen should open on the monitor. Perform the following steps:

- On the *Welcome* window, choose your language and click **Continue**.
- On the *Keyboard layout* window, choose your layout and click **Continue**.
- On the *Wireless* window, if you are not using a hard-wired Ethernet, click **Connect** and configure a Wi-Fi network. You must know the network SSID and will probably be prompted for a password.
- On the *Where are you?* window, choose your time zone.
- On the *Who are you?* window, set the following values:
    - Set your name.
    - Set your computer’s name (host name).
    - For a user name and password ``pi`` is recommended as it is documented in the reminder of this document.
    - For the last option, **Log in automatically** is recommended.
    - Click **Continue**.
 - The install process will take a number of minutes configuring and will reboot the computer.

    ``TAKE A BREAK?  In a test, this step took 5 minutes.``
    
 - When the system finishes rebooting, an *Online Accounts* window should appear. Click **Skip**.
 - Click **Next** at the *Enable Ubuntu Pro* window.
 - Choose an option on the *Help Improve Ubuntu* window and click **Next**.
 - Click **Next** at the *Privacy* window.
 - Click **Done** at the *Ready to go* window.

Ubuntu Desktop 22.04 should now be installed
 
### Install the SSH server

The secure shell (SSH) server is not installed by default on Ubuntu desktop. Install it so you can access your system remotely. To do so, perform the following steps:

- Open a terminal session by right-clicking the mouse anywhere on the desktop and choosing **Open in Terminal**. You should see a console window open.
- Show the contents of the ``/etc/os-release`` file just to confirm the Ubuntu release level.

    **``$ cat /etc/os-release``**
    
    ```
    PRETTY_NAME="Ubuntu 22.04.2 LTS"
    NAME="Ubuntu"
    VERSION_ID="22.04"
    VERSION="22.04.2 LTS (Jammy Jellyfish)"
    ...
    ```
    
- Install the ``openssh-server`` package, with the following command.  You will be prompted for your password.
    
    **``$ sudo apt-get install -y openssh-server ``**
    
    ``[sudo] password for pi:``

- After it installs **``sshd``** should be running. Verify with the following command:

    **``$ service sshd status``**
    
    ```
    ...
    Active: active (running) 
    ...
    ```
    
- You should have either a Wi-Fi (``wlan0``) or a hard-wired (``eth0``) connection. To verify, enter the following command. Note your IP address.

    **``ip a``**
    ```
    1: lo:
    ...
    2: eth0:
    ...
    3: wlan0:
    ...
    inet 192.168.1.229
    ```
    
### Start a terminal or SSH session

You can continue to work from a *terminal session*.  Right click anywhere on the desktop wallpaper and choose **Open in Terminal**.  A console window should appear.

You can also start an SSH session as the user ``pi``, if you want to continue from another system. You can use **putty** to SSH in from a Windows box, or just use the **``ssh``** command from a Linux or macOS console.

**IMPORTANT**: Do not run as ``root``. Doing so will almost certainly screw up your system.  It is recommended that you run as the user ``pi``.  Ideally, other user names should work, as the environment variable ``$HOME`` is used in scripts, but this has never been tested.

### Update and upgrade your system

Update and upgrade your system which installs the latest code for all installed packages.

- Enter the following command to prepare for the upgrade.  You will be prompted for your password.

    **``$ sudo apt-get update``**
    
- Upgrade your system so you have all the latest code. This step could take up to 25 minutes.

    **``$ sudo apt-get upgrade -y``**
    
    ``TAKE A BREAK?  In a test, this step took 19 minutes.``
    
Your system should now be at the latest software level.

## Install and use mycroft-tools

The **``mycroft-tools``** repo has been developed to help with the installation, configuration, use and testing of the free and open personal voice assistants.

To install **``mycroft-tools``** perform the following steps:
  
- Install **``git``** and **``vim``** as they are needed shortly.

    **``$ sudo apt-get install -y git vim``**
    
    **``...``**
    
- Make **``vim``** the default editor.

    **``$ sudo update-alternatives --install /usr/bin/editor editor /usr/bin/vim 100``**
    
    ``update-alternatives: using /usr/bin/vim to provide /usr/bin/editor (editor) in auto mode``
    
- Allow members of the ``sudo`` group to be able to run **``sudo``** commands without a password, by adding **``NOPASSWD:``** to the line near the bottom of the file.

    **``$ sudo visudo``**

    ```
    ...
    %sudo   ALL=(ALL:ALL) NOPASSWD: ALL
    ...
    ```

- Clone the **``mycroft-tools``** package in the ``pi`` home directory with the following commands:

    **``$ cd``**
    
    **``$ git clone https://github.com/mike99mac/mycroft-tools.git``**
    
    ```
    Cloning into 'mycroft-tools'...
    ...
    Resolving deltas: 100% (366/366), done.
    ```
    
- Change to the newly installed directory and run the setup script. It will copy scripts to the directory ``/usr/local/sbin`` which is in the default ``PATH``.

    **``$ cd mycroft-tools``**
    
    **``$ sudo ./setup.sh``**
    
    ```
    Copying all scripts to /usr/local/sbin ... 
    Success!  There are new scripts in your /usr/local/sbin/ directory
    ```
    
    The **``mycroft-tools``** repo is now installed.
    
### Further customize 

The script **``install1``**, in the **``mycroft-tools``** package you just installed, runs many commands and thus save typing, time and possible errors.

It performs the following tasks:

- Installs the **``mlocate mpc mpd net-tools pandoc python3 python3-pip python3-rpi.gpio python3.10-venv``** packages
- Sets  **``vim``** to a better color scheme and turns off the annoying auto-indent features
- Adds needed groups to users ``pi`` and ``mpd``
- Copies a ``.bash_profile`` to the user's home directory
- Turns ``default`` and ``vc4`` audio off and does not disable monitor overscan in the Linux boot parameters file.
- Changes a line in the **``rsyslog``** configuration file to prevent *kernel message floods*
- Copies a **``systemctl``** configuration file to mount ``/var/log/`` in a ``tmpfs`` which helps prolong the life of the micro-SD card
- Sets **``pulseaudio``** to start as a system service at boot time, and allows anonymous access so audio services work
- Configures **``mpd``**, the music player daemon, which plays most of the sound
- Turns off **``bluetooth``** as Linux makes connecting to it ridiculously hard, while most amplifiers make it easy

To run **``intall1``**, perform the following steps:

- First verify it is in your ``PATH`` with the **``which``** command.

    **``$ which install1``**
    
    ``/usr/local/sbin/install1``

- Run the **``install1``** script in the home directory and send ``stdout`` and ``stderr`` to a file.  You may want to reference that file in case of errors.

    **``$ cd``**
    
    **``$ install1 2>&1 | tee install1.out``**
    
    ``...``
    
    ``TAKE A BREAK?  In a test, this step took 3 minutes.``
    
### Test the changes

- Test your environment with the newly installed **``lsenv``** script which reports on many aspects of your Linux system.

    **``$ lsenv``**
    
    ```
    Status of minimy:
     -) WARNING: minimy is not running as a service ... checking for processes ...
        WARNING: minimy does not appear to be running
    ---------------------------------------------------------------------------------
    Status of mpd:
     -) WARNING: mpd is not running as a service ... checking for processes ...
        WARNING: mpd does not appear to be running
    ---------------------------------------------------------------------------------
    Status of pulseaudio:
     -) WARNING: pulseaudio is not running as a service ... checking for processes ...
        Found matching pulseaudio processes:
        pi         34471   34454  0 09:44 ?        00:00:01 /usr/bin/pulseaudio --daemonize=no --log-target=journal
    ---------------------------------------------------------------------------------
         IP address : 192.168.1.148
    CPU temperature : 55C / 131F
      Root fs usage : 14%
          CPU usage : 0%
    Memory usage    :
                     total        used        free      shared  buff/cache   available
      Mem:           3.7Gi       698Mi       268Mi       120Mi       2.8Gi       2.7Gi
      Swap:          1.0Gi        11Mi       1.0Gi
    tmpfs filesystem?
                          /var/log       Linux logs : no
              /home/pi/minimy/logs      Minimy logs : no
               /home/pi/minimy/tmp  Minimy temp dir : no
    ```
    
The output shows that:

- Processes with ``minimy`` in their name are not running.
- The Music Playing Daemon, **``mpd``** is not running.
- There is one **``pulseaudio``** process running, but it does not have **``--system``** as a parameter.
- Useful information such as IP address, the CPU temperature, root file system, CPU and memory usage.
- None of the file systems frequently written to are mounted over an in-memory ``tmpfs`` file system.

### Test changes of install1 script
Some of the changes made by **``install1``** will not be realized until boot time. To test this, perform the following steps:

- Reboot your system

    **``$ sudo reboot``**
    
- Restart your SSH session when it comes back up.
- Run the same script again to see how the environment has changed.

    **``$ lsenv``**
    
    ````
    Status of minimy:
     -) WARNING: minimy is not running as a service ... checking for processes ...
        WARNING: minimy does not appear to be running
    ---------------------------------------------------------------------------------
    Status of mpd:
     -) mpd is running as a service:
        Active: active (running) since Sat 2023-06-10 10:13:24 EDT; 56s ago
    ---------------------------------------------------------------------------------
    Status of pulseaudio:
     -) pulseaudio is running as a service:
        Active: active (running) since Sat 2023-06-10 10:13:22 EDT; 58s ago
        pulseaudio processes:
        pulse        850       1  0 10:13 ?        00:00:00 /usr/bin/pulseaudio --system --disallow-exit --disallow-module-loading --disable-shm --exit-idle-time=-1
    ---------------------------------------------------------------------------------
         IP address : 192.168.1.148
    CPU temperature : 63C / 145F
      Root fs usage : 14%
          CPU usage : 91%
    Memory usage    :
                     total        used        free      shared  buff/cache   available
      Mem:           3.7Gi       707Mi       2.3Gi        13Mi       685Mi       2.8Gi
      Swap:          1.0Gi          0B       1.0Gi
    tmpfs filesystem?
                          /var/log       Linux logs : yes
              /home/pi/minimy/logs      Minimy logs : no
               /home/pi/minimy/tmp  Minimy temp dir : no

    ````
    
You should see three changes:

- The Music Playing Daemon, **``mpd``** is now running.
- The one **``pulseaudio``** process shows a **``--system``** parameter which is vital to audio output working correctly.
- An in-memory ``tmpfs`` file system is now mounted over the **``/var/log/``** directory.

## Test microphone and speakers

It is important to know your microphone and speakers are working. 
There are scripts in *mycroft-tools* named **``testrecord``** and **``testplay``**. 
They are wrappers around the **``arecord``** and **``aplay``** commands designed to make it easier to test recording audio to a file and playing it back on the speaker(s).

- To test your microphone and speakers, issue the following command then speak for up to five seconds. 

    **``$ testrecord``**
    
    ```
    Testing your microphone for 5 seconds - SAY SOMETHING!
    INFO: running command: arecord -r 44100  -f S24_LE -d 5 /tmp/test-mic.wav
    Recording WAVE '/tmp/test-mic.wav' : Signed 24 bit Little Endian, Rate 44100 Hz, Mono
    Calling testplay to play back the recording ...
    Playing WAVE '/tmp/test-mic.wav' : Signed 24 bit Little Endian, Rate 44100 Hz, Mono
    ```
    
You should hear your words played back to you. If you do not, you must debug the issues - there's no sense in going forward without a microphone and speakers.

At this point your system should have a solid sound and microphone stack running, especially **``mpd``** and **``pulseaudio``**, and all software necessary for the installation of Minimy.

## Install and configure Minimy

In this section you will perform the following steps:
- Download and copy Minimy
- Install Minimy
- Configure Minimy
- Get a Google API key

### Download and copy Minimy 
It is recommended that you make a second copy of Minimy after you download it.  This way, if you make some changes to the running code, you'll have a reference copy. Also the copy of the code that you run should not have a ``.git/`` directory, thus removing any connection to github.

The new directory ***must*** be named ``minimy``, removing the ``-mike99mac`` suffix.  Otherwise things will break.

To download and copy Minimy, perform the following steps:

- Change to your home directory and clone the repo from github.

    **``$ cd``**
    
    **``$ git clone https://github.com/mike99mac/minimy-mike99mac``**

    ```
    Cloning into 'minimy-mike99mac'...
    ...
    Resolving deltas: 100% (450/450), done.
    ```
    
- Copy the directory recursively from ``minimy-mike99mac`` to ``minimy``.

    **``$ cp -a minimy-mike99mac minimy``**
    
- Remove the ``.git`` directory from the copy.

    **``$ cd minimy``**
    
    **``$ rm -fr .git``**
    
    Now the code will run and you can work in ``minimy`` and keep ``minimy-mike99mac`` as a reference copy.
    
### Install Minimy    
    
- Run the following script to install Minimy and direct ``stdout`` and ``stderr`` to a file.
    
    **``$ ./install/linux_install.sh 2>&1 | tee linux_install.out``**
    
    ```
    ...
    Install Complete
    ```
    
    ``TAKE A BREAK?  In a test, this step took 13 minutes.``
    
    It is recommended that you review the output file, checking for warnings or errors.
    
- Confirm that **``venv``** is an alias which should have been set in your ``.bash_profile`` after the reboot.

    **``alias venv``**
    
    ``alias venv='source /home/pi/minimy/venv_ngv/bin/activate'``
    
- Open a virtual environment.

    **``$ venv``**
    
    You should notice a new ``(venv_ngv)`` prefix on the command line.
    
### Configure Minimy

The system can use local or remote services for speech to text (STT), text to speech (TTS)
and intent matching. Intent matching is accomplished using natutal language processing (NLP) based on
the CMU link parser using a simpe enumerated approach referred to as shallow parsing.

As a result you will be asked during configuration if you would like to use remote or local STT, TTS
and NLP. Unless you have a good reason, for now you should always select local mode (``remote=n``) for NLP.

Remote TTS using polly requires an Amazon ID and key.  If you prefer to not use polly for remote TTS you may 
choose mimic2 from Mycroft which is a free remote TTS alternative. You could also select local only TTS in 
which case mimic3 should work fine.

By deault the system will fallback to local mode if a remote service fails. This will happen
automatically and result in a slower overall response. If the internet is going to be out
often you should probably just select local mode.  The differences are that remote STT is more accurate
and remote TTS sounds better. Both are slower but only slightly when given a reasonable internet
connection. Devices with decent connectivity should use remote for both.

You will also be asked for operating environment.  Currently the options are (p) for piOS, (l) for 
Ubuntu or (m) for the Mycroft MarkII.

During configuration you will be asked to provide one or more words to act as wake words. You will
enter them separated by commas with no punctuation.  For example, 
```
hey Bubba, bubba
```
or
```
computer
```

Wake words work best when you choose multi-syllable words. Longer names like 'Esmerelda' or  words like
'computer' or words with distinct sounds like 'expression' (the 'x') or 'kamakazi' (two hard
'k's) will always work better than words like 'hey' or 'Joe'. You can use the ``test_recognition.sh`` 
script to see how well your recognition is working.  Just using the word 'computer' should work adequately.

You will also be asked to provide an input device index. If you do not know what this means enter the
value 0. If you would like to see your options you can run 'python framework/tests/list_input_devices.py'.
Remember, if you do not source your virtual environment first, things will not go well for you. 

Always source the virtual environment before you run anything. 

The ``SVA_BASE_DIR`` and ``PYTHONPATH`` environment variables should set properly in your ``~/.bash_profile``.

- Run the following configuration script. In this example all defaults were accepted by pressing **Enter** for each question (except the log level was set to debug). At the end **y** was entered to save the changes.  
 
    **``(venv_ngv) $ ./mmconfig.py sa``**
    
    ```
    Advanced Options Selected sa
    ... all defaults taken except debug level ...
    Save Changes?y
    Configuration Updated
      Advanced
        ('CrappyAEC', 'n')
        ('InputDeviceId', '0')
        ('InputLevelControlName', 'Mic')
        ('LogLevel', 'd')
        ('NLP', {'UseRemote': 'n'})
        ('OutputDeviceName', '')
        ('OutputLevelControlName', 'Speaker')
        ('Platform', 'ubuntu')
        ('STT', {'UseRemote': 'y'})
        ('TTS', {'Local': 'm', 'Remote': 'p', 'UseRemote': 'y'})
      Basic
        ('AWSId', '')
        ('AWSKey', '')
        ('BaseDir', '/home/pi/minimy')
        ('GoogleApiKeyPath', 'install/my_google_key.json')
        ('Version', '1.0.4')
        ('WakeWords', ['hey computer', 'computer'])
    ```

### Get a Google API key

You need a Google Speech API key in order to be able to convert speech to text.  A template file is in the ``install/`` directory.

An alternative is to use a different STT engine, but that has not been tested.

To get a Google API key file, perform the following steps:

- Change to the install directory.

    **``cd /home/pi/minimy/install``**
    
- Copy the GPG key template file to the file that will be populated.

    **``cp my-google-key.json.template my-google-key.json``**

- Show the file.

    **``# cat my-google-key.json``**
    
    ```
    (venv_ngv) pi@johnsbox:~/minimy-mike99mac$ cat my-google-key.json.template
    {
      "type": "service_account",
      "project_id": "PROJECT_ID",
      "private_key_id": "KEY_ID",
      "private_key": "-----BEGIN PRIVATE KEY-----\nPRIVATE_KEY\n-----END PRIVATE KEY-----\n",
      "client_email": "SERVICE_ACCOUNT_EMAIL",
      "client_id": "CLIENT_ID",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://accounts.google.com/o/oauth2/token",
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
      "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/SERVICE_ACCOUNT_EMAIL"
    }
    ```

- You will need to obtain your own ``PROJECT_ID``, ``KEY_ID``, ``PRIVATE_KEY``, ``SERVICE_ACCOUNT_EMAIL`` and ``CLIENT_ID``. 
- Go to https://console.cloud.google.com/freetrial/signup/tos and obtain these values.
- Populate them in the file.

## Run Minimy
The scripts **``startminimy``** and **``stopminimy``** are used to start and stop processes. 
Each skill and service run as process and use the message bus or file system to synchronize. 
Their output is written to the ``logs/`` directory under the main install directory. 

The system relies on the environment variables ``PYTHONPATH, SVA_BASE_DIR`` and ``GOOGLE_APPLICATION_CREDENTIALS`` which are set in **``startminimy``** 
with this code:

    ...
    export PYTHONPATH="$HOME/minimy:$HOME/minimy/venv_ngv/lib/python3.10/site-packages"
    export SVA_BASE_DIR="$HOME/minimy"
    export GOOGLE_APPLICATION_CREDENTIALS="$HOME/minimy/install/my-google-key.json"
    ...

- Start Minimy, ensuring it is run from the base directory, as follows.

    **``(venv_ngv) $ cd $HOME/minimy``**
    
    **``(venv_ngv) $ ./startminimy``**

- Stop Minimy with:

    **``(venv_ngv) $ ./stopminimy``**
    
- Run **``lsenv``** again to see how your environment has changed.    

    **``lsenv``**

    ```
    Status of minimy:
     -) WARNING: minimy is not running as a service ... checking for processes ...
        Minimy user skills: connectivity email example1 help mpc timedate weather wiki
             System skills: buttons intent media_player mic skill_alarm skill_fallback skill_media skill_volume stt tts
    ---------------------------------------------------------------------------------
    Status of mpd:
     -) mpd is running as a service:
        Active: active (running) since Sat 2023-06-10 10:13:24 EDT; 2h 3min ago
    ---------------------------------------------------------------------------------
    Status of pulseaudio:
     -) pulseaudio is running as a service:
        Active: active (running) since Sat 2023-06-10 10:13:22 EDT; 2h 3min ago
        pulseaudio processes:
        pulse        850       1  2 10:13 ?        00:03:35 /usr/bin/pulseaudio --system --disallow-exit --disallow-module-loading --disable-shm --exit-idle-time=-1
    ---------------------------------------------------------------------------------
         IP address : 192.168.1.148
    CPU temperature : 72C / 161F
      Root fs usage : 18%
          CPU usage : 58%
    Memory usage    :
                     total        used        free      shared  buff/cache   available
      Mem:           3.7Gi       1.8Gi       224Mi        44Mi       1.7Gi       1.7Gi
      Swap:          1.0Gi       4.0Mi       1.0Gi
    tmpfs filesystem?
                          /var/log       Linux logs : yes
              /home/pi/minimy/logs      Minimy logs : yes
               /home/pi/minimy/tmp  Minimy temp dir : yes
    ```
You should see two changes:

- Minimy is now running - the output showing the user and system skill processes.
- The two minimy file systems frequently written to are now mounted over in-memory ``tmpfs``'s.



## The buttons process

The smart boombox model with the RasPi on-board has three pushbuttons on the front panel to allow quick access to *previous track*, *pause/resume*, and *next track* operations.  A new **``buttons``** system skill traps button presses and sends corresponding messages to the bus.

If you want to add buttons to your enclosure, attach them to the following GPIO pins:

    +-----+--------+-------------------------------+
    | Pin | Label  | Description                   |
    |-----|--------|-------------------------------|
    | 9   | GND    | Ground common to all buttons  |
    | 11  | GPIO17 | Previous track                |
    | 13  | GPIO27 | Pause/resume                  |
    | 15  | GPIO22 | Next track                    |
    +-----+--------+-------------------------------+

The ``buttons.py`` code is here: https://github.com/mike99mac/minimy-mike99mac/blob/main/framework/services/input/buttons.py
    
One source of purchasing pushbuttons is here: https://www.amazon.com/dp/B09C8C53DM  

**TODO:** On another model, the computer is a RaspPi 400 which is *offboard*. This allows Lithium-ion batteries to be *onboard*. That will need new code that uses the arrow keys on the RasPi 400 for the same function.

# Debugging
Maybe everything will work perfectly the first time, and you won't have to debug.  But we know how that goes :))

Many, many debug statements have been added to the code.  In the critical classes, almost every function has at least one log statement when in debug mode. 

Following are some debugging resources.
- Log files are in ``$HOME/minimy/logs``.  
    - Show the log files.
   
        **``$ cd $HOME/minimy/logs``**
        
        **``$ ls``**
        
        ``intent.log  media_player.log  skills.log  stt.log  tts.log``
   
    - When Minimy is running, you can watch all the log files get populated in real time.

        **``tail -f *``**
        
- There is an HTML file with JavaScript code that displays the message bus in real time. If you do not have a Web server running, you must view it from the local host. Start a browser on the box you're installing on and point it to: ``file:///home/pi/minimy/display/sysmon.html``. You should see all messages written to the message bus and the associated data.
    - **TODO:** get a screen shot
- Google searches, of course ...
- You can email me at mike99mac at gmail.com - can't promise anything, but I will try.


# Reference
These reference sections follow:
- Vocabulary and examples
- Other Documentation

## Vocabulary and examples

In the samples that follow (words) in parenthesis are the actual words spoken, while {words} in curly brackets become variables populated with the actual words spoken. When (multiple|words|) are separated by vertical bars any of those can be spoken, and a trailing vertical bar means that word can be omitted.

**``TODO``** Finish all vocabs and examples

### Connectivity skill

**TODO:** Finish writing this skill.

Following is the Connectivity skill vocabulary.
 
Following are examples of Connectivity skill requests:

 
### Email skill

Following is the Email skill vocabulary.

```
(compose|create|new|start) email
send email
```

Following are examples of Email skill requests:

- **``start email``**
- ... dialog continues ...
- **``send email``**
 
### Example1 skill

Following is the Example1 skill vocabulary.

``(run|test|execute) example one``
 
Following are examples of Example1 skill requests:
 
- **``run exmple one``**
 
### Help skill

**TODO:** Finish the code for this skill!

Following is the Help skill vocabulary.

Following are examples of Help skill requests:
 
### MPC skill

The MPC skill can:

- Play from your music library
- Play Internet radio stations
- Play Internet music
- Play NPR news
- Create, delete, manage and play playlists (**TODO:** finish this code)
- Perform basic player operations 

Following are the vocabularies for the MPC skill:

- Music library vocabulary
    ```
    play (track|song|title|) {track} by (artist|band|) {artist}
    play (album|record) {album} by (artist|band) {artist}
    play (any|all|my|random|some|) music 
    play (playlist) {playlist}
    play (genre|johnra) {genre}    
    ```

- Internet radio vocabulary

    ```
    play (the|) radio
    play music (on the|on my|) radio
    play genre {genre} (on the|on my|) radio
    play station {station} (on the|on my|) radio
    play (the|) (radio|) station {station}
    play (the|) radio (from|from country|from the country) {country}
    play (the|) radio (spoken|) (in|in language|in the language) {language}
    play (another|a different|next) (radio|) station
    (different|next) (radio|) station
    ```  
    
- Internet music vocabulary

    ```
    play (track|artist|album|) {music} (from|on) (the|) internet
    ```
    
- News vocabulary    

    ```
    play (NPR|the|) news
    ```
    
- Playlist vocabulary (**NOTE:** code is not complete yet)

    ```
    (create|make) playlist {playlist} from track {track}
    (delete|remove) playlist {playlist}
    add (track|song|title) {track} to playlist {playlist}
    add (album|record) {album} to playlist {playlist}
    (remove|delete) (track|song|title) {track} from playlist {playlist}
    (remove|delete) (album|record) {album} from playlist {playlist}
    list (my|) playlists
    what playlists (do i have|are there)
    what are (my|the) playlists
    ```  
    
- Basic player commands vocabulary (**NOTE:** code is not complete yet)

    ```
    previous (song|station|title|track|)
    next (song|station|title|track|)
    pause                               # stop music but maintain queue
    resume
    stop                                # stop music and clear queue
    
    increase volume
    decrease volume
    ```

Following are examples of MPC skill's requests:
- Play track 

### Timedate skill

Following is the Timedate skill vocabulary.

```
what time (is it|)
what (is|) (today's|) date
what day (of the week|) (is it|)
```

Following are examples of  skill's requests:

- What time is it?
- What is today's date
- What day of the week is it
 
### Weather skill

Following is the Weather skill vocabulary.
 
Following are examples of Weather skill requests:

### Wiki skill

The Wiki skill is a fallback skill. As such it does not have a vocabulary

**TODO:** Add ``Ask wikipedia {question}``

## More documentation

There is more documentation, by the original author Ken Smith, here: https://github.com/ken-mycroft/minimy/tree/main/doc

## Afterthought

One of my mantras is *Less is more*. I like minimy because it is a **Mini-My**croft. Here is a rough estimate of the lines of Python code in the three projects as of May 2023:
```
            Repo         Loc           files
    mycroft-core       38074             229
       ovos-core       18067             238
minimy-mike99mac        9900              79
```
So OVOS is half the size of Mycroft, and Minimy is about half again smaller.
