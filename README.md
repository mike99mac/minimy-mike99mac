# Minimy

Minimy is a simple NLU-based voice assistant framework.

It is a fork of Ken-Mycroft's code at: https://github.com/ken-mycroft/minimy

## Overview
**From Ken Smith, who is the original author:**

"The goal of this project is to provide a run-time environment which facilitates the development of 
voice enabled applications. These voice enabled applications take the form of a 'skill' and are
simply python programs which may do normal python things as well as call speak() and listen() and
get called asynchronously when an utterance is matched to an intent the skill has previously registered."  

**From Mike Mac, who is working on this fork of the code:**

I worked with the Mycroft free and open personal voice assistant since 2019, but the company went bankrupt in 2023, so had to move on. :((

I tried OVOS but was not able to get a music skill working after a couple weeks.  I still haven't given up on that platform - no doubt it will only get better and easier to install.

Then I found Minimy, and was able to get it running in a few hours. Apparently, it was a project that hoped to save Mycroft from the fire but wasn't well received. Thankfully, Ken Smith put it on github, I forked the code, and here we are.  Ken has been a great help in answering my many questions - **Thanks Dude!** 

So I continue to try to *give back to the community* while *standing on the shoulders* of so many thousands of others.

This document focuses on how to get the entire *software stack* running, and starts from the very beginning.

## Overview of build process

The test environment is a RasPi 4B with 4 GB of memory, running Ubuntu Desktop 22-04 inside a *boombox*. However, this code and these steps should be portable to any hardware that can run Linux, and probably just about any distro, in any type of *enclosure* you fancy.  But if you try it on different hardware, or a different distro, expect the unexpected :))

The overall steps to build a *Smart Boombox* are:

- Acquire the hardware - a minimum of a RasPi, a microphone and a speaker
- Flash a Linux image to a memory device
- Install and configure Linux
- Install a toolbox written for Minimy
- Install and customize Minimy
- Start using your new music machine and personal voice assistant!

Ideally Minimy would run on a Mycroft Mark II, however there is no code supporting the monitor, SJ-201 and associated hardware.

This document  is based on *The smart boombox cookbook* which also has some details on the construction of an enclosure that looks like a *boombox*. 

It is here: https://github.com/mike99mac/mycroft-tools/blob/master/smartBoombox.pdf 

## Acquire the hardware
The minimum recommended hardware is a Raspberry Pi (RasPi) 4B with at least 4 GB of memory.  Yes, they're still hard to get, but not impossible. 

A Rasberry Pi 400, also with at least 4GB, is another option.  On the boombox enclousres, having the CPU offboard frees up space to house lithium-ion batteries.

Hopefully the RasPi 5 is coming soon and will be more powerful and easy to procure.

Don't buy a cheap USB microphone. The sweet spot might be around $25 for flat disk type with a mute/unmute switch for visible privacy. 
It is best to move the microphone away from the speakers and closer to the center of the room.

You can start with just about any speaker(s) with a 3.5mm jack that will plug into the RasPi.  We could talk about DAC HATs and audio quality, but that's outside the scope of this document.

## Prepare an SD card to boot Linux
The RasPi boots from a micro-SD card that plugs into its underside. A 32 GB card or larger is recommended. You need to *prime the pump* and copy a Linux distribution to it. 

Hopefully you have another computer running Linux, but other OS's will work. It must have a hardware port to write to the card.

### Prepare on Linux

If you have a Linux box with an SD card reader, you can use **``rpi-imager``** to copy the Linux image. To do so, perform the following tasks.
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

You should see a progress indicator as the image is copied to the SD card. It should take around five minutes.

### Prepare an SD card on Windows
If you only have access to a Windows system Install the *Win 32 disk imager* from https://sourceforge.net/projects/win32diskimager/

No further details are provided.

## Connect the computer hardware

For the initial setup, a keyboard, monitor and mouse are needed. You can access the Internet using either Wi-Fi or with an Ethernet cable.

To connect all the computer hardware, perform the following steps:

- Plug the micro-SD card into the back underside of the RasPi.
- If you have wired ethernet, plug it in to the RJ-45 connector on the RasPi.
- Connect the mouse and keyboard to the USB connections on the RasPi.
- Connect the monitor to the RasPi with an appropriate micro-HDMI cable.  The RasPi 4 two micro HDMI ports - use the left one.
- Now that all the other hardware is connected, plug the 5v power supply with a USB-C end into the RasPi 4. An official RasPi power supply is recommended to avoid *undervoltage* warnings.  If you have an inline switch, turn it on.

### Boot the RasPi

When you supply power to the RasPi, it should start booting.  On the top, back, left side of the RasPi there are two LEDs:

