import requests
import cv2
import json
import configparser
import numpy as np

cp = configparser.ConfigParser()
cp.read('settings.ini')
cfg = cp['rocketpool']
rpl = cv2.imread(cfg['ImagePath'])
x_offset = int(cfg['XOffset'])
y_offset = int(cfg['YOffset'])
overpaint = cfg.getboolean('OverPaint')


def getPixelWall(x, y, width=1000, height=1000):
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
    wall = np.full((height, width, 3), 255, np.uint8)

    for pixel in wall_filled:  # fill in pixels which have been set
        col = int(pixel["color"], 16)
        wall[pixel["y"]][pixel["x"]][2] = (col >> 16) & 255
        wall[pixel["y"]][pixel["x"]][1] = (col >> 8) & 255
        wall[pixel["y"]][pixel["x"]][0] = col & 255
    return wall


def getFirstPixel(wall):
    rpl_size = 300
    found = False
    for y in range(rpl_size):
        if found:
            break
        for x in range(rpl_size):
            if not np.all((wall[x + x_offset][y + y_offset] == rpl[x][y])) and np.all((rpl[x][y] > 5)):
                # wall[x + offset][y + offset] = rpl[x][y]
                color = format(rpl[x][y][2], '02x')
                color += format(rpl[x][y][1], '02x')
                color += format(rpl[x][y][0], '02x')
                print("graffitiwall:" + str(x + x_offset) + ":" + str(y + y_offset) + ":#" + color)
                found = True
                break


def modify():
    rpl_size = 300
    count = 0
    for y in range(rpl_size):
        for x in range(rpl_size):
            if (not np.all(wall[y + y_offset][x + x_offset] == rpl[y][x])) and np.all((rpl[y][x] > 5)):
                if (not np.all(wall[y + y_offset][x + x_offset] == 255)) and not overpaint:
                    continue
                count += 1
                wall[y + y_offset][x + x_offset] = rpl[y][x]
    print(str(count) + " todo!")


def show(img, title):
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.imshow(title, img)


if __name__ == "__main__":
    wall = getPixelWall(x_offset, y_offset, 300, 300)
    #show(wall, "before")
    getFirstPixel(wall)
    modify()
    #show(wall, "after")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
