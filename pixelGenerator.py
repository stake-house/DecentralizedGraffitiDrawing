import requests
import cv2
import json
import configparser

cp = configparser.ConfigParser()
cp.read('settings.ini')
cfg = cp['rocketpool']


def getPixelWall():
    page = requests.get(cfg['GraffitiURL'])
    found = False
    wall_string = ""
    for line in page:
        if found:
            wall_string += line.decode("utf-8").split("\n")[0]
            if b'\n' in line:
                break
            continue
        if b"var pixels = [{" in line:
            found = True
            wall_string += line.decode("utf-8").split("var pixels = ", 1)[1]

    wall_filled = json.loads(wall_string)
    wall_size = 1000
    wall = [[[1, 1, 1] for x in range(wall_size)] for y in range(wall_size)]  # initialize empty, white wall

    for i in wall_filled:  # fill in pixels which have been set
        col = int(i["color"], 16)
        wall[i["y"]][i["x"]][0] = (col >> 16) & 255
        wall[i["y"]][i["x"]][1] = (col >> 8) & 255
        wall[i["y"]][i["x"]][2] = col & 255
    return wall


def getFirstPixel(wall):
    rpl_size = 300
    offset = int(500 - (rpl_size / 2))
    rpl = cv2.imread(cfg['ImagePath'])
    found = False
    for x in range(rpl_size):
        if found:
            break
        for y in range(rpl_size):
            if not (wall[x + offset][y + offset] == rpl[x][y]).all() and rpl[x][y].all() != 0:
                wall[x + offset][y + offset] = rpl[x][y] / 255.0
                color = format(int(wall[x + offset][y + offset][0] * 255), '02x')
                color += format(int(wall[x + offset][y + offset][1] * 255), '02x')
                color += format(int(wall[x + offset][y + offset][2] * 255), '02x')
                print("graffitiwall:" + str(x + offset) + ":" + str(y + offset) + ":#" + color)
                found = True
                break


if __name__ == "__main__":
    wall = getPixelWall()
    getFirstPixel(wall)
