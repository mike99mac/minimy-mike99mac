# minimy
Minimy is a simple NLU-based voice assistant framework.
It is a fork of Ken-Mycroft's code at: https://github.com/ken-mycroft/minimy

## Overview
**From Ken Smith:**

"The goal of this project is to provide a run-time environment which facilitates the development of 
voice enabled applications. These voice enabled applications take the form of a 'skill' and are
simply python programs which may do normal python things as well as call speak() and listen() and
get called asynchronously when an utterance is matched to an intent the skill has previously registered."  

**From Mike Mac:**

I worked with the Mycroft free and open personal voice assistant since 2019, but the company went bankrupt in 2023, so had to move on. :((

I tried OVOS/Neon, but was not able to get my music skill going after a couple weeks in early 2023.  I still haven't given up on that platform. There is no doubt it will only get better and easier to install.

Then I found Minimy, and was able to get it running in a few hours. Apparently, it was a project that hoped to save Mycroft from the fire, but it wasn't well received. Thankfully, Ken Smith put it on github, I forked the code, and here we are.  Ken has been a great help in answering my many questions - **Thanks Dude!** So I continue to try to *give back to the community* while standing on the shoulders of so many thousands of others.

One of my mantras is *Less is more*, so I liked minimy as it is a MINI-MYcroft.  Here is a rough estimate of the lines of Python code in the three projects as of May 2023:
```
            Repo         Loc           files
    mycroft-core       38074             229
       ovos-core       18067             238
minimy-mike99mac        9900              79
```
So OVOS is half the size of Mycroft, and Minimy is about half the size of OVOS.

My environment is a Raspberry Pi 4B with 4 GB of memory, running Ubuntu Desktop 22-04 inside a *boombox*. However, this code and these steps should be portable to any hardware that can run Linux, and probably just about any distro, in any type of *enclosure* you fancy.  But if you try it on different hardware, or a different distro - you're on your own - no warranties.

This is based on "The smart boombox cookbook" on https://github.com/mike99mac/mycroft-tools/blob/master/smartBoombox.pdf which describes much detail of building a boombox.  This document focuses just on the steps to get the *software stack* running, and starts from the very beginning.

I have probably reflashed and rebuilt this system 20 or 30 times, and each time I compare notes. So this document should be relatively solid.

## Prepare an SD card to boot Linux
So you have a device that can run Linux - probably from a micro-SD card. A 32 GB card or larger is recommended. You need to *prime the pump* and put a Linux distribution on that card. 

Hopefully you have another computer running Linux, but other OS's will work. The box you use must have a hardware port to write to the card.

### Prepare on Linux

If you have a Linux box with an SD card reader, you can use **``rpi-imager``**. To do so, perform the following tasks.
- Put a micro-SD card into an SD adapter.
- Plug the SD adapter into the card reader.
- Download and install the tool.

    **``$ sudo apt-get install -y rpi-imager``**

### Flash the drive

- Run the tool.

    **``$ rpi-imager``**
    
You should see a window as shown in the following figure. **TODO**: add a screenshot

To flash a Linux image to the card, perform the following steps:

- Select your preferred *Operating System*. **Ubuntu Desktop 22.04 LTS** is recommended. It's a solid OS, and the LTS stands for *Long Term Support*.  Canonical promises to support it for at least four years. 

- Select the *Storage* device. Ideally you will see the one micro-SD card in the dropdown menu.

- Click **Write**.

- Enter the password of the current user.

The tool will start copying to the SD card.  A 64 GB card should take around five minutes.

### Prepare on Windows
If you only have access to a Windows system Install the *Win 32 disk imager* from https://sourceforge.net/projects/win32diskimager/

Further details are not provided.

## Connect the computer hardware

For the initial setup, a keyboard, monitor and mouse are needed. Ideally there will be a way of setting up “headlessly”, but that’s not available yet.

To connect all the computer hardware, perform the following steps:

- Plug the micro-SD card into the back of the RasPi.
- You can access the Internet using either Wi-Fi or with an Ethernet patch cord. If you have wired ethernet, plug it in to the RJ-45 on the RasPi.
- Connect the mouse and keyboard to the USB connections on the RasPi.
- Connect the monitor to the RasPi with an appropriate HDMI cable.  If your Raspberry Pi has two micro HDMI ports, use the left one.
- Now that all the other hardware is connected, plug the 5v power supply with a USB-C end into the RasPi 4. If you have an inline switch has a red LED below the on/off button.

### Boot the RasPi

When you supply power to the Raspberry Pi, it should start booting.  On the top, back, left of the RasPi there are two LEDs:

- The LED to the left should glow solid red. This signifies the RasPi has 5V DC power.
- The LED to the right of the red one should flicker green. This signifies that an operating system is communicating with the CPU. If there is a red light, but no green one, this probably means that the micro-SD card does not have Linux properly installed.

**Important**: Never turn the RasPi off without first shutting Linux down with the **``halt``** or similar command. Doing so can damage the operating system and possibly even the RasPi itself.

You should see a rainbow colored splash screen on the monitor, then the Ubuntu desktop should initialize.

### Initial configuration

A welcome screen should open on the monitor. Perform the following steps:

- On the *Welcome* window, choose your language and click **Continue**.
- On the *Keyboard layout* window, choose your keyboard layout and click **Continue**.
- On the *Wireless* window, if you are not using a hard-wired Ethernet, click **Connect** and configure a Wi-Fi network. You must know the network SSID and will probably be prompted for a password.
- On the *Where are you?* window, choose your time zone.
- On the *Who are you?* window, set the following values:
    - Set your name.
    - Set your computer’s name (host name).
    - For a user name and password ``pi`` is recommended as it is documented in the reminder of this document.
    - For the last option, **Log in automatically** is recommended.
    - Click **Continue**.
 - The install process will take a number of minutes configuring and will reboot the computer.
 - When the system reboots, an *Online Accounts* window should appear. Click **Skip**.
 - Click **Next** at the *Enable Ubuntu Pro* window.
 - Choose an option on the *Help Improve Ubuntu* window and click **Next**.
 - Click **Next** at the *Privacy* window.
 - Click **Done** at the *Ready to go* window.

Ubuntu Desktop should now be installed.

## Install and configure software

To configure Ubuntu, perform the following sections.

### Install SSH server and other software

The secure shell (SSH) server is not installed by default on Ubuntu desktop (which is curious). Install it so you can access your system remotely. 

To do so, perform the following steps:

- Open a terminal session by right-clicking the mouse anywhere on the desktop and choosing **Open in Terminal**. You should see a console window open.
- From that window, install the ``openssh-server`` package, with the following command.  You will be prompted for your password.
    
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
    
In this example, the IP address is 192.168.1.229.

### Start an SSH session

You should now be able to start an SSH session as the user pi, if you want to continue from another desktop system. You can use **putty** to SSH in from a Windows box, or just use the **``ssh``** command from a Linux or macOS terminal session.

### Upgrade your system

Update and upgrade youre system which installs the latest code for all installed packages.

- Enter the following command.  You will be prompted for your password.

    **``$ sudo apt-get update``**
    
- Upgrade your system so you have all the latest code. This step could take up to 25 minutes.

    **``$ sudo apt-get upgrade -y``**
    
Your system should now be at the latest software levels.

### Install Mycroft tools

There is a github repo with some tools to help with the installation and testing of Minimy and associated audio resources.

To install the **``mycroft-tools``** package, perform the following steps:
  
- Make **``vim``** the default editor.

    **``$ sudo update-alternatives --install /usr/bin/editor editor /usr/bin/vim 100``**
    
    ``update-alternatives: using /usr/bin/vim to provide /usr/bin/editor (editor) in auto mode``
    
- Allow members of the ``sudo`` group to be able to run sudo without a password, by adding **``NOPASSWD:``** to the line near the bottom of the file.

    **``$ sudo visudo``**

    ```
    ...
    %sudo   ALL=(ALL:ALL) NOPASSWD: ALL
    ...
    ```

- Clone the **``mycroft-tools``** package in pi’s home directory with the following commands.

    **``$ cd``**
    
    **``$ git clone https://github.com/mike99mac/mycroft-tools.git``**
    
    ```
    Cloning into 'mycroft-tools'...
    ...
    Resolving deltas: 100% (366/366), done.
    ```
    
- Change to the newly installed directory and run the setup script. It will copy scripts to the directory ``/usr/local/sbin`` which is in the default PATH.

    **``$ cd mycroft-tools``**
    
    **``$ sudo ./setup.sh``**
    
    ```
    Copying all scripts to /usr/local/sbin ...
    Success!  There are new scripts in your /usr/local/sbin/ directory
    ```
    
### Use a script to further cusomize

An script named **``install1``** was written to perform many commands and thus save typing and time.  It is in the mycroft-tools package you just installed.
It performs the following taksks:

- Installs the **``mlocate mpc mpd net-tools pandoc python3 python3-pip python3-rpi.gpio python3.10-venv``** packages
- Sets  **``vim``** to a better color scheme and turns off the annoying auto-indent features
- Adds needed groups to users ``pi`` and ``mpd``
- Copies a ``.bash_profile`` to your home directory
- Turns ``default`` and ``vc4`` audio off and does not disable monitor overscan in the boot parameters file
- Changes a line in the **``rsyslog``** configuration file to prevent *kernel message floods*
- Copies a **``systemctl``** configuration file to mount ``/var/log/`` in a tmpfs which helps prolong the life of the micro-SD card
- Sets **``pulseaudio``** to start as a system service at boot time, and allows anonymous access so audio services work
- Configures **``mpd``**, the music player daemon, which plays most of the sound
- Turns off **bluetooth** as Linux makes connecting to it ridiculously hard, while most amplifiers make it ridiculously easy

To run **``intall1``**, perform the following steps:

- First verify it is in your ``PATH`` with the **``which``** command.

    **``$ which install1``**
    
    ``/usr/local/sbin/install1``

- Run the **``install1``** script in the home directory and save the output to a file.

    **``# cd``**
    
    **``$ time install1 | tee install1.out 2>&1``**
    
    ```
    ...
    real    3m25.141s
    user    0m0.299s
    sys     0m0.646s
    ```
    
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

- Minimy processes are not running
- The **``buttons``** daemon is not running, which traps and report physical button push
- The Music Playing Daemon, **``mpd``** is not running
- There is one **``pulseaudio``** process running, but it does not have **``--system``** as a parameter
- Useful information such as IP address, the CPU temperature, root file system, CPU and memory usage
- Which of three file systems frequently written to are mounted over a tmpfs (in memory)

Reboot your system and run lsenv again. Mycroft should not be running, but mpd should be. pulseaudio should also be running with the --system flag.
$ sudo reboot
... reconnect ...
$ lsenv
Status of mycroft:
 -) WARNING: mycroft is not running as a service ... 
    WARNING: no processes matching mycroft found
-------------------------------------------------------------------------
Status of mpd:
 -) mpd is running as a service:
    Active: active (running) since Wed 2023-03-01 13:01:13 EST; 1min 15s ago
