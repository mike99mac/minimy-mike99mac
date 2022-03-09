#!/bin/bash
#
# simple audio timer script
# Usage:
#   ./timer_test.sh seconds 
# Example 
#  ./timer_test.sh 15
# note seconds must be at least 10
# anything less will be forced to 10
#
END=$1-10
for ((i=1;i<=END;i++)); do
    aplay tick.wav
done
# timer 
# must be more than 10 seconds
# so play tick x times until last
# ten seconds then play last_ten
# and finally three alarms
mpg123 last_ten.mp3
mpg123 alarm1.mp3
mpg123 alarm1.mp3
mpg123 alarm1.mp3
