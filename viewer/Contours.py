import cv2
import numpy as np

EdgeDetectorWindowTitle = "Contours"

# Preprocessing / Image filtering
GaussFilter_Kernel = 3

BiFilter_SigmaColor = 75
BiFilter_SigmaSpace = 75
BiFilter_BorderType = 4

# Edge detection
FillEdges = True # False means Fill between detected contours
Canny_Threshold1 = 100
Canny_Threshold2 = 100
Canny_RetrievalMode = cv2.RETR_TREE

Sobel_Aperture = 5

Scaled_Threshold = 0
Scaled_Offset_X = 0
Scaled_Offset_Y = 0

maxLevel = 2
minLevel = 0
Contour_Thickness = 1
Contour_Index = 0

fill_start = 0
fill_end = 2

Erode_Kernel = 5
Erode_Iterations = 5


filter_title  = "1: Preprocessing / Filter"
canny_title   = "2: Identify Edges"
edges_title   = "3: Select Contours"
erosion_title = "4: Erode Contours"


Shown_Windows = {
    filter_title: False,
    canny_title: False,
    edges_title: False,
    erosion_title: False,
}


bifilter_border_types = [
    cv2.BORDER_CONSTANT,
    cv2.BORDER_REPLICATE,
    cv2.BORDER_REFLECT,
    cv2.BORDER_WRAP,
    cv2.BORDER_REFLECT101,
    cv2.BORDER_ISOLATED,
]

canny_retrieval_modes = [
    cv2.RETR_CCOMP,    # 2
    cv2.RETR_EXTERNAL, # 0
    cv2.RETR_LIST,     # 1
    cv2.RETR_TREE,     # 3
]

def updateContours():
    global result_mask, img_filter, img_edges, contours, img_contours, img_erosion

    # 1. Blur image
    # Could also use Gaussian or other blur methods, but bilateral served best for now
    # res = cv2.copyMakeBorder(orig_img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=[255, 255, 255, 0])
    # blurred = cv2.GaussianBlur(orig_img[..., :3], (GaussFilter_Kernel, GaussFilter_Kernel), cv2.BORDER_DEFAULT)
    img_filter = cv2.bilateralFilter(orig_img[..., :3], 15, BiFilter_SigmaColor, BiFilter_SigmaSpace, borderType=bifilter_border_types[BiFilter_BorderType])
    
    # 2. Detect edges
    img_edges = cv2.Canny(image=img_filter, threshold1=Canny_Threshold1, threshold2=Canny_Threshold2, apertureSize=Sobel_Aperture)

    # 3. Identify contours
    contours, hierarchy = cv2.findContours(img_edges, canny_retrieval_modes[Canny_RetrievalMode], cv2.CHAIN_APPROX_NONE)  # I've had examples in which CHAIN_APPROX_SIMPLE wasn't good enough...

    # 3.1 Create contour areas
    contour_area = []
    for c in contours:
        contour_area.append((cv2.contourArea(c), c))
    # 3.2 Sort by size
    contour_area = sorted(contour_area, key=lambda x:x[0], reverse=True)

    # 4. Draw contours
    img_contours = np.full_like(orig_img, [0, 0, 0, 255])
    if len(contour_area) >= maxLevel and FillEdges:
        for i in range(minLevel, maxLevel + 1):
            coords = np.vstack([contour_area[minLevel][1], contour_area[i][1]])
            cv2.fillPoly(img_contours, [coords], (255, 255, 255))
    else:
        cv2.drawContours(img_contours, contours, Contour_Index, (255, 255, 255), thickness=Contour_Thickness, hierarchy=hierarchy, maxLevel=maxLevel)

    
    # cv2.fillPoly(orig_contours, contours)

    # 5. Erode
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (Erode_Kernel, Erode_Kernel))
    img_erosion = cv2.erode(img_contours, kernel, iterations=Erode_Iterations, borderType=cv2.BORDER_CONSTANT, borderValue=[0, 0, 0, 0])

    # 6. resize
    resized_contours = cv2.resize(img_erosion, dsize=(img.shape[1], img.shape[0]), interpolation=cv2.INTER_AREA)
    # img_erosion = cv2.erode(img_contours, kernel, iterations=1)

    contour_mask = np.where(resized_contours > Scaled_Threshold, True, False)[..., :3]
    img_contours_result = np.copy(img)
    # Ensure we don't attempt to draw invisible pixels (maybe some contour algorithm would select pixels outside of our image)
    visible = img[..., 3] != 0
    white_img = np.all(img[..., :3] == [255, 255, 255], axis=-1)
    todo_mask = np.repeat((visible & ~white_img)[..., np.newaxis], 3, axis=2)
    np.copyto(img_contours_result[..., :3], np.array([0, 0, 0], dtype=np.uint8), where=contour_mask & todo_mask)
    result_mask = np.all((contour_mask & todo_mask) == [True, True, True], axis = -1)
    cv2.imshow(EdgeDetectorWindowTitle, img_contours_result)
    updateWindows()