-------------------------------------------------------------------------
Status of pulseaudio:
 -) pulseaudio is running as a service:
    Active: active (running) since Wed 2023-03-01 13:01:11 EST; 1min 17s ago
    pulseaudio processes:
    pulse        819       1  0 13:01 ?        00:00:00 /usr/bin/pulseaudio --system --disallow-exit --disallow-module-loading --disable-shm --exit-idle-time=-1


## Installation
Installation should be run as a non-root user such as 'pi'. Run the install script:
```
$ ./install/linux_install.sh
```
This step can take up to ten minutes.
## Configuration
You can run a basic configuration with the command:
```
$ ./mmconfig.py
```
or, for more configuration options:
```
$ ./mmconfig.py sa
```

## Running
The system uses ./start.sh and ./stop.py to start and stop the system en masse. Each
skill and service run in their own process space and use the message bus or file system
to synchronize. Their output may be found in the directory named 'logs/'. 

The system relies on the environment variables ``SVA_BASE_DIR`` and ``GOOGLE_APPLICATION_CREDENTIALS``.
These are typically set in the start.sh script.

The SVA_BASE_DIR is set to the install directory of your system. The Google variable is set
based on where your Google Speech API key is located. 

Start a virtual environment
```
source venv_ngv/bin/activate<br/><br/>
```
Then start Minimy with:
```
$ ./start.sh
```
To stop Minimy:
```
$ ./stop.py
```
These must be run from the base directory.  The base directory is defined as where you installed this code to. 
For example:
```
/home/pi/minimy-mike99mac
```

