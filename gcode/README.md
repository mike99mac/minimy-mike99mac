# Building a boombox

This describes how to build a smart boombox. 

## Overview
The goal of this project is to create a really f***ing cool boombox that sounds amazing and can play music by voice. 

## Bill of material
Following are the wood parts that need to be cut out.
All panels are from 1/2" baltic birch plywood. The nominal size should be 0.480".
All moldings are cut from "one by ones" hardwood. The nominal size will be 0.820" x 0.820".

### Plywood
- 1 Main panel: 19.875" wide x 32.295" high
- 2: Sides: TODO: get exact size

### Moldings
TODO

## G-code
The following G-code files are used on a CNC machine to cut out all the pieces.
All panels should be 1/2" (nominal - usually .480") baltic birch.
The main panel is cut in two CNC jobs, and later is cut on the tablesaw to create four pieces: the front, the bottom, the back and interior divider. Because the panel is over 30", the maximum for many CNC machines, it must be cut twice rotating 180 degrees.  

The side 

| G-code file       | Size   | Description |
| -----------       | ----   | -----------
| 4PanelsMainJob.nc | 19.875" wide x 32.295" high | Most cuts on the main panel  |
| faceUpsideDown.nc | 19.875" wide x 32.295" high | Remaining cuts on the top face with panel rotated 180 degrees |
| leftSide.nc       | 7.386" wide x 11.875" high| Cuts on the assembled left side |
| righttSide.nc     | 7.386" wide x 11.875" high| Cuts on the assembled right side |

## Assembling the sides
The right and left sides are a piece of baltic birch framed by hardwood moldings. 

## Drilling holes in the face
After the two jobs are finished on the main panel, 
Always use masking tape on the front face and sharp Forstner bits!

2 holes for jacks:   11/32 (.344")
3 holes for buttons:  9/32 (.281") 
5 holes for amp:     19/64 (.297") 

Distance between each of the 5 knobs on amp: .720"

