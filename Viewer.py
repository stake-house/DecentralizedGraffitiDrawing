import os
import requests
import cv2
import json
import configparser
import numpy as np


def getPixelWallData():
    if cfg['network'] == "mainnet":
        url = "https://beaconcha.in/graffitiwall"
    elif cfg['network'] == "pyrmont":
        url = "https://pyrmont.beaconcha.in/graffitiwall"
    else:
        print("wrong network!")
        return
    try:
        page = requests.get(url)
    except requests.exceptions.RequestException as _:
        print("[getPixelWallData] Can't reach graffitiwall")
        return
    wall_string = "[]"
    if "var pixels = [{" in page.text:
        wall_string = page.text.split("var pixels = ", 1)[1].split("\n")[0]
    return json.loads(wall_string)


def saveSettings():
    if cfg['xres'] == 'original':
        config['GraffitiConfig']['xres'] = 'original'
    else:
        config['GraffitiConfig']['xres'] = str(x_res)
    if cfg['yres'] == 'original':
        config['GraffitiConfig']['yres'] = 'original'
    else:
        config['GraffitiConfig']['yres'] = str(y_res)
    config['GraffitiConfig']['scale'] = str(scale)
    config['GraffitiConfig']['xoffset'] = str(x_offset)
    config['GraffitiConfig']['yoffset'] = str(y_offset)
    config['GraffitiConfig']['overpaint'] = str(overpaint)
    config['GraffitiConfig']['interpolation'] = str(int_mode)
    with open('settings.ini', 'w') as cfgfile:
        config.write(cfgfile)
    print('saved')


def paintWall():
    for pixel in wall_data:
        new_pixel = tuple(int(pixel["color"][i:i + 2], 16) for i in (4, 2, 0))  # opencv wants pixels in BGR
        wall[pixel["y"]][pixel["x"]] = new_pixel


def paintImage():
    global wall, img, count
    if hide:
        return
    visible = img[..., 3] != 0
    wall_part = wall[y_offset: y_offset + y_res, x_offset: x_offset + x_res]
    # This looks too complicated. If you know how to do this better, feel free to improve
    same = np.all(img[..., :3] == wall_part, axis=-1)
    need_to_set = ~(same + ~visible)
    count = np.sum(need_to_set)

    mask2 = np.repeat(need_to_set[..., np.newaxis], 3, axis=2)
    if not progressFilterEnabled:
        np.copyto(wall_part, img[..., :3], where=mask2)
    else:
        np.copyto(wall_part, np.array([0, 0, 255], dtype=np.uint8), where=mask2)
        need_to_not_set = ~(~same + ~visible)
        mask3 = np.repeat(need_to_not_set[..., np.newaxis], 3, axis=2)
        # this now includes white pixels if they're visible (alpha > 0)
        # depending on your input image the output may looks unexpected, but should be correct
        np.copyto(wall_part, np.array([0, 255, 0], dtype=np.uint8), where=mask3)


def getPixelInfo(x, y):
    # very inefficient, #TODO transform wall_data into map or something
    for pixel in wall_data:
        if pixel['y'] == y and pixel['x'] == x:
            info = ""
            info += "x: " + str(x) + "\n"
            info += "y: " + str(y) + "\n"
            info += "RGB: " + pixel['color'] + "\n"
            info += "validator: " + str(pixel['validator']) + "\n"
            info += "slot: " + str(pixel['slot']) + "\n"
            return info
    return ""


def repaint():
    global wall, wall2
    wall = np.full((1000, 1000, 3), 255, np.uint8)
    if not overpaint and not progressFilterEnabled:
        paintImage()
        paintWall()
    else:
        paintWall()
        paintImage()
    wall2 = wall.copy()


def changeSize(scale_percent=0):
    global x_res, y_res, img, scale

    width = int(x_res * (100 + scale_percent) / 100)
    height = int(y_res * (100 + scale_percent) / 100)

    if width + x_offset > 1000 or \
            height + y_offset > 1000:
        # seems like one border reached, we don't want to change aspect ratio
        return
    x_res = width
    y_res = height
    scale += int(scale_percent * scale / 100)
    img = cv2.resize(orig_img, dsize=(x_res, y_res), interpolation=interpolation_modes[int_mode])
    repaint()


def nextInterpolationMode():
    global int_mode
    found = False
    int_before = int_mode
    for key in interpolation_modes.keys():
        if found:
            int_mode = key
            break
        found = key == int_mode
    if int_before == int_mode:
        int_mode = next(iter(interpolation_modes))
    changeSize()


def changePos(x=0, y=0):
    global x_offset, y_offset
    x_offset = max(0, min(x_offset + x, 1000 - x_res))
    y_offset = max(0, min(y_offset + y, 1000 - y_res))
    repaint()


def toggleOverpaint():
    global overpaint
    overpaint = not overpaint
    repaint()


def toggleHide():
    global hide
    hide = not hide
    repaint()