If you don't have a Google Speech API key you 
can get one from here ...

https://console.cloud.google.com/freetrial/signup/tos

The start.sh file must then be modified to use this
key. The Google Python module actually requires this
enviornment variable but as mentioned it is typically 
set in the start.sh script. You could, if you like,
set it manually.

```
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/my/key/key_filename.json
```

## Configuration Explained

* ./mmconfig.py # basic
* ./mmconfig.py sa # super advanced options

<br/>
The system can use local or remote services for speech to text (STT), text to speech (TTS)
and intent matching. Intent matching is accomplished using natutal language processing (NLP) based on
the CMU link parser using a simpe enumerated approach referred to as shallow parsing.

As a result you will be asked during configuration if you would like to use remote or local STT, TTS
and NLP. Unless you have a good reason, for now you should always select local mode (remote=n) for NLP.

Remote TTS using polly requires an Amazon ID and key.  If you prefer to not use polly for remote TTS you may 
choose mimi2 from Mycroft which is a free remote TTS alternative. You could also select local only TTS in 
which case mimic3 should work fine.

By deault the system will fallback to local mode if a remote service fails. This will happen
automatically and result in a slower overall response. If the internet is going to be out
often you should probably just select local mode.  The differences are that remote STT is more accurate
and remote TTS sounds better. Both are slower but only slightly when given a reasonable internet
connection. Devices with decent connectivity should use remote for both.

