import argparse
import configparser
import json

import cv2
import numpy as np
import requests
import time
import os


interpolation_modes = {
    "near": cv2.INTER_NEAREST,
    "lin": cv2.INTER_LINEAR,
    "cube": cv2.INTER_CUBIC,
    "area": cv2.INTER_AREA,
    "lanc4": cv2.INTER_LANCZOS4,
    "lin_ex": cv2.INTER_LINEAR_EXACT,
}


def getProposalsBeaconchain():
    if args.network == "pyrmont":
        url = "https://pyrmont.beaconcha.in/api/v1/epoch/latest/blocks"
    else:
        url = "https://beaconcha.in/api/v1/epoch/latest/blocks"
    try:
        page = requests.get(url)
    except requests.exceptions.RequestException as e:
        print("can't reach Beaconcha.in: " + e)
        return
    if page.status_code != 200:
        print("status code: " + str(page.status_code))
        return
    p = set()
    for block in page.json()['data']:
        p.add(block['proposer'])
    return p


def getPixelWallData():
    global wall
    if args.network == "pyrmont":
        url = "https://pyrmont.beaconcha.in/api/v1/graffitiwall"
    else:
        url = "https://beaconcha.in/api/v1/graffitiwall"
    try:
        page = requests.get(url)
    except requests.exceptions.RequestException as e:
        print("can't reach graffitiwall: " + e)
        return
    if page.status_code != 200:
        print("error fetching wall")
        return
    w = page.json()["data"]

    # filter visible area
    wall = dict()
    for pixel in w:
        if y_offset <= pixel["y"] < y_offset + int(cfg['YRes']) and \
                x_offset <= pixel["x"] < x_offset + int(cfg['XRes']):
            wall[pixel["y"] - y_offset, pixel["x"] - x_offset] = tuple(int(pixel["color"][i:i+2], 16) for i in (0, 2, 4))


def updateDrawPixels():
    # add already set pixels which might need to be re-drawn
    # TODO do this without loop? but the wall is full of wholes
    overdraw = np.full_like(white_pixels, False)
    for k, v in wall.items():
        overdraw[k[0], k[1]] = np.any(img[k[0], k[1], :3] != v)

    return static_draw + (~transparent_pixels * overdraw)


def getPixel():
    draw_y, draw_x = np.where(draw_pixels)
    if len(draw_y) > 0:
        random_pixel_index = np.random.choice(len(draw_y))
        y = draw_y[random_pixel_index]
        x = draw_x[random_pixel_index]
        color = format(img[y][x][0], '02x')
        color += format(img[y][x][1], '02x')
        color += format(img[y][x][2], '02x')
        return "graffitiwall:" + str(x + x_offset) + ":" + str(y + y_offset) + ":#" + color
    return "RocketPool"


def getImage():
    x_res = int(cfg['XRes'])
    y_res = int(cfg['YRes'])
    file = cfg['ImagePath']
    if not os.path.isabs(file):
        file = os.path.dirname(os.path.abspath(__file__)) + "/" + os.path.basename(file)
    orig_img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    _, _, channels = orig_img.shape
    int_mode = cfg["interpolation"]
    if int_mode not in interpolation_modes:
        print("unknown interpolation mode: " + cfg["interpolation"])
        exit(1)
    resized = cv2.resize(orig_img, dsize=(x_res, y_res), interpolation=interpolation_modes[int_mode])
    # support for various formats (grayscale, jpg, png, ...)
    if channels == 1:
        img = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGBA)
    elif channels == 3:
        img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGBA)
    elif channels == 4:
        img = cv2.cvtColor(resized, cv2.COLOR_BGRA2RGBA)
    return img, min(1000 - x_res, int(cfg['XOffset'])), min(1000 - y_res, int(cfg['YOffset']))


def setNimbusGraffiti(graffiti):
    url = "http://" + args.nimbus_rpc_url + ":" + str(args.nimbus_rpc_port) + "/jsonrpc"
    headers = {'content-type': 'application/json'}

    payload = {
        "method": "setGraffiti",
        "params": [graffiti],
        "jsonrpc": "2.0",
        "id": "id",
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers).json()
    except requests.exceptions.RequestException as e:
        return False
    return 'result' in response


