# Decentralized Graffiti Drawing

This generic tool helps you draw images on the beaconcha.in graffitiwall for 
[pyrmont](https://pyrmont.beaconcha.in/graffitiwall) or
[mainnet](https://beaconcha.in/graffitiwall). First, use the Viewer to generate a config
representing your image on the wall. Then share it with your friends and start drawing together!

![Rocketpool](rocketpool/desired.png "Default settings")


## Requirements
You need python3 with some libraries. Install dependencies with `pip install -r requirements.txt`.
It should support all four clients on amd64 and arm64 (raspberry pi & co).
[Note: I didn't test Prysm yet, let me know if it breaks!]

## Rocketpool users
While this tool can be used by any eth2 staker, here is an easy solution for rocketpool
users. The first image we decided to draw is the Rocket Pool logo.
By following the instructions you can help drawing! Once we're done there will be a new image.

Just run these commands to get started. It's assumed you're running rocketpool the normal way (default install directory of `.rocketpool`, 
using docker etc.). If you don't, you probably know what you are doing and are able to modify accordingly.
```
  wget https://raw.githubusercontent.com/RomiRand/DecentralizedGraffitiDrawing/rocket_pool/rocketpool/install.sh -P ~/.rocketpool/graffiti/
  wget https://raw.githubusercontent.com/RomiRand/DecentralizedGraffitiDrawing/rocket_pool/rocketpool/uninstall.sh -P ~/.rocketpool/graffiti/
  chmod +x ~/.rocketpool/graffiti/install.sh ~/.rocketpool/graffiti/uninstall.sh
```
To install, run this command. This will briefly stop your rocketpool stack, add the graffiti container and restart it:
  `~/.rocketpool/graffiti/install.sh` \
uninstall:`~/.rocketpool/graffiti/uninstall.sh`


## Viewer
The viewer loads the current graffitiwall as well as an image. You can move it around or
scale it until you found your favorite spot. Once you're done, you can save your
desired configuration, so it can be picked up by the Drawer.
### Usage:
`python3 Viewer.py` \
You can move your image around using `wasd` and scale it with `+` and `-`
(using different interpolation methods, iterated by `i`). To hide your image behind already drawn
pixels, use `o` (example shown below), `h` to hide it entirely. At any time you can print (to console)
the amount of pixels needed with `c`. Print a list of participators with `1` for eth1 addresses and `2` for eth2 validators.
To save your settings, press `f`. `Esc` or `q` to exit.

To use your own file instead, edit `settings.ini` accordingly.

<img src="https://raw.githubusercontent.com/RomiRand/rpl_graffiti/main/doc/overpaint.png" width="400">

## Drawer
This component performs the decentralized drawing. The script identifies invalid pixels
and fixes them. It checks all relevant data in defined intervals.

### Usage
Check out `python3 Drawer.py --help` for available parameters. You need to specify your client because
they each expect the graffiti file to be in a specific format. \
Example: `python3 Drawer.py --network pyrmont --client lighthouse --out-file /mnt/ssd/lighthouse/graffiti.txt`

Lighthouse, Teku and Prysm read the generated graffiti from a file.
Nimbus gets updated via RPC.\
Just let the script run in another process (using screen, for example).
Also don't forget restarting your eth2 validator client with the file specified / rpc enabled:
- [Lighthouse](https://lighthouse-book.sigmaprime.io/graffiti.html#1-using-the---graffiti-file-flag-on-the-validator-client):
  `lighthouse vc --graffiti-file /path/to/your/graffiti.txt`
- [Prysm](https://docs.prylabs.network/docs/prysm-usage/graffiti-file/): 
  `prysm.sh validator --graffiti-file=/path/to/your/graffiti.txt`
- [Teku](https://docs.teku.consensys.net/en/latest/Reference/CLI/CLI-Syntax/#validators-graffiti-file):
  `teku vc --validators-graffiti-file=/path/to/your/graffiti.txt`
- [Nimbus](https://nimbus.guide/api.html#introduction): `nimbus_beacon_node --rpc`

### Contributing
If you find any issues or want to help developing this tool, you can open an issue.
Also, feel free to contact me for feedback.

### Disclaimer
  In theory, it shouldn't be possible for this script to interrupt your staking performance,
but I won't promise that. Use at your own risk.
