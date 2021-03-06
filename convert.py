import cv2

m = {cv2.INTER_LANCZOS4: "lanc",
     cv2.INTER_AREA: "area",
     cv2.INTER_CUBIC: "cube",
     cv2.INTER_NEAREST: "near",
     cv2.INTER_BITS: "bits",
     cv2.INTER_LINEAR: "lin",
     }

size = 300
rpl = cv2.imread('rpl.png', cv2.IMREAD_UNCHANGED)

for key in m:
    edit = cv2.resize(rpl, dsize=(size, size), interpolation=key)
    trans_mask = edit[:, :, 3] < 10
    edit[trans_mask] = [0, 0, 0, 255]
    cv2.imwrite(m[key] + ".jpg", edit, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

    read = cv2.imread(m[key] + ".jpg")
    cv2.namedWindow(m[key], cv2.WINDOW_NORMAL)
    cv2.imshow(m[key], read)

cv2.waitKey(0)
cv2.destroyAllWindows()
