import requests
import cv2
import json
import configparser
import numpy as np
import time
import math

# initialize settings
cp = configparser.ConfigParser()
cp.read('settings.ini')
cfg = cp['rocketpool']
orig = cv2.imread(cfg['ImagePath'])
rpl = orig
x_res, y_res, _ = rpl.shape
x_offset = int(cfg['XOffset'])
y_offset = int(cfg['YOffset'])
overpaint = cfg.getboolean('OverPaint')


def getPixelWall():
    page = requests.get(cfg['GraffitiURL'])
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

    wall_filled = json.loads(wall_string)
    wall = np.full((1000, 1000, 3), 255, np.uint8)

    for pixel in wall_filled:  # fill in pixels which have been set
        col = int(pixel["color"], 16)
        wall[pixel["y"]][pixel["x"]][2] = (col >> 16) & 255
        wall[pixel["y"]][pixel["x"]][1] = (col >> 8) & 255
        wall[pixel["y"]][pixel["x"]][0] = col & 255
    return wall


orig_wall = getPixelWall()


def update():
    global wall
    wall = orig_wall.copy()
    r = rpl[max(0, -1 * y_offset): 1000 - y_offset, max(0, -1 * x_offset): 1000 - x_offset]
    w = wall[max(0, y_offset):y_offset + y_res, max(0, x_offset):x_res + x_offset]

    #non_white_pixels_mask = np.any(w != [255, 255, 255], axis=-1)
    #wall[non_white_pixels_mask] = wall[...,:]
    #rpl[non_white_pixels_mask] = [255, 255, 255]

    t = np.where(w == [255])
    print(t)
    #test = np.where(overpaint or np.argwhere(w == 255), r, w)
    wall[max(0, y_offset):y_offset + y_res, max(0, x_offset):x_res + x_offset] = np.all(
        overpaint or w == [255, 255, 255], r, w)
    #wall[max(0, y_offset):y_offset + y_res, max(0, x_offset):x_res + x_offset] = np.where(
    #    overpaint or w == [255, 255, 255], r, w)


def changeSize(x = 0, y = 0):
    global x_res, y_res, rpl
    x_res += x
    y_res += y
    rpl = cv2.resize(orig, dsize=(x_res, y_res), interpolation=cv2.INTER_CUBIC)
    update()


def changePos(x = 0, y = 0):
    global x_offset, y_offset
    x_offset = x_offset + x
    #if x_offset < -1000:
    #    x_offset += 2000
    #if x_offset > 1000:
    #    x_offset -= 2000
    x_offset = (x_offset + x) % 1000
    y_offset = (y_offset + y) % 1000
    update()


def toggleOverpaint():
    global overpaint
    overpaint = not overpaint
    update()


def reset():
    global wall
    wall = orig_wall


def load():
    update()


def show(title):
    global wall
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
        elif k == 'r':
            reset()
        elif k == 'l':
            load()
        elif k == 't':
            print("test")
        elif k == 'q':
            done = True
        elif c == 27:
            done = True
    cv2.destroyAllWindows()


if __name__ == "__main__":
    update()
    show("wall")
