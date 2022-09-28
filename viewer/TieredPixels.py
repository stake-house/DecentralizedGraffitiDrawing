import cv2
import numpy as np

title = "Manage Pixel Drawing Order"
current_layer = 0
colors = [
    [255,   0,   0, 255],
    [  0, 255,   0, 255],
    [  0,   0, 255, 255],
    [255, 255,   0, 255],
    [255,   0, 255, 255],
    [  0, 255, 255, 255],
]

drawing = False
mouse_x, mouse_y = 0, 0


def isCursorOutside():
    return mouse_x < 0 or mouse_x > orig_img.shape[0] - 1 or \
           mouse_y < 0 or mouse_y > orig_img.shape[1] - 1


def setColorAtCursor(color):
    global shown_img
    shown_img[mouse_y, mouse_x] = color


def isPixelUsed(x, y) -> bool:
    for i in range(len(colors)):
        if i == current_layer:
            continue
        if layers[y, x] > -1:
            return True
    return False


def onMouseEvent(event, x, y, flags, param):
    global shown_img, drawing, edited_img, mouse_x, mouse_y, layers
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        if erase:
            shown_img[y, x] = orig_img[y, x]
            layers[y, x] = -1
    elif event == cv2.EVENT_LBUTTONUP:
        if drawing:
            drawing = False
            edited_img = shown_img.copy()
    elif event == cv2.EVENT_RBUTTONDOWN:
        if drawing:
            drawing = False
            shown_img = edited_img.copy()

    
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x = x
        mouse_y = y
        if isCursorOutside():
            return
        if shown_img[y, x, 3] > 0:
            color = colors[current_layer]
            if not erase and isPixelUsed(x, y):
                return
            if not drawing:
                shown_img = edited_img.copy()
                if erase:
                    color = [128, 128, 128, 0]
            elif erase:
                color = orig_img[y, x]
                layers[y, x] = -1
            else:
                layers[y, x] = current_layer
            setColorAtCursor(color)


def createPixelOrderWindow(in_img):
    global orig_img, shown_img, edited_img, erase, current_layer, layers
    orig_img = in_img
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(title, 600, 800)
    cv2.setMouseCallback(title, onMouseEvent)
    edited_img = orig_img.copy()
    shown_img = edited_img.copy()
    layers = np.full_like(orig_img, -1, shape=(orig_img.shape[1], orig_img.shape[0]), dtype=np.int8)

    done = False
    erase = False
    current_layer = 0
    while not done:
        c = cv2.waitKey(1)
        cv2.imshow(title, shown_img)
        if c == -1:
            continue
        k = chr(c)
        if k == 'q':
            done = True
        elif k == '+':
            if current_layer < len(colors) - 1:
                current_layer += 1
        elif k == '-':
            if current_layer > 0:
                current_layer -= 1
        elif k == 'e':
            erase = not erase
            if isCursorOutside():
                continue
            if erase:
                setColorAtCursor([128, 128, 128, 255])
            else:
                setColorAtCursor(colors[current_layer])
    cv2.destroyWindow(title)