def updateValidators():
    global validators
    _, new_folders, _ = next(os.walk(args.validator_dir))
    diff = set(new_folders) - validators
    if len(diff) != 0:
        print("loading " + str(len(diff)) + " new keys: ")
        for element in diff:
            print(element)
    validators = set(new_folders)


def getWaitTime():
    if args.network == "pyrmont":
        url = "https://pyrmont.beaconcha.in/api/v1/block/latest"
    else:
        url = "https://beaconcha.in/api/v1/block/latest"
    try:
        page = requests.get(url)
    except requests.exceptions.RequestException as e:
        print("can't reach Beaconcha.in: " + e)
        return
    if page.status_code != 200:
        print("status code: " + str(page.status_code))
        return
    slot = page.json()['data']['slot']
    print("slot in epoch: " + str(slot % 32))
    w = 12 * (32 - (slot % 32))
    return w


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced beaconcha.in graffitiwall image drawer.')
    parser.add_argument('--network', default='mainnet', choices=['mainnet', 'pyrmont'],
                        help='pyrmont or mainnet (default: mainnet)')
    parser.add_argument('--out-file', default='./graffiti.txt', help='Out location of the generated graffiti file (default: ./graffiti.txt).')
    parser.add_argument('--settings-file', default='./settings.ini', help='Settings file location (default: ./settings.ini).')
    parser.add_argument('--client', required=True, choices=['prysm', 'lighthouse', 'teku', 'nimbus'], help='your eth2 client.')
    parser.add_argument('--nimbus-rpc-url', default='localhost', help='Your nimbus client RPC url (default: localhost).')
    parser.add_argument('--nimbus-rpc-port', default=9190, help='Your nimbus client RPC port (default: 9190).')
    # update mode
    # TODO move this to settings file ?
    parser.add_argument('--update-mode', default='interval', choices=['interval', 'on-proposal'], help='Select when to update pixel data (default: interval).')
    parser.add_argument('--update-wall-time', default=600, help='Interval between graffiti wall updates (default: 600s).')
    parser.add_argument('--update-file-time', default=30, help='Interval between graffiti file updates (default: 30s).')
    parser.add_argument('--validator-dir', required=True, help='Your eth2 validator key directory.')
    parser.add_argument('--infura-id', help='Your eth2 infura project id.')
    parser.add_argument('--eth2-url', help='Your eth2 node url.')  # assumes client selected by --client
    parser.add_argument('--eth2-port', help='Your eth2 node port.')

    args = parser.parse_args()

    if args.update_mode == 'on-proposal' and not os.path.isdir(args.validator_dir):
        print("invalid validator path: " + args.validator_dir)
        exit(0)

    config = configparser.ConfigParser()
    config.read(args.settings_file)
    cfg = config['GraffitiConfig']
    img, x_offset, y_offset = getImage()

    white_pixels = np.all(img[:, :, :3] == [255, 255, 255], axis=-1)
    transparent_pixels = img[..., 3] == 0
    static_draw = ~(white_pixels + transparent_pixels)

    last_wall_update = 0
    last_file_update = 0
    wall = dict()
    # file formatting
    pre = ""
    post = ""
    if args.client != "teku":
        pre += "default: "
        if args.client == "prysm":
            pre += '"'
            post = '"'

    validators = set()
    # Start the work!
    print("Generating graffitis...")
    while True:
        if args.update_mode == 'interval':
            now = time.time()
            if last_wall_update + args.update_wall_time < now:
                getPixelWallData()
                draw_pixels = updateDrawPixels()
                last_wall_update = now
            if last_file_update + args.update_file_time < now:
                if args.client == "nimbus":
                    if not setNimbusGraffiti(getPixel()):
                        print("error setting nimbus graffiti")
                else:
                    with open(args.out_file, 'w') as f:
                        f.write(pre + getPixel() + post)
                last_file_update = now
            time.sleep(10)
        elif args.update_mode == 'on-proposal':
            # 1. load the keys (could be more/others since last time)
            updateValidators()
            # 2. get current proposers
            proposers = getProposalsBeaconchain()
            # 3. check if we can propose
            if len(proposers.intersection(validators)) != 0:
                print(len(proposers.intersection(validators)))
            time.sleep(getWaitTime())
            continue
