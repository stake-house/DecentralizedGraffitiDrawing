import cv2
import numpy as np

EdgeDetectorWindowTitle = "Edge Detection"

BiFilter_SigmaColor = 75
BiFilter_SigmaSpace = 75
BiFilter_BorderType = 4

Canny_Threshold1 = 100
Canny_Threshold2 = 100
Canny_RetrievalMode = 1

Scaled_Threshold = 0

Contour_Thickness = 1


bifilter_border_types = [
    cv2.BORDER_CONSTANT,
    cv2.BORDER_REPLICATE,
    cv2.BORDER_REFLECT,
    cv2.BORDER_WRAP,
    cv2.BORDER_REFLECT101,
    cv2.BORDER_ISOLATED,
]

canny_retrieval_modes = [
    cv2.RETR_CCOMP,
    cv2.RETR_EXTERNAL,
    cv2.RETR_LIST,
    cv2.RETR_TREE,
]


def updateContours():
    # 1. Blur image
    # Could also use Gaussian or other blur methods, but bilateral served best for now
    blurred = cv2.bilateralFilter(orig_img[..., :3], 15, BiFilter_SigmaColor, BiFilter_SigmaSpace, borderType=bifilter_border_types[BiFilter_BorderType])
    
    # 2. Detect edges
    # Could also use Sobel edge detection algorithm
    canny = cv2.Canny(image=blurred, threshold1=Canny_Threshold1, threshold2=Canny_Threshold2)

    # 3. Identify contours
    contours, _ = cv2.findContours(canny, canny_retrieval_modes[Canny_RetrievalMode], cv2.CHAIN_APPROX_SIMPLE)

    # 4. Draw, scale and show contours
    orig_contours = np.full_like(orig_img, [0, 0, 0, 255])
    cv2.drawContours(orig_contours, contours, -1, (255, 255, 255), thickness=Contour_Thickness)
    img_contours = cv2.resize(orig_contours, dsize=(img.shape[1], img.shape[0]), interpolation=cv2.INTER_AREA)
    contour_mask = np.where(img_contours > Scaled_Threshold, True, False)[..., :3]
    img_contours_result = np.copy(img)
    # Ensure we don't attempt to draw invisible pixels (maybe some contour algorithm would select pixels outside of our image)
    visible = img[..., 3] != 0
    white_img = np.all(img[..., :3] == [255, 255, 255], axis=-1)
    todo_mask = np.repeat((visible & ~white_img)[..., np.newaxis], 3, axis=2)
    np.copyto(img_contours_result[..., :3], np.array([0, 0, 0], dtype=np.uint8), where=contour_mask & todo_mask)
    cv2.imshow(EdgeDetectorWindowTitle, img_contours_result)


def Canny_Threshold1_changed(value):
    global Canny_Threshold1
    Canny_Threshold1 = value
    updateContours()


def Canny_Threshold2_changed(value):
    global Canny_Threshold2
    Canny_Threshold2 = value
    updateContours()


def Canny_RetrievalMode_changed(value):
    global Canny_RetrievalMode
    Canny_RetrievalMode = value
    updateContours()


def Scaled_Threshold_changed(value):
    global Scaled_Threshold
    Scaled_Threshold = value
    updateContours()


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


def Contour_Thickness_changed(value):
    global Contour_Thickness
    Contour_Thickness = value
    updateContours()


def createContoursWindow(or_img, i):
    global orig_img, img

    print("\n\n------ Entering contour Editor -------")
    print("Have fun playing around with the sliders. To accept your changes, press e. Press q to exit.\n")

    orig_img = or_img
    img = i
    cv2.namedWindow(EdgeDetectorWindowTitle, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(EdgeDetectorWindowTitle, 600, 800)
    cv2.createTrackbar("BiFilter SigmaColor", EdgeDetectorWindowTitle, BiFilter_SigmaColor, 255,  BiFilter_SigmaColor_changed)
    cv2.createTrackbar("BiFilter SigmaSpace", EdgeDetectorWindowTitle, BiFilter_SigmaSpace, 255,  BiFilter_SigmaSpace_changed)
    cv2.createTrackbar("Canny Threshold 1", EdgeDetectorWindowTitle, Canny_Threshold1, 1000, Canny_Threshold1_changed)
    cv2.createTrackbar("Canny Threshold 2", EdgeDetectorWindowTitle, Canny_Threshold2, 1000, Canny_Threshold2_changed)
    cv2.createTrackbar("Canny Retrieval Mode", EdgeDetectorWindowTitle, Canny_RetrievalMode, len(canny_retrieval_modes) - 1, Canny_RetrievalMode_changed)
    cv2.createTrackbar("Scaled Threshold", EdgeDetectorWindowTitle, Scaled_Threshold, 255, Scaled_Threshold_changed)
    cv2.createTrackbar("Contour Thickness", EdgeDetectorWindowTitle, Contour_Thickness, 16, Contour_Thickness_changed)
    cv2.setTrackbarMin("Contour Thickness", EdgeDetectorWindowTitle, 1)
    # No effect
    # cv2.createTrackbar("BiFilter BorderType", EdgeDetectorWindowTitle, BiFilter_BorderType, len(bifilter_border_types) - 1,  BiFilter_BorderType_changed)
    
    done = False
    while not done:
        updateContours()
        c = cv2.waitKey(0)
        k = chr(c)
        if k == 'q':
            done = True
    cv2.destroyWindow(EdgeDetectorWindowTitle)
