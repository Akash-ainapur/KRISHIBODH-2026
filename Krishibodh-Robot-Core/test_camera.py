import cv2
import time

# Try to open camera at index 1 (the second camera)
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if cap.isOpened():
    print("Camera opened successfully!")
    time.sleep(1)  # Let camera warm up
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("test_capture.jpg", frame)
        print("Image saved as test_capture.jpg")
    else:
        print("Failed to capture frame")
    cap.release()
else:
    print("Failed to open camera at index 1")
