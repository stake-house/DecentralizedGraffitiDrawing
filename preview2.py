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


def paintWall():
    global count
    count = 0
    for pixel in wall_data:
        new_pixel = tuple(int(pixel["color"][i:i+2], 16) for i in (4, 2, 0))
        if np.any(wall[pixel["y"]][pixel["x"]] != new_pixel) and np.any(wall[pixel["y"]][pixel["x"]] != 255):
            count += 1
        wall[pixel["y"]][pixel["x"]] = new_pixel


def paintImage():
    global wall, img
    if hide:
        return
    #o = np.sum(img[..., 3] != 255)
    #print(o)

    mask = img[..., 3] != 0

    w = wall[y_offset: y_offset + y_res, x_offset: x_offset + x_res]

    #mask2 = np.array([[[x, x, x] for x in y] for y in mask])
    mask2 = np.repeat(mask[..., np.newaxis], 3, axis=2)
    np.copyto(w, img[..., :3], where=mask2)

    #cv2.imshow("test", w)
    #cv2.waitKey(0)

    #alpha = img[..., 3] / 255.0
    #alpha2 = np.array([[[x, x, x] for x in y] for y in alpha])

    #foreground = cv2.multiply(alpha2, img[..., :3].astype(float)).astype(np.uint8)
    #background = cv2.multiply(1.0 - alpha2, wall[y_offset: y_offset + y_res, x_offset: x_offset + x_res].astype(float)).astype(np.uint8)

    #out = cv2.add(foreground, background)
    #wall[y_offset: y_offset + y_res, x_offset: x_offset + x_res] = out


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
    if cfg["interpolation"] not in interpolation_modes:
        print ("unknown interpolation mode: " + cfg["interpolation"])
        return
    img = cv2.resize(orig_img, dsize=(x_res, y_res), interpolation=interpolation_modes[cfg["interpolation"]])
    repaint()


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
        if (c == -1):
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
        elif k == 'c':
            print("Need to draw " + str(count) + " Pixels currently.")
        elif k == 'q':
            done = True
        elif c == 27:
            done = True
    cv2.destroyAllWindows()


interpolation_modes = {
    "lanc": cv2.INTER_LANCZOS4,
    "area": cv2.INTER_AREA,
    "cube": cv2.INTER_CUBIC,
    "near": cv2.INTER_NEAREST,
    "bits": cv2.INTER_BITS,
    "lin": cv2.INTER_LINEAR,
     }

if __name__ == "__main__":
    cp = configparser.ConfigParser()
    cp.read('settings.ini')
    cfg = cp['GraffitiConfig']
    orig_img = cv2.imread(cfg['ImagePath'], cv2.IMREAD_UNCHANGED)
    x_res, y_res, channels = orig_img.shape
    #if channels == 4:
        # set hidden pixels to white
        #orig_img[orig_img[:, :, 3] == 0] = 0
    img = orig_img
    x_offset = min(1000 - x_res, int(cfg['XOffset']))
    y_offset = min(1000 - y_res, int(cfg['YOffset']))
    overpaint = cfg.getboolean('OverPaint')
    wall_data = getPixelWallData()
    orig_wall = np.full((1000, 1000, 3), 255, np.uint8)
    hide = False

    repaint()
    show("Beaconcha.in Graffitiwall (" + cfg['network'] + ")")
