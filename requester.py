import argparse
import configparser

import cv2
import numpy as np
import requests
import json
from datetime import datetime
import time
import os

user = "1pQO0ZiEx0FExWddgBK31GPQykI"
pas = "3f2f041c2c959d8c3551890df3a6c670"
headers = {'content-type': 'application/json'}

interpolation_modes = {
    "near": cv2.INTER_NEAREST,
    "lin": cv2.INTER_LINEAR,
    "cube": cv2.INTER_CUBIC,
    "area": cv2.INTER_AREA,
    "lanc4": cv2.INTER_LANCZOS4,
    "lin_ex": cv2.INTER_LINEAR_EXACT,
    # "max": cv2.INTER_MAX,
    # "warp_fill": cv2.WARP_FILL_OUTLIERS,
    # "warp_inv": cv2.WARP_INVERSE_MAP,
}


def getProposals(epoch):
    payload = {
        "method": "get_v1_validator_duties_proposer",
        "params": [epoch],
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(
        url, data=json.dumps(payload), headers=headers).json()

    print(response)
    # print(json.dumps(response, indent=4))


def getCurEpoch():
    payload = {
        "method": "getBeaconHead",
        "params": [],
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(
        url, data=json.dumps(payload), headers=headers).json()

    epoch = int(response["result"] / 32)
    print("epoch:" + str(epoch) + " slot: " + str(response["result"]))
    return epoch


def getPixelWallData():
    global network
    if network == "mainnet":
        url = "https://beaconcha.in/graffitiwall"
    elif network == "pyrmont":
        url = "https://pyrmont.beaconcha.in/graffitiwall"
    else:
        print("wrong network!")
        return
    page = requests.get(url)
    found = False
    wall_string = ""
    for line in page:
        if found:
            wall_string += line.decode("utf-8").split("\n")[0]
            if b'}]\n' in line:
                break
            continue
        if b"var pixels = [{" in line:
            found = True
            wall_string += line.decode("utf-8").split("var pixels = ", 1)[1]

    w = json.loads(wall_string)
    wall = dict()
    for pixel in w:
        # filter visible area
        if y_offset <= pixel["y"] < y_offset + y_res and \
                x_offset <= pixel["x"] < x_offset + x_res:
            wall[pixel["y"] - y_offset, pixel["x"] - x_offset] = tuple(int(pixel["color"][i:i+2], 16) for i in (0, 2, 4))
    return wall


def getPixel():
    global x_res, y_res, img, wall
    simulate = False # Debug stuff, remove
    white_pixels = np.all(img[:, :, :3] == [255, 255, 255], axis=-1)
    transparent_pixels = img[..., 3] == 0
    # add already set pixels which might need to be over-drawn
    overdraw = np.full_like(white_pixels, False)
    i2 = np.full((150, 150, 3), 255, np.uint8)
    for k, v in wall.items():
        overdraw[k[0], k[1]] = np.any(img[k[0], k[1], :3] != v)
        if simulate:
            i2[k[0], k[1]] = [v[2], v[1], v[0]]

    draw_pixels = ~(white_pixels + transparent_pixels) + (~transparent_pixels * overdraw)
    draw_y, draw_x = np.where(draw_pixels)
    change_color = 0
    add_pixel = 0
    if simulate:
        cv2.imshow("test", cv2.resize(i2, dsize=(600, 600)))
        cv2.waitKey(2000)
    while len(draw_y) > 0:
        if simulate:
            cv2.imshow("test", cv2.resize(i2, dsize=(600, 600)))
            cv2.waitKey(1)
        random_pixel_index = np.random.choice(len(draw_y))
        y = draw_y[random_pixel_index]
        x = draw_x[random_pixel_index]
        draw_y = np.delete(draw_y, random_pixel_index)
        draw_x = np.delete(draw_x, random_pixel_index)
        #pot_key = str(y_offset + y) + ":" + str(x_offset + x)
        color = format(img[y][x][0], '02x')
        color += format(img[y][x][1], '02x')
        color += format(img[y][x][2], '02x')
        if (y, x) not in wall:
            wall[(y, x)] = img[y, x, :3]
            add_pixel += 1
            if simulate:
                i2[y, x] = [img[y, x, 2], img[y, x, 1], img[y, x, 0]]
            else:
                return str(x + x_offset) + ":" + str(y + y_offset) + ":#" + color
        elif (wall[(y, x)] != img[y, x, :3]).any():
            change_color += 1
            wall[(y, x)] = img[y, x, :3]
            if simulate:
                i2[y, x] = [img[y, x, 2], img[y, x, 1], img[y, x, 0]]
            else:
                return str(x + x_offset) + ":" + str(y + y_offset) + ":#" + color
    if simulate:
        cv2.waitKey(0)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced beaconcha.in graffitiwall image drawer.')
    parser.add_argument('--client', required=True, choices=['prysm', 'lighthouse', 'teku'],
                        help='your eth2 client (nimbus not supported yet)')
    parser.add_argument('--network', default='mainnet', choices=['mainnet', 'pyrmont'],
                        help='pyrmont or mainnet (default: mainnet)')
    parser.add_argument('--out-dir', default='.', help='out location of the generated graffiti_file')
    parser.add_argument('--validator-dir', required=True, help='location of your validator keys')
    # TODO add config for client's ip and port

    # CHEK same for all clients ? correct ip ?
    infura_ip = "https://eth2-beacon-pyrmont.infura.io/"
    local_ip = "http://127.0.0.1:5052/"
    sub_head = "eth/v1/beacon/headers/head"
    sub_proposals = "eth/v1/validator/duties/proposer/"
    args = parser.parse_args()

    # debug
    chosen_ip = local_ip

    config = configparser.ConfigParser()
    config.read('settings.ini')
    cfg = config['GraffitiConfig']
    orig_img = cv2.imread(cfg['ImagePath'], cv2.IMREAD_UNCHANGED)
    x_res = int(cfg['XRes'])
    y_res = int(cfg['YRes'])
    network = cfg['network']
    _, _, channels = orig_img.shape
    x_offset = min(1000 - x_res, int(cfg['XOffset']))
    y_offset = min(1000 - y_res, int(cfg['YOffset']))
    int_mode = cfg["interpolation"]
    if int_mode not in interpolation_modes:
        print("unknown interpolation mode: " + cfg["interpolation"])
        exit(1)
    resized = cv2.resize(orig_img, dsize=(x_res, y_res), interpolation=interpolation_modes[int_mode])
    if channels == 1:
        img = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGBA)
    elif channels == 3:
        img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGBA)
    elif channels == 4:
        img = cv2.cvtColor(resized, cv2.COLOR_BGRA2RGBA)

    validators = set()
    while True:
        if not os.path.isdir(args.validator_dir):
            print("invalid validator path: " + args.validator_dir)
            break
        _, new_folders, _ = next(os.walk(args.validator_dir))
        diff = set(new_folders) - validators
        if len(diff) != 0:
            print("loading " + str(len(diff)) + " new keys: ")
            for element in diff:
                print(element)
        validators = set(new_folders)

        res = requests.get(chosen_ip + sub_head, auth=(user, pas)).json()
        cur_slot = int(res["data"]["header"]["message"]["slot"])
        wait_time = 12 * (32 - (cur_slot % 32))    # lh can't look into the future, we'll need to time the first block
        epoch = int(cur_slot / 32)
        # print("slot: " + str(cur_slot) + " [" + str(cur_slot % 32) + "/32], epoch: " + str(epoch))
        if args.client != "lighthouse":
            epoch += 1
        res2 = requests.get(chosen_ip + sub_proposals + str(epoch), auth=(user, pas))
        if res2.status_code != 200:
            print("can't reach beacon, error " + str(res2.status_code))
            print(res2.json())
            time.sleep(wait_time)
            continue
        arr = res2.json()["data"]
        for duty in arr:
            if duty["pubkey"] in validators:
                wall = getPixelWallData()
                graf = "graffitiwall:" + getPixel()
                print("[" + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + "] " + \
                    duty["validator_index"] + " proposing on slot " + duty["slot"] + ": " + graf)
                with open(args.out_dir + 'graffiti_file.txt', 'w') as f:
                    f.write("default: " + graf)
        time.sleep(wait_time)
