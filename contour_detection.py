import cv2
import os
import numpy as np

def nothing(x):
    # Dummy function for trackbar callback
    pass

def detect_contours(image_path, output_dir='contour_detection_results', preview=True):
    """
    Apply contour detection to an image with optional preview and save the result.
    
    Args:
        image_path (str): Path to the input image
        output_dir (str): Directory to save the output image
        preview (bool): Whether to show interactive preview window
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image at {image_path}")
        return False
    
    # Convert to grayscale for contour detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if not preview:
        # Non-interactive mode - use default values
        return _process_contours(img, gray, 127, 255, image_path, output_dir)
    
    # Create a window and trackbars for interactive adjustment
    cv2.namedWindow('Contour Detection Preview')
    cv2.createTrackbar('Threshold', 'Contour Detection Preview', 127, 255, nothing)
    cv2.createTrackbar('Max Value', 'Contour Detection Preview', 255, 255, nothing)
    cv2.createTrackbar('Min Area', 'Contour Detection Preview', 100, 5000, nothing)
    
    # Apply Gaussian blur to reduce noise (done once for performance)
    gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    while True:
        # Get current trackbar positions
        thresh_val = cv2.getTrackbarPos('Threshold', 'Contour Detection Preview')
        max_val = cv2.getTrackbarPos('Max Value', 'Contour Detection Preview')
        min_area = cv2.getTrackbarPos('Min Area', 'Contour Detection Preview')
        
        # Create binary image
        _, binary = cv2.threshold(gray_blur, thresh_val, max_val, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]
        
        # Create display image
        display = img.copy()
        
        # Draw contours
        cv2.drawContours(display, filtered_contours, -1, (0, 255, 0), 2)
        
        # Add text with current parameter values and contour count
        cv2.putText(display, f'Threshold: {thresh_val}, Max: {max_val}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(display, f'Min Area: {min_area}, Contours: {len(filtered_contours)}', 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(display, 'Press ENTER to save, ESC to cancel', 
                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)
        
        # Show the result
        cv2.imshow('Contour Detection Preview', display)
        
        # Wait for key press
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # ENTER key
            cv2.destroyAllWindows()
            return _process_contours(img, gray, thresh_val, max_val, image_path, output_dir, min_area)
        elif key == 27:  # ESC key
            cv2.destroyAllWindows()
            print("Operation cancelled by user")
            return False

def _process_contours(img, gray, thresh_val, max_val, image_path, output_dir, min_area=100):
    """Helper function to process contours with given parameters and save the result."""
    # Apply Gaussian blur to reduce noise
    gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Create binary image
    _, binary = cv2.threshold(gray_blur, thresh_val, max_val, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]
    
    # Create result image
    result = img.copy()
    cv2.drawContours(result, filtered_contours, -1, (0, 255, 0), 2)
    
    # Create output filename
    filename = os.path.basename(image_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(output_dir, f"{name}_contours{ext}")
    
    # Save the result
    cv2.imwrite(output_path, result)
    print(f"Contour detection complete. Found {len(filtered_contours)} contours. Result saved to {output_path}")
    return True

if __name__ == "__main__":
    # Path to the captured image
    image_path = "captures/capture_20250703_161123.jpg"
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
    else:
        detect_contours(image_path)
