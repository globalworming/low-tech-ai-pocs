"""
Configuration settings for the Image Processor.
"""
from pathlib import Path

# Default paths
DEFAULT_MODEL_PATH = "/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-int4.gguf"
DEFAULT_MMPROJ_PATH = "/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-mmproj-f16.gguf"
DEFAULT_CAPTURE_DIR = "captures"
DEFAULT_OUTPUT_DIR = "descriptions"

# Model parameters
DEFAULT_MODEL_PARAMS = {
    "n_ctx": 8192,  # Context window size
    "n_threads": 8,  # Number of CPU threads
    "n_batch": 2048,  # Batch size for prompt processing
    "seed": 42,  # Random seed for reproducibility
    "verbose": True  # Show detailed logs
}

# Generation parameters
DEFAULT_GEN_PARAMS = {
    "max_tokens": 10000,
    "temperature": 0.1,
    "top_p": 0.9,
    "stop": ["Q:", "\n"]
}

# Image extensions to look for
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}

def get_default_paths():
    """Return default paths as Path objects."""
    return {
        "model": Path(DEFAULT_MODEL_PATH),
        "mmproj": Path(DEFAULT_MMPROJ_PATH),
        "captures": Path(DEFAULT_CAPTURE_DIR),
        "output": Path(DEFAULT_OUTPUT_DIR)
    }
