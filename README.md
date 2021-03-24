# Decentralized Graffiti Drawing

This generic tool helps you draw images on the beaconcha.in graffitiwall for 
[pyrmont](https://pyrmont.beaconcha.in/graffitiwall) or
[mainnet](https://beaconcha.in/graffitiwall). First, use the Viewer to generate a config
representing your image on the wall. Then share it with your friends and start drawing together!

![Rocketpool](rocketpool/desired.png "Default settings")

## Rocketpool users
While this tool can be used by any eth2 staker, I want to provide an easy solution for rocketpool beta
users. Below I'll explain how to setup a docker container that's running along the rocketpool stack.
It will draw above situation (but on pyrmont). 



## Requirements
You'll need python3 with some libraries. Check [requirements.txt](requirements.txt)
Python will complain if you don't already have them installed, google if you don't know how to
do that.

## Viewer
The viewer loads the current graffitiwall as well as an image. You can move it around or
scale it until you found your favorite spot. Once you're done, you can save your
desired configuration, so it can be picked up by the Drawer.
### Usage:
`python3 Viewer.py` \
You can move your image around using `wasd` and scale it with `+` and `-`
(using different interpolation methods, iterated by `i`). To hide your image behind already drawn
pixels, use `o` (shown below), `h` to hide it entirely. At any time you can print (to console)
the amount of pixels needed with `c`. To save your settings, press `f`. `Esc` or `q` to exit.

To use your own file instead, edit `settings.ini` accordingly.

<img src="https://raw.githubusercontent.com/RomiRand/rpl_graffiti/main/doc/overpaint.png" width="400">

## Drawer
This component performs the decentralized drawing. The script identifies invalid pixels
and fixes them. It checks all relevant data in defined intervals.

### Usage
Check out `python3 Drawer.py --help` for available parameters. You need to specify your client because
they each expect the graffiti file to be in a specific format. \
Example: `python3 Drawer.py --network pyrmont --client lighthouse --out-file /mnt/ssd/lighthouse/graffiti.txt`

Lighthouse, Teku and Prysm support reading the generated graffiti file, Nimbus isn't supported (yet!).
Just let the script run in another process (using screen, for example).
Also don't forget restarting your eth2 validator client with the file specified:
- [Lighthouse](https://lighthouse-book.sigmaprime.io/graffiti.html#1-using-the---graffiti-file-flag-on-the-validator-client):
  `lighthouse vc --graffiti-file /path/to/your/graffiti.txt`
  `lighthouse vc --graffiti-file /mnt/ssd/lighthouse/graffiti.txt`
- [Prysm](https://docs.prylabs.network/docs/prysm-usage/graffiti-file/): 
  `prysm.sh validator --graffiti-file=/path/to/your/graffiti.txt`
- [Teku](https://docs.teku.consensys.net/en/latest/Reference/CLI/CLI-Syntax/#validators-graffiti-file):
  `teku vc ----validators-graffiti-file=/path/to/your/graffiti.txt`

### Disclaimer
In theory, it shouldn't be possible for this script to interrupt your staking performance,
but I won't promise that. Use at your own risk.
