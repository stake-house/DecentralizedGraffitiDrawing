from examples import getPixel

if __name__ == "__main__":
    # 1. init
    getPixel.init("../settings.ini")
    while True:
        # 2. Update pixels left to draw (pull wall, perform calculations;
        # heavy operation, do at larger intervals,  like 10+ min)
        getPixel.getPixelWallData()
        # 3. return random pixel (very cheap)
        print(getPixel.getPixel())