- The LED to the left should glow solid red. This signifies it has 5V DC power.
- The LED to the right should flicker green. This signifies that there is communicaiton with the CPU. If there is a red light, but no green one, it's likely the micro-SD card does not have Linux properly installed.
- You should see a rainbow colored splash screen on the monitor, then the Ubuntu desktop should initialize.

**IMPORTANT**: Never turn the RasPi off without first shutting Linux down with the **``halt``** or similar command. Doing so can damage the operating system and possibly even the RasPi itself.

## Install and configure Linux

To configure Ubuntu Desktop, perform the following sections.

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
 - When the system finishes rebooting, an *Online Accounts* window should appear. Click **Skip**.
 - Click **Next** at the *Enable Ubuntu Pro* window.
 - Choose an option on the *Help Improve Ubuntu* window and click **Next**.
 - Click **Next** at the *Privacy* window.
 - Click **Done** at the *Ready to go* window.

Ubuntu Desktop 22-04 should now be installed
 
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
    
Your system should now be at the latest software level.

### Install Mycroft tools

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
    
### Test the changes

- Test your environment with the newly installed **``lsenv``** script which reports on many aspects of your Linux system.

    **``$ lsenv``**
    
    ```
    Status of minimy:
     -) WARNING: minimy is not running as a service ... checking for processes ...
        WARNING: no processes matching minimy - does not appear to be running ...
    ---------------------------------------------------------------------------------
    Status of buttons:
     -) WARNING: buttons is not running as a service ... checking for processes ...
        WARNING: no processes matching buttons - does not appear to be running ...
    ---------------------------------------------------------------------------------
    Status of mpd:
     -) WARNING: mpd is not running as a service ... checking for processes ...
        WARNING: no processes matching mpd - does not appear to be running ...
    ---------------------------------------------------------------------------------
    Status of pulseaudio:
     -) WARNING: pulseaudio is not running as a service ... checking for processes ...
        Found matching pulseaudio processes:
        pi         34786   34768  0 09:00 ?        00:00:14 /usr/bin/pulseaudio --daemonize=no --log-target=journal
    ---------------------------------------------------------------------------------
         IP address : 192.168.1.148
    CPU temperature : 50C / 122F
      Root fs usage : 14%
          CPU usage : 6%
    Memory usage    :
                     total        used        free      shared  buff/cache   available
      Mem:           3.7Gi       1.5Gi       220Mi       156Mi       2.0Gi       1.9Gi
      Swap:          1.0Gi       166Mi       857Mi
    tmpfs filesystem?
                          /var/log       Linux logs : no
              /home/pi/minimy/logs      Minimy logs : no
               /home/pi/minimy/tmp  Minimy temp dir : no
    ```
The output shows that:

- Processes with ``minimy`` in their name are not running.
- The **``buttons``** daemon, which traps and sends messages when physical buttons are pushed, is not running.
- The Music Playing Daemon, **``mpd``** is not running.
- There is one **``pulseaudio``** process running, but it does not have **``--system``** as a parameter.
- Useful information such as IP address, the CPU temperature, root file system, CPU and memory usage.
- None of three file systems frequently written to is mounted over an in-memory ``tmpfs`` file systems.

### Test changes of install1 script
Some of the changes made by **``install1``** will not be realized until boot time. To test this, perform the following steps:

- Reboot your system

    **``$ sudo reboot``**
    
- Restart your SSH session.
- Run the same script again.

    **``$ lsenv``**
    
    ````
    Status of minimy:
     -) WARNING: minimy is not running as a service ... checking for processes ...
        WARNING: no processes matching minimy - does not appear to be running ...
    ---------------------------------------------------------------------------------
    Status of buttons:
     -) WARNING: buttons is not running as a service ... checking for processes ...
        WARNING: no processes matching buttons - does not appear to be running ...
    ---------------------------------------------------------------------------------
    Status of mpd:
     -) mpd is running as a service:
        Active: active (running) since Fri 2023-05-26 12:08:04 EDT; 1min 46s ago
    ---------------------------------------------------------------------------------
    Status of pulseaudio:
     -) pulseaudio is running as a service:
        Active: active (running) since Fri 2023-05-26 12:08:02 EDT; 1min 48s ago
        pulseaudio processes:
        pulse        842       1  0 12:08 ?        00:00:00 /usr/bin/pulseaudio --system --disallow-exit --disallow-module-loading --disable-shm --exit-idle-time=-1
    ---------------------------------------------------------------------------------
         IP address : 192.168.1.148
    CPU temperature : 55C / 131F
      Root fs usage : 14%
          CPU usage : 0%
    Memory usage    :
                     total        used        free      shared  buff/cache   available
      Mem:           3.7Gi       779Mi       2.2Gi        27Mi       718Mi       2.8Gi
      Swap:          1.0Gi          0B       1.0Gi
    tmpfs filesystem?
                          /var/log       Linux logs : yes
              /home/pi/minimy/logs      Minimy logs : no
               /home/pi/minimy/tmp  Minimy temp dir : no
    ````
    
