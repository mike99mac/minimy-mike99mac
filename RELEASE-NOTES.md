# Minimy Release notes

This repo, minimy-mike99mac is a fork of Ken Smith's Minimy at https://github.com/ken-mycroft/minimy

It will be used to drive a *Smart Boombox*, powered by a Raspberry Pi which can be described as a *personal voice assistant and general purpose computer with really great sound*.

It only knows English - there is little internationalization code.

The version numbers are simply *yy.mm.dd*.

Version 23.06.20
----------------
- Pressing stop button for more than 2 seconds now does "mpc stop" which clears the queue
- Fixed a couple of small bugs

Version 23.06.11
----------------
- Initial release
- Complete documentation in README.md - details on all steps to install, configure and use
- Works with an associated repo, mycroft-tools, to speed install and add a box of useful tools
- A new music playing skill that uses the mpc/mpd packages. It can:
    - Play music from a library (mp3 files, etc.)
    - Play Internet radio stations
    - Play Internet music
    - Play NPR news
    - Create, manipulate, delete and play playlists (NOTE: code is not finished yet)
    - Perform basic player operations
- Code to mount /var/log and two Minimy directories over a tmpfs so as to extend the life of the SD card
- A *buttons* system skill enables 3 pushbuttons: 'previous', 'pause/resume' and 'next'.
- Many debug statements were added so log files will be more helpful
