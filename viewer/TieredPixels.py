import cv2
import numpy as np

from Contours import createContoursWindow

title = "Manage Pixel Drawing Order"
colors = [
    [255,   0,   0],
    [  0, 255,   0],
    [  0,   0, 255],
    [255, 255,   0],
    [255,   0, 255],
    [  0, 255, 255],
]

cursors = [
    np.array([
        [1]
    ], dtype=bool),
    np.array([
        [1,1],
        [1,1]
    ], dtype=bool),
    np.array([
        [0,1,0],
        [1,1,1],
        [0,1,0],
    ], dtype=bool),
    np.array([
        [1,1,1],
        [1,1,1],
        [1,1,1],
    ], dtype=bool),
    np.array([
        [0,0,1,0,0],
        [0,1,1,1,0],
        [1,1,1,1,1],
        [0,1,1,1,0],
        [0,0,1,0,0],
    ], dtype=bool),
    np.array([
        [1,1,1,1],
        [1,1,1,1],
        [1,1,1,1],
        [1,1,1,1],
    ], dtype=bool),
    np.array([
        [0,0,1,1,0,0],
        [0,1,1,1,1,0],
        [1,1,1,1,1,1],
        [1,1,1,1,1,1],
        [0,1,1,1,1,0],
        [0,0,1,1,0,0],
    ], dtype=bool),
]



def isCursorOutside():
    return mouse_x < 0 or mouse_x > orig_img.shape[0] - 1 or \
           mouse_y < 0 or mouse_y > orig_img.shape[1] - 1


def setColorAtCursor():
    # TODO improve this the numpy way, there's too much copy paste
    global shown_img
    if hidden:
        return
    if not drawing:
        shown_img = edited_img.copy()
    cursor = cursors[current_cursor]
    cursor_copy = cursor.copy()

    h_h = int(cursor.shape[0] / 2)
    h_w = int(cursor.shape[1] / 2)
    min_y = mouse_y - h_h
    min_x = mouse_x - h_w
    max_y = mouse_y + h_h + cursor.shape[1] % 2
    max_x = mouse_x + h_w + cursor.shape[0] % 2

    cursor_section = shown_img[
        max(min_y, 0) : max(mouse_y + h_h + cursor.shape[0] % 2, 0),
        max(min_x, 0) : max(mouse_x + h_w + cursor.shape[1] % 2, 0)
    ]
    layers_section = layers[
        max(min_y, 0) : max(mouse_y + h_h + cursor.shape[0] % 2, 0),
        max(min_x, 0) : max(mouse_x + h_w + cursor.shape[1] % 2, 0)
    ]
    not_used = (layers_section == -1) | (layers_section == current_layer)
    if min_x < 0:
        cursor_copy = cursor_copy[:, abs(min_x):]
    if min_y < 0:
        cursor_copy = cursor_copy[abs(min_y):, :]
    if max_x > orig_img.shape[1]:
        m = orig_img.shape[1] - max_x
        cursor_copy = cursor_copy[:, :m]
    if max_y > orig_img.shape[0]:
        m = orig_img.shape[0] - max_y
        cursor_copy = cursor_copy[:m, :]
    visible = cursor_section[..., 3] > 0
    l = current_layer
    if erase:
        colorized = visible & cursor_copy
        if drawing:
            orig = orig_img[
                max(min_y, 0) : max(mouse_y + h_h + cursor.shape[0] % 2, 0),
                max(min_x, 0) : max(mouse_x + h_w + cursor.shape[1] % 2, 0)
            ]
            np.copyto(cursor_section[..., :3], orig[..., :3],
                where=np.repeat(colorized[..., np.newaxis], 3, axis=-1))
            l = -1
        else:
            np.copyto(cursor_section[..., :3], np.array([128, 128, 128], dtype=np.uint8),
                where=np.repeat(colorized[..., np.newaxis], 3, axis=-1))
    else:
        colorized = visible & cursor_copy & not_used
        np.copyto(cursor_section[..., :3], np.array(colors[current_layer], dtype=np.uint8),
            where=np.repeat(colorized[..., np.newaxis], 3, axis=-1))
    if drawing:
        np.copyto(layers_section, l, where=colorized)


