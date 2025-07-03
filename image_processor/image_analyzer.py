"""
Image analysis functionality for the Image Processor.
"""
import time
from pathlib import Path
from typing import Optional, Dict, Any

from .llm_client import LLMClient
from .file_utils import save_description, get_latest_image

class ImageAnalyzer:
    """Handles image analysis using an LLM client."""
    
    def __init__(
        self, 
        model_path: str, 
        mmproj_path: str,
        output_dir: Optional[str] = None,
        **llm_kwargs
    ):
        """
        Initialize the ImageAnalyzer.
        
        Args:
            model_path: Path to the LLaMA model file.
            mmproj_path: Path to the multimodal projection file.
            output_dir: Directory to save output files.
            **llm_kwargs: Additional arguments for the LLM client.
        """
        self.llm_client = LLMClient(model_path, mmproj_path, **llm_kwargs)
        self.output_dir = Path(output_dir) if output_dir else None
    
    def analyze_image(
        self, 
        image_path: str,
        save_output: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze an image and generate a description.
        
        Args:
            image_path: Path to the image file.
            save_output: Whether to save the output to a file.
            **kwargs: Additional arguments for the LLM client.
            
        Returns:
            Dictionary containing the analysis results and metadata.
        """
        print(f"Analyzing image: {image_path}")
        start_time = time.time()
        
        # Generate the description
        result = self.llm_client.describe_image(image_path, **kwargs)
        
        # Save the output if requested
        output_path = None
        if save_output and self.output_dir:
            output_path = save_description(
                result["content"],
                output_dir=self.output_dir
            )
            print(f"Output saved to: {output_path}")
        
        # Calculate total processing time
        total_time = time.time() - start_time
        
        return {
            "content": result["content"],
            "output_path": str(output_path) if output_path else None,
            "processing_time": total_time,
            "tokens_generated": result["tokens_generated"],
            "tokens_per_second": result["tokens_per_second"]
        }
    
    def analyze_latest_image(
        self,
        image_dir: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze the most recent image in a directory.
        
        Args:
            image_dir: Directory containing images. If None, uses the default.
            **kwargs: Additional arguments for analyze_image.
            
        Returns:
            Dictionary containing the analysis results and metadata.
        """
        image_path = get_latest_image(image_dir)
        return self.analyze_image(str(image_path), **kwargs)
    
    def run_continuous_analysis(
        self,
        image_dir: Optional[str] = None,
        interval: float = 0,
        **kwargs
    ) -> None:
        """
        Continuously analyze new images as they appear.
        
        Args:
            image_dir: Directory to watch for new images.
            interval: Time to wait between checks (seconds).
            **kwargs: Additional arguments for analyze_latest_image.
        """
        print("Starting continuous image analysis...")
        print(f"Watching directory: {image_dir}")
        print(f"Check interval: {interval} seconds")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                try:
                    self.analyze_latest_image(image_dir=image_dir, **kwargs)
                    print(f"Waiting {interval} seconds before next check...")
                    time.sleep(interval)
                except FileNotFoundError as e:
                    print(f"Error: {e}. Waiting for images...")
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping continuous analysis...")
            print("Goodbye!")
