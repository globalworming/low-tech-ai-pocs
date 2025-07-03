import cv2
import os
import numpy as np

def nothing(x):
    # Dummy function for trackbar callback
    pass

def detect_edges(image_path, output_dir='edge_detection_results', preview=True):
    """
    Apply Canny edge detection to an image with optional preview and save the result.
    
    Args:
        image_path (str): Path to the input image
        output_dir (str): Directory to save the output image
        preview (bool): Whether to show interactive preview window
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the image in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Error: Could not read image at {image_path}")
        return False
    
    if not preview:
        # Non-interactive mode - use default values
        return _process_edges(img, 50, 150, image_path, output_dir)
    
    # Create a window and trackbars for interactive adjustment
    cv2.namedWindow('Edge Detection Preview')
    cv2.createTrackbar('Min Threshold', 'Edge Detection Preview', 50, 255, nothing)
    cv2.createTrackbar('Max Threshold', 'Edge Detection Preview', 150, 255, nothing)
    
    # Apply Gaussian blur to reduce noise (done once for performance)
    img_blur = cv2.GaussianBlur(img, (5, 5), 0)
    
    while True:
        # Get current trackbar positions
        min_thresh = cv2.getTrackbarPos('Min Threshold', 'Edge Detection Preview')
        max_thresh = cv2.getTrackbarPos('Max Threshold', 'Edge Detection Preview')
        
        # Ensure min threshold is less than max threshold
        if min_thresh >= max_thresh:
            min_thresh = max(0, max_thresh - 1)
            cv2.setTrackbarPos('Min Threshold', 'Edge Detection Preview', min_thresh)
        
        # Apply Canny edge detection
        edges = cv2.Canny(img_blur, min_thresh, max_thresh)
        
        # Create a 3-channel image for display (converting from grayscale to BGR)
        display = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # Add text with current threshold values
        cv2.putText(display, f'Min: {min_thresh}, Max: {max_thresh}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(display, 'Press ENTER to save, ESC to cancel', 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)
        
        # Show the result
        cv2.imshow('Edge Detection Preview', display)
        
        # Wait for key press
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # ENTER key
            cv2.destroyAllWindows()
            return _process_edges(img, min_thresh, max_thresh, image_path, output_dir)
        elif key == 27:  # ESC key
            cv2.destroyAllWindows()
            print("Operation cancelled by user")
            return False

def _process_edges(img, min_thresh, max_thresh, image_path, output_dir):
    """Helper function to process edges with given thresholds and save the result."""
    # Apply Gaussian blur to reduce noise
    img_blur = cv2.GaussianBlur(img, (5, 5), 0)
    
    # Apply Canny edge detection
    edges = cv2.Canny(img_blur, min_thresh, max_thresh)
    
    # Create output filename
    filename = os.path.basename(image_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(output_dir, f"{name}_edges{ext}")
    
    # Save the result
    cv2.imwrite(output_path, edges)
    print(f"Edge detection complete. Result saved to {output_path}")
    return True

if __name__ == "__main__":
    # Path to the captured image
    image_path = "captures/capture_20250703_161123.jpg"
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
    else:
        detect_edges(image_path)
