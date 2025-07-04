import cv2
import os

class HaarCascadeDetector:
    def __init__(self, cascade_xml_path=None):
        """
        Initialize Haar Cascade detector.
        
        Args:
            cascade_xml_path (str): Path to Haar cascade XML file. 
                                   If None, uses placeholder path that needs to be set.
        """
        if cascade_xml_path is None:
            # Placeholder - replace with actual cascade XML path
            cascade_xml_path = "/home/wormi/models/haar/haarcascade_fullbody.xml"
        
        self.cascade_xml_path = cascade_xml_path
        self.cascade = None
        self._load_cascade()
    
    def _load_cascade(self):
        """Load the Haar cascade classifier."""
        if os.path.exists(self.cascade_xml_path):
            self.cascade = cv2.CascadeClassifier(self.cascade_xml_path)
            if self.cascade.empty():
                raise ValueError(f"Failed to load cascade from {self.cascade_xml_path}")
        else:
            print(f"Warning: Cascade file not found at {self.cascade_xml_path}")
            print("Please update the cascade_xml_path with a valid Haar cascade XML file")
    
    def detect_objects(self, image_path, scale_factor=1.1, min_neighbors=5, min_size=(30, 30)):
        """
        Detect objects in image using Haar cascade.
        
        Args:
            image_path (str): Path to input image
            scale_factor (float): How much image size is reduced at each scale
            min_neighbors (int): How many neighbors each object needs to retain
            min_size (tuple): Minimum possible object size, smaller objects ignored
            
        Returns:
            tuple: (original_image, detections) where detections is list of (x, y, w, h)
        """
        if self.cascade is None:
            raise ValueError("Cascade not loaded. Please provide valid cascade XML path")
        
        # Read and convert image to grayscale
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect objects
        detections = self.cascade.detectMultiScale(
            gray, 
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=min_size
        )
        
        return image, detections
    
    def draw_detections(self, image, detections, color=(255, 0, 0), thickness=2):
        """
        Draw rectangles around detected objects.
        
        Args:
            image: Input image
            detections: List of (x, y, w, h) tuples
            color: BGR color tuple for rectangle
            thickness: Rectangle line thickness
            
        Returns:
            Image with drawn rectangles
        """
        result_image = image.copy()
        
        for (x, y, w, h) in detections:
            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, thickness)
        
        return result_image
    
    def detect_and_display(self, image_path, window_name="Detected Objects"):
        """
        Detect objects and display result.
        
        Args:
            image_path (str): Path to input image
            window_name (str): Name of display window
        """
        try:
            image, detections = self.detect_objects(image_path)
            result_image = self.draw_detections(image, detections)
            
            print(f"Found {len(detections)} objects")
            
            cv2.imshow(window_name, result_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
            return result_image, detections
            
        except Exception as e:
            print(f"Error during detection: {e}")
            return None, []

def main():
    """Example usage of HaarCascadeDetector."""
    # Example with common cascade files (uncomment and modify as needed):
    # Face detection:
    # detector = HaarCascadeDetector(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Eye detection:
    # detector = HaarCascadeDetector(cv2.data.haarcascades + 'haarcascade_eye.xml')
    
    # Car detection (if you have the XML file):
    # detector = HaarCascadeDetector('path/to/haarcascade_car.xml')
    
    # Initialize with placeholder (will show warning)
    detector = HaarCascadeDetector()
    
    # Example image path (update with your image)
    image_path = "captures/image.png"
    
    # Detect and display (will show error until valid cascade is provided)
    try:
        detector.detect_and_display(image_path)
    except Exception as e:
        print(f"Demo failed: {e}")
        print("\nTo use this detector:")
        print("1. Set a valid cascade XML path")
        print("2. Provide a valid image path")
        print("3. Run the detection")

if __name__ == "__main__":
    main()
