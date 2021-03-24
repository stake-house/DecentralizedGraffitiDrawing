import configparser
import os
import cv2
import numpy as np
import requests

interpolation_modes = {
    "near": cv2.INTER_NEAREST,
    "lin": cv2.INTER_LINEAR,
    "cube": cv2.INTER_CUBIC,
    "area": cv2.INTER_AREA,
    "lanc4": cv2.INTER_LANCZOS4,
    "lin_ex": cv2.INTER_LINEAR_EXACT,
}

cfg = None
white_pixels = None
static_draw = None
transparent_pixels = None
draw_pixels = None
img = None
x_offset = None
y_offset = None


def init(config_file):
    global cfg, img, x_offset, y_offset, static_draw, transparent_pixels
    config = configparser.ConfigParser()
    config.read(config_file)
    cfg = config['GraffitiConfig']
    x_res = int(cfg['XRes'])
    y_res = int(cfg['YRes'])
    file = cfg['ImagePath']
    if not os.path.isabs(file):
        file = os.path.dirname(os.path.abspath(config_file)) + "/" + os.path.basename(file)
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
    x_offset = min(1000 - x_res, int(cfg['XOffset']))
    y_offset = min(1000 - y_res, int(cfg['YOffset']))
    white_pixels = np.all(img[:, :, :3] == [255, 255, 255], axis=-1)
    transparent_pixels = img[..., 3] == 0
    static_draw = ~(white_pixels + transparent_pixels)


def getPixelWallData():
    global draw_pixels
    if cfg['network'] == "mainnet":
        url = "https://beaconcha.in/api/v1/graffitiwall"
    elif cfg['network'] == "pyrmont":
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
    overdraw = np.full_like(white_pixels, False)
    for pixel in w:
        if y_offset <= pixel["y"] < y_offset + int(cfg['YRes']) and \
                x_offset <= pixel["x"] < x_offset + int(cfg['XRes']):
            col = tuple(int(pixel["color"][i:i+2], 16) for i in (0, 2, 4))
            wall[pixel["y"] - y_offset, pixel["x"] - x_offset] = col
            overdraw[pixel["y"], pixel["x"]] = np.any(img[pixel["y"], pixel["x"], :3] != col)
    draw_pixels = static_draw + (~transparent_pixels * overdraw)


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

