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

    return json.loads(wall_string)


def saveSettings():
    config['GraffitiConfig']['xres'] = str(x_res)
    config['GraffitiConfig']['yres'] = str(y_res)
    config['GraffitiConfig']['xoffset'] = str(x_offset)
    config['GraffitiConfig']['yoffset'] = str(y_offset)
    config['GraffitiConfig']['overpaint'] = str(overpaint)
    config['GraffitiConfig']['interpolation'] = str(int_mode)
    with open('settings.ini', 'w') as cfgfile:
        config.write(cfgfile)
    print('saved')


def paintWall():
    for pixel in wall_data:
        new_pixel = tuple(int(pixel["color"][i:i+2], 16) for i in (4, 2, 0))    # opencv wants pixels in BGR
        wall[pixel["y"]][pixel["x"]] = new_pixel


def paintImage():
    global wall, img, count
    if hide:
        return
    mask = img[..., 3] != 0
    wall_part = wall[y_offset: y_offset + y_res, x_offset: x_offset + x_res]
    # This looks too complicated. If you know how to do this better, feel free to improve
    same = np.all(img[..., :3] == wall_part, axis=-1)
    need_to_set = ~(same + ~mask)
    count = np.sum(need_to_set)

    mask2 = np.repeat(mask[..., np.newaxis], 3, axis=2)
    np.copyto(wall_part, img[..., :3], where=mask2)


def repaint():
    global wall
    wall = orig_wall.copy()
    if (overpaint):
        paintWall()
        paintImage()
    else:
        paintImage()
        paintWall()


def changeSize(x = 0, y = 0):
    global x_res, y_res, img

    x_new = max(1, min(x_res + x, 1000 - x_offset))
    y_new = max(1, min(y_res + y, 1000 - y_offset))
    if x_res - y_res != x_new - y_new:
        # seems like one border reached, we don't want to change aspect ratio
        return
    x_res = x_new
    y_res = y_new
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


def changePos(x = 0, y = 0):
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


def show(title):
    global count
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    done = False
    while not done:
        cv2.imshow(title, wall)
        c = cv2.waitKey(1)
        if c == -1:
            continue
        k = chr(c)
        if k == '+':
            changeSize(10, 10)
        elif k == '-':
            changeSize(-10, -10)
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
        elif k == 'i':
            nextInterpolationMode()
        elif k == 'c':
            print("Need to draw " + str(count) + " Pixels currently.")
        elif k == 'f':  # c == 19 to ctrl + s, but for qt backend only ?
            saveSettings()
        elif k == 'q' or c == 27:   # esc-key
            done = True
    cv2.destroyAllWindows()


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


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('settings.ini')
    cfg = config['GraffitiConfig']
    orig_img = cv2.imread(cfg['ImagePath'], cv2.IMREAD_UNCHANGED)
    x_res = int(cfg['XRes'])
    y_res = int(cfg['YRes'])
    _, _, channels = orig_img.shape
    img = orig_img
    x_offset = min(1000 - x_res, int(cfg['XOffset']))
    y_offset = min(1000 - y_res, int(cfg['YOffset']))
    overpaint = cfg.getboolean('OverPaint')
    wall_data = getPixelWallData()
    orig_wall = np.full((1000, 1000, 3), 255, np.uint8)
    hide = False
    int_mode = cfg["interpolation"]
    if int_mode not in interpolation_modes:
        print("unknown interpolation mode: " + cfg["interpolation"])
        exit(1)

    changeSize()
    show("Beaconcha.in Graffitiwall (" + cfg['network'] + ")")