You should see three changes:

- The Music Playing Daemon, **``mpd``** is now running.
- The one **``pulseaudio``** process has **``--system``** as a parameter which is vital to audio output working correctly.
- The **``/var/log/``** file system is now mounted over an in-memory tmpfs.

### Test microphone and speakers

It is important to know your microphone and speakers are working. 
There are scripts in mycroft-tools named **``testrecord``** and **``testplay``**. 
They are wrappers around the **``arecord``** and **``aplay``** commands designed to make it easier to test recording audio to a file and playing it back on the speakers.

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

### Download and copy Minimy 
It is recommended that you make a second copy of Minimy after you download it.  This way, if you make some changes to the running code, you'll have a reference copy. Also the copy of the code that you run should not have a ``.git/`` directory, thus removing any connection to github.

The directory the copy will run in **must be named**  ``minimy``, removing the ``-mike99mac`` suffix.  Otherwise things will break.

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
    
- Run the following script to install minimy and direct stdout and stderr to a file.
    
    **``$ ./install/linux_install.sh 2>&1 | tee linux_install.out``**
    
    ```
    ...
    Install Complete
    ```
    
    This step can take up to ten minutes. It is recommended that you review the output file, checking for warnings or errors.
    
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
choose mimi2 from Mycroft which is a free remote TTS alternative. You could also select local only TTS in 
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

You need a Google Speech API key in order to be able to convert speech to text.  

Get one from: https://console.cloud.google.com/freetrial/signup/tos

Once you get your key, copy it to ``/home/pi/minimy/install/my-google-key.json``.

An alternative is to use a different STT engine.

## Run Minimy
The scripts **``startminimy``** and **``stopminimy``** are used to start and stop processes. 
Each skill and service run as process and use the message bus or file system to synchronize. 
Their output is written to the ``logs/`` directory under the main install directory. 

The system relies on the environment variables ``PYTHONPATH, SVA_BASE_DIR`` and ``GOOGLE_APPLICATION_CREDENTIALS`` which are set in **``startminimy``** 
with this code:

**TODO:** the first two varaibles should be ``$HOME/minimy``. The third should use $HOME.

    ...
    export PYTHONPATH=`pwd`
    export SVA_BASE_DIR=`pwd`
    export GOOGLE_APPLICATION_CREDENTIALS="/home/pi/minimy/install/my-google-key.json"
    ...

- Start Minimy, ensuring it is run from the base directory, as follows.

    **``(venv_ngv) $ cd $HOME/minimy``**
    
    **``(venv_ngv) $ ./startminimy``**

- Stop Minimy with:

    **``(venv_ngv) $ ./stopminimy``**
    
**TODO:** Show some output of running startminimy and run lsenv again.    

## The buttons process

The smart boombox model with the RasPi on-board has three pushbuttons on the front panel to allow quick access to *previous track*, *pause/resume*, and *next track* operations.  A new **``buttons``** system skill traps button presses and sends corresponding messages to to the bus.

If your enclosure does not have them, you can skip this step.  Or, if you want to add buttons, attach them to the following GPIO pins:

    +-----+--------+-------------------------------+
    | Pin | Label  | Description                   |
    |-----|--------|-------------------------------|
    | 9   | GND    | Ground common to all buttons  |
    | 11  | GPIO17 | Previous track                |
    | 13  | GPIO27 | Pause/resume                  |
    | 15  | GPIO22 | Next track                    |
    +-----+--------+-------------------------------+

The ``buttons.py`` code is here: https://github.com/mike99mac/minimy-mike99mac/blob/main/framework/services/input/buttons.py
    
One source of buttons is here: https://www.amazon.com/dp/B09C8C53DM
    

**TODO:** On another model, the computer is a RaspPi 400 which is *offboard*. This allows Lithium-ion batteries to be on-board. That will need new code that uses the arrow keys for the same function.

## Use Minimy

### Vocabulary

In the samples that follow (words) in parenthesis are the actual words spoken, while {words} in curly brackets become variables populated with the actual words spoken. When (multiple|words|) are separated by vertical bars any of those can be spoken, and a trailing vertical bar means that word can be omitted.

Following is a summary of Minimy's vocabulary.

#### Connectivity skill

``TODO``
 
#### Email skill

``TODO``
 
#### Example1 skill

``TODO``
 
#### Help skill

``TODO``
 
#### MPC skill

The MPC skill can search:

- Your music library
- Internet radio stations
- Internet music
- NPR news 

Following are the vocabularies for the MPC skill

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
    
- Playlist vocabulary (NOTE: code is not complete yet)

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

#### Timedate skill

What time is it?

``TODO: finish``
 
#### Weather skill

What's the weather
``TODO``
 
#### Wiki skill

``TODO``

## What can I say?

**TODO** Add a lot of sample utternaces here ...

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
