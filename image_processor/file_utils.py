"""
File and directory utilities for the Image Processor.
"""
import os
import time
from pathlib import Path
from typing import Optional, List, Set
from .config import IMAGE_EXTENSIONS, DEFAULT_CAPTURE_DIR, DEFAULT_OUTPUT_DIR

def ensure_directory(directory: Path) -> None:
    """Ensure that a directory exists, creating it if necessary."""
    directory.mkdir(parents=True, exist_ok=True)

def get_latest_image(directory: Path = None) -> Path:
    """
    Get the most recently created image file from the specified directory.
    
    Args:
        directory: Directory to search for images. Defaults to DEFAULT_CAPTURE_DIR.
        
    Returns:
        Path to the most recent image file.
        
    Raises:
        FileNotFoundError: If the directory doesn't exist or contains no images.
    """
    if directory is None:
        directory = Path(DEFAULT_CAPTURE_DIR)
    
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"The directory '{directory}' does not exist")
    
    # Find all image files in the directory
    image_files = [f for f in directory.iterdir() 
                  if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    
    if not image_files:
        raise FileNotFoundError(f"No image files found in '{directory}'")
    
    # Return the most recently created file
    return max(image_files, key=os.path.getctime)

def save_description(content: str, output_dir: Path = None) -> Path:
    """
    Save a description to a JSON file with a timestamp.
    
    Args:
        content: The description content to save.
        output_dir: Directory to save the file. Defaults to DEFAULT_OUTPUT_DIR.
        
    Returns:
        Path to the saved file.
    """
    if output_dir is None:
        output_dir = Path(DEFAULT_OUTPUT_DIR)
    
    ensure_directory(output_dir)
    
    # Create a timestamped filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"description_{timestamp}.json"
    
    # Write the content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_file