def toggleProgressFilter():
    global progressFilterEnabled
    progressFilterEnabled = not progressFilterEnabled
    repaint()


def draw_label(text, pos):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    s = 0.4
    color = (0, 0, 0)  # black
    thickness = cv2.FILLED
    txt_size = cv2.getTextSize(text, font_face, s, thickness)

    for i, line in enumerate(text.split('\n')):
        y2 = pos[1] + i * (txt_size[0][1] + 4)
        cv2.putText(wall2, line, (pos[0], y2), font_face, s, color, 1, 2)


def onMouseEvent(event, x, y, flags, param):
    global wall2
    if event == cv2.EVENT_MOUSEMOVE:
        wall2 = wall.copy()
        pixel_string = getPixelInfo(x, y)
        if pixel_string != "":
            draw_label(pixel_string, (x, y))


def eth2addresses():
    eth2_addresses = set()
    for pixel in wall_data:
        x = pixel["x"]
        y = pixel["y"]
        # 1. is near our image
        if x_offset <= x <= x_offset + x_res and \
                y_offset <= y <= y_offset + y_res:
            if np.all(tuple(int(pixel["color"][i:i + 2], 16) for i in (4, 2, 0)) == wall[y, x]):
                eth2_addresses.add(str(pixel["validator"]))
    return eth2_addresses


def eth1addresses():
    if cfg['network'] == "mainnet":
        url = "https://beaconcha.in/api/v1/validator/"
    elif cfg['network'] == "pyrmont":
        url = "https://pyrmont.beaconcha.in/api/v1/validator/"
    else:
        print("wrong network!")
        return
    validators = ','.join(eth2addresses())
    try:
        page = requests.get(url + validators + "/deposits")
    except requests.exceptions.RequestException as _:
        print("can't reach graffitiwall")
        return ""
    eth1_addresses = set()
    for validator in page.json()["data"]:
        eth1_addresses.add(validator["from_address"])
    return eth1_addresses


def show(title):
    global count
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(title, onMouseEvent)
    done = False
    while not done:
        cv2.imshow(title, wall2)
        c = cv2.waitKey(1)
        if c == -1:
            continue
        k = chr(c)
        if k == '+':
            changeSize(10)
        elif k == '-':
            changeSize(-10)
        elif k == 'w':
            changePos(0, -10)
        elif k == 'a':
            changePos(-10, 0)
        elif k == 's':
            changePos(0, 10)
        elif k == 'd':
            changePos(10, 0)
        elif k == 'o':
            toggleOverpaint()
        elif k == 'h':
            toggleHide()
        elif k == 'p':
            toggleProgressFilter()
        elif k == 'i':
            nextInterpolationMode()
        elif k == 'c':
            print("Need to draw " + str(count) + " Pixels currently.")
        elif k == '1':
            print("\n\n --- Participating eth1 addresses: ")
            for add in eth1addresses():
                print(add)
        elif k == '2':
            print("\n\n --- Participating validators: ")
            for add in eth2addresses():
                print(add)
        elif k == 'f':  # c == 19 to ctrl + s, but for qt backend only ?
            saveSettings()
        elif k == 'q' or c == 27:  # esc-key
            done = True
    cv2.destroyAllWindows()


interpolation_modes = {
    "near": cv2.INTER_NEAREST,
    "lin": cv2.INTER_LINEAR,
    "cube": cv2.INTER_CUBIC,
    "area": cv2.INTER_AREA,
    "lanc4": cv2.INTER_LANCZOS4,
    "lin_ex": cv2.INTER_LINEAR_EXACT,
}

if __name__ == "__main__":
    config = configparser.ConfigParser(inline_comment_prefixes=('#',))
    config.read('settings.ini')
    cfg = config['GraffitiConfig']
    file = cfg['ImagePath']
    if not os.path.isabs(file):
        file = os.path.dirname(os.path.abspath(__file__)) + "/" + file
    orig_img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    y_res, x_res, channels = orig_img.shape
    scale = int(cfg['scale'])
    x_res = int(x_res * (scale / 100))
    y_res = int(y_res * (scale / 100))
    # absolute resolution is preffered over relative (= scale is ignored if x/y_res is set)
    if cfg['XRes'] != "original":
        x_res = int(cfg['XRes'])
    if cfg['YRes'] != "original":
        y_res = int(cfg['YRes'])
    img = orig_img
    x_offset = min(1000 - x_res, int(cfg['XOffset']))
    y_offset = min(1000 - y_res, int(cfg['YOffset']))
    overpaint = cfg.getboolean('OverPaint')
    wall_data = getPixelWallData()
    hide = False
    progressFilterEnabled = False
    int_mode = cfg["interpolation"]
    if int_mode not in interpolation_modes:
        print("unknown interpolation mode: " + cfg["interpolation"])
        exit(1)

    changeSize()
    show("Beaconcha.in Graffitiwall (" + cfg['network'] + ")")