You will also be asked for operating environment.  Currently the options are (p) for piOS, (l) for 
Ubuntu or (m) for the Mycroft MarkII running the Pantacor build.

This system relies on the concept of a wake word.  A wake word is one or more words which will cause 
the system to take notice of what you say next and then act upon this.

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
'k's) will always work better than words like 'hey' or 'Joe'. You can use the test_recognition.sh 
script to see how well your recognition is working.  Just using the word 'computer' should work adequately.

You will also be asked to provide an input device index. If you do not know what this means enter the
value 0. If you would like to see your options you can run 'python framework/tests/list_input_devices.py'.
Remember, if you do not source your virtual environment first, things will not go well for you. 

So remember to always source the virtual environment before you run anything. The SVA_BASE_DIR and 
PYTHONPATH environments being set properly also helps.

You may also modify the default audio output device.  This value is used by the system aplay command 
and the system mpg123 command. To see your options run 
```
aplay -L
```
Which will produce a series of lines which look something like this ...
```
sysdefault:CARD=Headset
```
Remove the 'CARD=' and provide the value 
```
sysdefault:Headset
```
To the configuration program.

Local TTS refers to the local TTS engine.  Currently three are supported. Espeak, Coqui
and mimic3. Mimic3 is strongly recommended.

The Mark2 does not have Coqui as an option as it does not currently work on the Mark2. Espeak is
very fast but the sound quality is poor. Coqui sound quality is excellent but it takes forever
to produce a wav file (3-8 seconds). 

The crappy AEC value is used to determine if the system needs to work around poor quality AEC or
if it does not. Good quality AEC is typically provided by a standard set of headphones whereas
poor quality AEC is what you normally have if you were using a laptop's built in speaker and mic.

An easy way to test this setting in your environment would be to run the 'example 1' skill and see how 
well it recognizes you.
```
Hey Computer ---> run example one
```
Finally, you must provide a logging level. The characters 'e', 'w', 'i', 'd' correspond to the 
standard log levels. Specifically 'e' sets the log level to 'error' and 'd' sets it to 'debug', etc.

Once you confirm your changes you can see what was produced by typing 'cat install/mmconfig.yml'. You 
should not modify this file by hand even thought it may be enticing to do so.