def toggleWindow(window):
    Shown_Windows[window] = not Shown_Windows[window]
    updateWindows()


def updateWindows():
    for window in Shown_Windows:
        if Shown_Windows[window]:
            if window == filter_title:
                img = img_filter
            if window == canny_title:
                img = img_edges
            if window == edges_title:
                img = img_contours
            if window == erosion_title:
                img = img_erosion
            cv2.imshow(window, img)
        else:
            cv2.destroyWindow(window)


def BiFilter_SigmaColor_changed(value):
    global BiFilter_SigmaColor
    BiFilter_SigmaColor = value
    updateContours()


def BiFilter_SigmaSpace_changed(value):
    global BiFilter_SigmaSpace
    BiFilter_SigmaSpace = value
    updateContours()

def BiFilter_BorderType_changed(value):
    global BiFilter_BorderType
    BiFilter_BorderType = value
    updateContours()


def GaussFilter_Kernel_changed(value):
    global GaussFilter_Kernel
    GaussFilter_Kernel = value * 2 + 1
    updateContours()


def Canny_Threshold1_changed(value):
    global Canny_Threshold1
    Canny_Threshold1 = value
    updateContours()


def Canny_Threshold2_changed(value):
    global Canny_Threshold2
    Canny_Threshold2 = value
    updateContours()


def Sobel_Aperture_changed(value):
    global Sobel_Aperture
    Sobel_Aperture = value * 2 + 1
    updateContours()


def maxLevel_changed(value):
    global maxLevel
    maxLevel = value
    updateContours()


def minLevel_changed(value):
    global minLevel
    minLevel = value
    updateContours()


def FillEdges_changed(value):
    global FillEdges
    FillEdges = bool(value)
    updateContours()


def Contour_Index_changed(value):
    global Contour_Index
    Contour_Index = value
    updateContours()


def Contour_Thickness_changed(value):
    global Contour_Thickness
    Contour_Thickness = value
    updateContours()


def Canny_RetrievalMode_changed(value):
    global Canny_RetrievalMode
    Canny_RetrievalMode = value
    updateContours()


def Erode_Kernel_changed(value):
    global Erode_Kernel
    Erode_Kernel = value * 2 + 1
    updateContours()


def Erode_Iterations_changed(value):
    global Erode_Iterations
    Erode_Iterations = value
    updateContours()


def Scaled_Threshold_changed(value):
    global Scaled_Threshold
    Scaled_Threshold = value
    updateContours()


def Scaled_Offset_X_changed(value):
    global Scaled_Offset_X
    Scaled_Offset_X = value
    updateContours()


def Scaled_Offset_Y_changed(value):
    global Scaled_Offset_Y
    Scaled_Offset_Y = value
    updateContours()


def printHelpMessage():
    print("This tool allows you to detect, select and apply contours on your image. There are a lot of parameters which can be modified using the sliders.")
    print("Operations are always applied in the same order, indicated by the leading number.")
    print("You're operating on the unscaled version of your image because there's limited efficiency doing it on pixelated images.")
    print("The end result is downscaled and projected onto your image.")
    print("\n Manuals:")
    print(" 1-4     Open a preview window of the current step. This allows you to see what's actually happening")
    print(" q, c    Exit and apply changes to current priority\n")
    print(" ESC     Exit and discard changes")


