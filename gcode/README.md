# Building a boombox

This describes how to build a smart boombox. 

## Overview
The goal of this project is to create a really f***ing cool boombox that sounds amazing and can play music by voice. 

The picture of the front shows the “carcass” which has three enclosures below for the left, right and subwoofer, and the space above for the amp, computer and other components. Two removable panels allow easy access to the components. It’s constructed of 1/2" Baltic birch plywood with some rare curly oak for the edge moldings. The decorative molding in the front is curly maple and cherry. The subwoofer is “down firing” while the other 5-1/4" device in front is a “passive radiator” - a speaker with no electronics. There is also a smaller passive radiator on the back, so the subwoofer is effectively driving three “speakers”. The left and right enclosures get 4" mid-range and 1" tweeters. “Crossover networks” come with the tweeters, so no soldering required. The tweeters really do bring out the highs when compared with “full range drivers”, and of course, the subwoofer and friends really bring out the lows. There will be a 3.5mm headphone jack on the left, and an “aux in” on the right. The left and right enclosures are ported with 1-3/4" ports seen on the sides. The sub and mid-ranges are protected with grills, while the passive radiators are unprotected because they’re the cheapest to replace and look kinda cool naked.

![image](parts-front-view.jpg)

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

