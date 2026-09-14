import cv2
import numpy as np
class AlignmentError(Exception):
    pass


def align_image(gray_old,gray_new,min_match_count=15):
    orb = cv2.ORB_create(nfeatures=5000)
    kp1, des1 = orb.detectAndCompute(gray_old, None)
    kp2, des2 = orb.detectAndCompute(gray_new, None)

    print(f"old image: {len(kp1) if kp1 else 0} keypoints found")
    print(f"new image: {len(kp2) if kp2 else 0} keypoints found")

    if des1 is None or des2 is None or len(des1) == 0 or len(des2) == 0:
        raise AlignmentError("No features detected in one of the images")
    try:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(des1, des2, k=2)

        good = []

        for m_n in matches:
            if len(m_n) != 2:
                continue
            m, n = m_n
            if m.distance < 0.75 * n.distance:
                good.append(m)

        print(f"good matches after ratio test: {len(good)} (need {min_match_count})")
    except Exception as e:
        print(f"CRASH in matching step: {type(e).__name__}: {e}")
        raise

    if len(good) < min_match_count:
        raise AlignmentError(f"Only {len(good)} good matches, need {min_match_count}")

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    H,mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)
    if H is None:
        raise AlignmentError("Homography estimation failed")

    inliers = int(mask.sum()) if mask is not None else 0
    h,w = gray_old.shape
    warped_new = cv2.warpPerspective(gray_new,H,(w,h))
    return {
        "warped_new": warped_new,
        "match_count": len(good),
        "inlier_count": inliers,
        "confidence": inliers / max(len(good), 1),
        "H": H,
    }

