import cv2

def capture_image(file_path='webcam_capture.jpg'):
    """
    Captures a single image from the default webcam.
    """
    # Initialize the camera
    cam = cv2.VideoCapture(0)
    cv2.namedWindow("Webcam Capture - Press SPACE to save, ESC to quit")
    img_counter = 0

    while True:
        ret, frame = cam.read()
        if not ret:
            print("Failed to grab frame.")
            break
        cv2.imshow("Webcam Capture - Press SPACE to save, ESC to quit", frame)

        k = cv2.waitKey(1)
        if k % 256 == 27:  # ESC key
            print("Escape hit, closing...")
            break
        elif k % 256 == 32:  # SPACE key
            cv2.imwrite(file_path, frame)
            print(f"Image saved to {file_path}")
            break

    cam.release()
    cv2.destroyAllWindows()
    return True

if __name__ == '__main__':
    capture_image()