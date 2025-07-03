#!/usr/bin/env python3
"""
Command-line interface for the Image Processor.
"""
import argparse
import sys
from pathlib import Path

from image_processor.config import (
    get_default_paths,
    DEFAULT_CAPTURE_DIR,
    DEFAULT_OUTPUT_DIR
)
from image_processor.image_analyzer import ImageAnalyzer

def parse_args():
    """Parse command-line arguments."""
    default_paths = get_default_paths()
    
    parser = argparse.ArgumentParser(
        description="Analyze images using a local LLaVA model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Model options
    model_group = parser.add_argument_group('Model Options')
    model_group.add_argument(
        '--model',
        type=Path,
        default=default_paths['model'],
        help='Path to the LLaMA model file'
    )
    model_group.add_argument(
        '--mmproj',
        type=Path,
        default=default_paths['mmproj'],
        help='Path to the multimodal projection file'
    )
    
    # Input/output options
    io_group = parser.add_argument_group('Input/Output')
    io_group.add_argument(
        '--image',
        type=Path,
        help='Path to the image file to analyze (default: use latest in --capture-dir)'
    )
    io_group.add_argument(
        '--capture-dir',
        type=Path,
        default=Path(DEFAULT_CAPTURE_DIR),
        help='Directory to watch for new images'
    )
    io_group.add_argument(
        '--output-dir',
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR),
        help='Directory to save output files'
    )
    
    # Runtime options
    runtime_group = parser.add_argument_group('Runtime Options')
    runtime_group.add_argument(
        '--continuous',
        action='store_true',
        help='Run in continuous mode, watching for new images'
    )
    runtime_group.add_argument(
        '--interval',
        type=float,
        default=0,
        help='Time to wait between checks in continuous mode (seconds)'
    )
    runtime_group.add_argument(
        '--no-save',
        action='store_true',
        help="Don't save output to a file"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Create output directory if it doesn't exist
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize the analyzer
    analyzer = ImageAnalyzer(
        model_path=str(args.model),
        mmproj_path=str(args.mmproj),
        output_dir=args.output_dir if not args.no_save else None,
        verbose=True
    )
    
    try:
        if args.continuous:
            # Run in continuous mode
            analyzer.run_continuous_analysis(
                image_dir=args.capture_dir,
                interval=args.interval,
                save_output=not args.no_save
            )
        else:
            # Single image mode
            if args.image:
                image_path = args.image
            else:
                # Use the latest image in the capture directory
                image_path = get_latest_image(args.capture_dir)
            
            analyzer.analyze_image(
                str(image_path),
                save_output=not args.no_save
            )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
