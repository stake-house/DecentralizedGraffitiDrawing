import argparse
import configparser

import cv2
import numpy as np
import requests
import time


interpolation_modes = {
    "near": cv2.INTER_NEAREST,
    "lin": cv2.INTER_LINEAR,
    "cube": cv2.INTER_CUBIC,
    "area": cv2.INTER_AREA,
    "lanc4": cv2.INTER_LANCZOS4,
    "lin_ex": cv2.INTER_LINEAR_EXACT,
}


def getPixelWallData():
    global wall
    if args.network == "mainnet":
        url = "https://beaconcha.in/api/v1/graffitiwall"
    elif args.network == "pyrmont":
        url = "https://pyrmont.beaconcha.in/api/v1/graffitiwall"
    else:
        print("unknown network!")
        return
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
    orig_img = cv2.imread(cfg['ImagePath'], cv2.IMREAD_UNCHANGED)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced beaconcha.in graffitiwall image drawer.')
    parser.add_argument('--network', default='mainnet', choices=['mainnet', 'pyrmont'],
                        help='pyrmont or mainnet (default: mainnet)')
    parser.add_argument('--out-file', default='./graffiti.txt', help='out location of the generated graffiti_file')
    parser.add_argument('--update-wall-time', default=600, help='Interval between graffiti wall updates (default: 600s).')
    parser.add_argument('--update-file-time', default=30, help='Interval between graffiti file updates (default: 30s).')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('settings.ini')
    cfg = config['GraffitiConfig']
    img, x_offset, y_offset = getImage()

    white_pixels = np.all(img[:, :, :3] == [255, 255, 255], axis=-1)
    transparent_pixels = img[..., 3] == 0
    static_draw = ~(white_pixels + transparent_pixels)

    last_wall_update = 0
    last_file_update = 0
    wall = dict()
    while True:
        now = time.time()
        if last_wall_update + args.update_wall_time < now:
            getPixelWallData()
            draw_pixels = updateDrawPixels()
            last_wall_update = now
        if last_file_update + args.update_file_time < now:
            with open(args.out_file, 'w') as f:
                f.write("default: " + getPixel())
            last_file_update = now
        time.sleep(10)