def createContoursWindow(or_img, i):
    global orig_img, img, result_mask

    print("\n\n------ Entering Contours Editor -------")
    print("Press h to show manuals.")

    orig_img = or_img
    img = i
    result_mask = np.zeros_like(img, shape=img.shape[:2], dtype=bool)
    cv2.namedWindow(EdgeDetectorWindowTitle, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(EdgeDetectorWindowTitle, 600, 800)
    # Filters
    # cv2.createTrackbar("GaussFilter Kernel", EdgeDetectorWindowTitle, int(GaussFilter_Kernel / 2), 32,  GaussFilter_Kernel_changed) # Not used
    # cv2.setTrackbarMin("GaussFilter Kernel", EdgeDetectorWindowTitle, 1)
    cv2.createTrackbar("1: BiFilter SigmaColor", EdgeDetectorWindowTitle, BiFilter_SigmaColor, 255, BiFilter_SigmaColor_changed)
    cv2.createTrackbar("1: BiFilter SigmaSpace", EdgeDetectorWindowTitle, BiFilter_SigmaSpace, 255, BiFilter_SigmaSpace_changed)
    # Edge detection
    cv2.createTrackbar("2: Canny Threshold 1", EdgeDetectorWindowTitle, Canny_Threshold1, 1000, Canny_Threshold1_changed)
    cv2.createTrackbar("2: Canny Threshold 2", EdgeDetectorWindowTitle, Canny_Threshold2, 1000, Canny_Threshold2_changed)
    cv2.createTrackbar("2: Sobel Aperture", EdgeDetectorWindowTitle, int(Sobel_Aperture / 2), 3, Sobel_Aperture_changed)
    cv2.setTrackbarMin("2: Sobel Aperture", EdgeDetectorWindowTitle, 1)
    # Edge drawing OR
    cv2.createTrackbar("3: Edges (0) or Fill (1)", EdgeDetectorWindowTitle, FillEdges, 1, FillEdges_changed)
    cv2.createTrackbar("3: Canny Retrieval Mode", EdgeDetectorWindowTitle, Canny_RetrievalMode, len(canny_retrieval_modes) - 1, Canny_RetrievalMode_changed)
    cv2.createTrackbar("3: Contour Max Depth", EdgeDetectorWindowTitle, maxLevel, 32, maxLevel_changed)
    cv2.createTrackbar("3: Contour Index", EdgeDetectorWindowTitle, Contour_Index, 32, Contour_Index_changed)
    cv2.setTrackbarMin("3: Contour Index", EdgeDetectorWindowTitle, -1)
    cv2.createTrackbar("3: Contour Thickness", EdgeDetectorWindowTitle, Contour_Thickness, 64, Contour_Thickness_changed)
    cv2.setTrackbarMin("3: Contour Thickness", EdgeDetectorWindowTitle, -1)
    # Edge filling (fill area between detected edges)
    cv2.createTrackbar("3: Contour Min Depth (Fill only)", EdgeDetectorWindowTitle, minLevel, 32, minLevel_changed)
    cv2.createTrackbar("4: Erode Kernel", EdgeDetectorWindowTitle, int(Erode_Kernel / 2), 10, Erode_Kernel_changed)
    cv2.createTrackbar("4: Erode Iterations", EdgeDetectorWindowTitle, Erode_Iterations, 16, Erode_Iterations_changed)
    cv2.createTrackbar("Scaled Threshold", EdgeDetectorWindowTitle, Scaled_Threshold, 255, Scaled_Threshold_changed)
    cv2.createTrackbar("Scale Offset X", EdgeDetectorWindowTitle, Scaled_Offset_X, 64, Scaled_Offset_X_changed)
    cv2.createTrackbar("Scale Offset Y", EdgeDetectorWindowTitle, Scaled_Offset_Y, 64, Scaled_Offset_Y_changed)
    # No effect
    # cv2.createTrackbar("BiFilter BorderType", EdgeDetectorWindowTitle, BiFilter_BorderType, len(bifilter_border_types) - 1,  BiFilter_BorderType_changed)

    updateContours()
    done = 0
    while done == 0:
        # updateContours()
        c = cv2.waitKey(1)
        if c == -1:
            continue
        k = chr(c)
        if c == 27:
            done = 1
        elif k == 'q' or k == 'c':
            done = 2
        elif k == 'h':
            printHelpMessage()
        elif k == '1':
            toggleWindow(filter_title)
        elif k == '2':
            toggleWindow(canny_title)
        elif k == '3':
            toggleWindow(edges_title)
        elif k == '4':
            toggleWindow(erosion_title)
    for i in Shown_Windows:
        if Shown_Windows[i]:
            Shown_Windows[i] = False
    cv2.destroyAllWindows()
    if done == 1:
        return None
    elif done == 2:
        return result_mask
