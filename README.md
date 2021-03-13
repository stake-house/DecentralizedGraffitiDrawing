# Graffiti Drawer

This generic tool helps you drawing images on the beaconcha.in graffitiwall for 
[pyrmont](https://pyrmont.beaconcha.in/graffitiwall) or
[mainnet](https://beaconcha.in/graffitiwall). It consists of a viewer which allows
convenient image placement and a drawer which performs actually drawing.
This tool can be used for every image by anyone, but it will be focused on easy integration
to the RocketPool Eth2 smartnode-stack.

## Viewer
The viewer loads the current graffitiwall as well as your image. You can move it around or
scale it until you found your favorite spot. Scaling can be done using different interpolation
methods. Once you're done, you can save your desired configuration to be picked up by the
Drawer.

## Drawer
The main feature of this component is overdraw-resistance. Lighthouse, Prysm and Teku clients
already support drawing of preset pixel data which can be used to draw images; However they
won't detect (yet?) if someone destroys your image by drawing on top of it. This script
allows you to identify invalid pixels ASAP and fixes them automatically. It checks all
relevant data once per epoch (every ~6.5 minutes).

## Rocketpool users
This is WIP. I'll try to integrate the script nicely into rocketpools docker stack so you 
don't have to worry about graffiti files, client compatibility and other stuff.

The current (default) settings are aimed to replace a obscene element on the wall with rocketpool's logo.
It'd currently need 14234 pixels to do so; with 7200 blocks per day and a share of 10% for rocketpool,
it should take about 20 days to reach this goal. This can be tested in the next rocketpool
beta first.

## General use

