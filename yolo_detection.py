#!/usr/bin/env python3
"""
YOLO11 Object Detection Implementation
Requires: pip install ultralytics
"""

import cv2
import os
from ultralytics import YOLO
import numpy as np


class YOLO11Detector:
    def __init__(self, model_name='yolo11n.pt', enable_tracking=False):
        """
        Initialize YOLO11 detector.
        
        Args:
            model_name (str): YOLO11 model variant (yolo11n.pt, yolo11s.pt, yolo11m.pt, yolo11l.pt, yolo11x.pt)
            enable_tracking (bool): Enable object tracking capabilities
        """
        self.model_name = model_name
        self.enable_tracking = enable_tracking
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the YOLO11 model."""
        try:
            task = 'track' if self.enable_tracking else 'detect'
            print(f"Loading YOLO11 model: {self.model_name} (task: {task})")
            self.model = YOLO(self.model_name, task=task, verbose=True)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def detect_objects(self, image_path):
        if self.model is None:
            raise ValueError("Model not loaded")
        
        # Check if image exists
        if not os.path.exists(image_path):
            raise ValueError(f"Image not found: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        # Run detection or tracking
        if self.enable_tracking:
            print(f"Running YOLO11 tracking on: {image_path}")
            results = self.model.track(image_path, persist=True)
        else:
            print(f"Running YOLO11 detection on: {image_path}")
            results = self.model(image_path)
        
        print(results)
        return image, results[0]  # Return first result
    
    def draw_detections(self, image, result, show_conf=True, show_class=True):
        """
        Draw bounding boxes and labels on image.
        
        Args:
            image: Input image
            result: YOLO detection result
            show_conf (bool): Show confidence scores
            show_class (bool): Show class names
            
        Returns:
            Image with drawn detections
        """
        result_image = image.copy()
        
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()  # Get bounding boxes
            confidences = result.boxes.conf.cpu().numpy()  # Get confidence scores
            class_ids = result.boxes.cls.cpu().numpy().astype(int)  # Get class IDs
            
            # Get class names
            class_names = result.names
            
            for i, (box, conf, class_id) in enumerate(zip(boxes, confidences, class_ids)):
                x1, y1, x2, y2 = box.astype(int)
                
                # Draw bounding box
                color = self._get_color(class_id)
                cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
                
                # Create label
                label_parts = []
                if show_class:
                    label_parts.append(class_names[class_id])
                if show_conf:
                    label_parts.append(f"{conf:.2f}")
                
                label = " ".join(label_parts)
                
                # Draw label background
                (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(result_image, (x1, y1 - label_height - 10), (x1 + label_width, y1), color, -1)
                
                # Draw label text
                cv2.putText(result_image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return result_image
    
    def _get_color(self, class_id):
        """Generate consistent color for each class."""
        np.random.seed(class_id)
        return tuple(np.random.randint(0, 255, 3).tolist())
    
    def detect_and_save(self, image_path, output_path=None):
        """
        Detect objects and save result image.
        
        Args:
            image_path (str): Path to input image
            output_path (str): Path to save result image (optional)
            conf_threshold (float): Confidence threshold
            iou_threshold (float): IoU threshold
            
        Returns:
            tuple: (result_image, detection_info)
        """
        try:
            image, result = self.detect_objects(image_path)
            result_image = self.draw_detections(image, result)
            
            # Print detection summary
            if result.boxes is not None:
                num_detections = len(result.boxes)
                print(f"Found {num_detections} objects:")
                
                # Group detections by class
                class_counts = {}
                for class_id in result.boxes.cls.cpu().numpy().astype(int):
                    class_name = result.names[class_id]
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
                
                for class_name, count in class_counts.items():
                    print(f"  {class_name}: {count}")
            else:
                print("No objects detected")
            
            # Save result if output path provided
            if output_path:
                cv2.imwrite(output_path, result_image)
                print(f"Result saved to: {output_path}")
            
            return result_image, result
            
        except Exception as e:
            print(f"Error during detection: {e}")
            return None, None


def main():
    """Run YOLO11 detection on the specified image."""
    # Image path
    image_path = "captures/yolo11_result.png"
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return
    
    try:
        # Initialize detector (using nano model for speed)
        print("Initializing YOLO11 detector...")
        detector = YOLO11Detector('yolo11n.pt')
        
        # Run detection
        result_image, result = detector.detect_and_save(
            image_path,
            output_path="captures/yolo11_result.png"
        )
        
        if result_image is not None:
            print("\nDetection completed successfully!")
            print("Result saved to: captures/yolo11_result.png")
        else:
            print("Detection failed")
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure to install ultralytics:")
        print("pip install ultralytics")


if __name__ == "__main__":
    main()
