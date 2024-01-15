# Building a boombox

This describes how to build a smart boombox. 

## Overview
"The goal of this project is to create a really fucking cool boombox that sounds amazing and can play music by voice. 

## G-code
The following G-code files are used on a CNC machine to cut out all the pieces.
All panels should be 1/2" (nominal - usually .480") baltic birch.
The main panel is cut in two CNC jobs, and later is cut on the tablesaw to create four pieces: the front, the bottom, the back and interior divider. Because the panel is over 30", the maximum for many CNC machines, it must be cut twice rotating 180 degrees.  

The side 

| G-code file       | Size   | Description |
| -----------       | ----   | -----------
| 4PanelsMainJob.nc | 19.875" wide x 32.295" high | Most cuts on the main panel  |
| faceUpsideDown.nc | 19.875" wide x 32.295" high | Remaining cuts on the top face |
| leftSide.nc       | 7.386" wide x 11.875" high| Cuts on the assembled left side |
| righttSide.nc     | 7.386" wide x 11.875" high| Cuts on the assembled right side |

## Assembling the sides
The rigth and left sides are a piece of baltic birch framed by hardwood moldings. 
