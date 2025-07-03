"""
Image analysis functionality for the Image Processor.
"""
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from .llm_client import LLMClient
from .file_utils import get_latest_image

class ImageAnalyzer:
    """
    Handles image analysis using a language model for generating descriptions.
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the ImageAnalyzer with an LLMClient.
        
        Args:
            llm_client: Initialized LLMClient instance for making inference calls
        """
        self.llm = llm_client
    
    def generate_description(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Generate a structured description of an image.
        
        Args:
            image_path: Path to the image file to analyze
            
        Returns:
            Dictionary containing the generated description
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        try:
            # Use the LLM client to generate the description
            response = self.llm.describe_image(str(image_path))
            print(response)
            # Parse the response if it's a JSON string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
            
        except Exception as e:
            raise RuntimeError(f"Error generating description: {str(e)}")
    
    def run_continuous_describe(
        self, 
        input_dir: Union[str, Path],
        output_dir: Union[str, Path] = 'descriptions',
        sleep_seconds: int = 0
    ) -> None:
        """
        Continuously monitor an input directory for new images and generate descriptions.
        
        Args:
            input_dir: Directory to monitor for new images
            output_dir: Directory to save description files
            sleep_seconds: Time to sleep between checks (0 for no sleep)
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Starting continuous describe loop")
        print(f"Input directory: {input_dir}")
        print(f"Output directory: {output_dir}")
        print(f"Sleep interval: {sleep_seconds} seconds")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                image_file = get_latest_image(input_dir)
                print(f"Using latest image: {image_file}")
                
                if not image_file or not image_file.exists():
                    print(f"Warning: Image file {image_file} not found. Waiting...")
                    time.sleep(sleep_seconds)
                    continue
                
                # Generate timestamp for filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
                output_file = output_dir / f"description_{timestamp}.json"
                
                try:
                    # Generate description
                    print(f"Generating description at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
                    description = self.generate_description(image_file)
                    
                    print(description)
                    # Create response object with metadata
                    response_data = {
                        "timestamp": timestamp,
                        "iso_timestamp": datetime.now().isoformat(),
                        "image_file": str(image_file.absolute()),
                        "description": description
                    }
                    
                    # Write to JSON file
                    with open(output_file, 'w') as f:
                        json.dump(response_data, f, indent=2)
                    
                    print(f"Description saved to: {output_file}")
                    
                except Exception as e:
                    print(f"Error generating description: {e}")
                    # Still sleep to avoid tight error loop
                
                # Wait before next iteration if needed
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
                    
        except KeyboardInterrupt:
            print("\nStopping continuous describe loop...")
            print("Goodbye!")
