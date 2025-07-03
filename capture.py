import cv2
import time
from datetime import datetime
import os

def capture_images(interval=5, output_dir='captures'):
    """
    Captures and saves an image from the default webcam at regular intervals.
    
    Args:
        interval (int): Time between captures in seconds
        output_dir (str): Directory to save captured images
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the camera
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Error: Could not open webcam")
        return False
        
    cv2.namedWindow("Webcam Capture - Press ESC to quit")
    
    print(f"Starting webcam capture. Saving image every {interval} seconds...")
    print("Press ESC to quit")
    
    last_capture = 0
    
    try:
        while True:
            current_time = time.time()
            
            # Capture frame
            ret, frame = cam.read()
            if not ret:
                print("Failed to grab frame.")
                break
                
            # Show the frame
            cv2.imshow("Webcam Capture - Press ESC to quit", frame)
            
            # Save image at specified interval
            if current_time - last_capture >= interval:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(output_dir, f"capture_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                print(f"Image saved: {filename}")
                last_capture = current_time
            
            # Check for ESC key
            if cv2.waitKey(1) % 256 == 27:  # ESC key
                print("Escape hit, closing...")
                break
                
    finally:
        # Clean up
        cam.release()
        cv2.destroyAllWindows()
        print("Webcam released")
    
    return True

if __name__ == '__main__':
    capture_images(interval=5)  # Capture every 5 seconds