def isPixelUsed(x, y) -> bool:
    return layers[y, x] != -1 and layers[y, x] != current_layer


def onMouseEvent(event, x, y, flags, param):
    global shown_img, drawing, edited_img, mouse_x, mouse_y, layers
    mouse_x = x
    mouse_y = y - 9
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        setColorAtCursor()
    elif event == cv2.EVENT_LBUTTONUP or \
         event == cv2.EVENT_RBUTTONDOWN:
        if drawing:
            drawing = False
            edited_img = shown_img.copy()
            setColorAtCursor()

    if event == cv2.EVENT_MOUSEMOVE:
        setColorAtCursor()


def toggleErase():
    global erase
    if drawing:
        return
    erase = not erase
    if isCursorOutside():
        return
    setColorAtCursor()


def toggleBackgroundColor():
    global edited_img, shown_img, background_inverted
    background = orig_img[..., 3] == 0
    background_inverted = not background_inverted
    if background_inverted:
        bg_color = [0, 0, 0]
    else:
        bg_color = [255, 255, 255]
    np.copyto(edited_img[..., :3], np.array(bg_color, dtype=np.uint8), where=np.repeat(background[..., np.newaxis], 3, axis=-1))
    shown_img = edited_img.copy()


def toggleHideColors():
    global hidden, shown_img
    hidden = not hidden
    if hidden:
        shown_img = orig_img
    else:
        applyLayers()


def applyLayers():
    global edited_img, shown_img
    for i in range(len(colors)):
        color_mask = layers == i
        color_mask = np.repeat(color_mask[..., np.newaxis], 3, axis = -1)
        np.copyto(edited_img[..., :3], np.array(colors[i], dtype=np.uint8), where=color_mask)
    shown_img = edited_img.copy()
    setColorAtCursor()


def addHeader():
    res = cv2.copyMakeBorder(shown_img, 9, 0, 0, 0, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    s = 0.3
    color = [255, 255, 255] 
    # thickness = cv2.FILLED
    pos = [0, 7]
    txt_size = int(orig_img.shape[1] / 6) # cv2.getTextSize(text, font_face, s, thickness)
    for i in range(len(colors)):
        text = str(i + 1)
        res[:9, pos[0]:pos[0] + txt_size, :3] = colors[i]
        cv2.putText(res, text, pos, font_face, s, color, 1, 2)
        pos[0] += txt_size
    return res


def resetCursor():
    global mouse_x, mouse_y
    mouse_x, mouse_y = 0, 0


def createPixelOrderWindow(in_img, layers_in, unscaled):
    global orig_img, shown_img, edited_img, erase, current_layer, layers, current_cursor, hidden, background_inverted, drawing
    orig_img = in_img
    layers = layers_in
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(title, 600, 800)
    cv2.setMouseCallback(title, onMouseEvent)
    edited_img = orig_img.copy()

    done = False
    erase = False
    hidden = False
    background_inverted = False
    drawing = False
    current_layer = 0
    current_cursor = 0
    resetCursor()
    applyLayers()
    while not done:
        c = cv2.waitKey(1)
        cv2.imshow(title, addHeader())
        if c == -1:
            continue
        k = chr(c)
        if k == 'q' or k == 't':
            done = True
        elif c > 48 and c < 55:
            if drawing:
                continue
            current_layer = int(k) - 1
            if erase:
                toggleErase()
            else:
                setColorAtCursor()
        elif k == '+':
            if current_cursor < len(cursors) - 1:
                current_cursor += 1
                setColorAtCursor()
        elif k == '-':
            if current_cursor > 0:
                current_cursor -= 1
                setColorAtCursor()
        elif k == 'e':
            toggleErase()
        elif k == 'b':
            toggleBackgroundColor()
        elif k == 'v':
            toggleHideColors()
        elif k == 'c':
            cv2.destroyWindow(title)
            contours = createContoursWindow(unscaled, orig_img)
            np.copyto(layers, current_layer, where=contours)
            applyLayers()
            cv2.namedWindow(title, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(title, 600, 800)
            resetCursor()
            cv2.setMouseCallback(title, onMouseEvent)
    cv2.destroyWindow(title)
    return layers
