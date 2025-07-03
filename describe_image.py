from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
import base64
import json
import time
import datetime
import os

def generate_description(image_path, llm):

    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Convert image bytes to base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
          
    response = llm.create_chat_completion(
        messages=[
             {
                "role": "system",
                "content": """You are an image analysis assistant that outputs structured JSON.
Analyze the image and provide a JSON object with three keys:
1. "summary": A brief one-sentence overview of the image.
2. "setting": A description of the background, location, and lighting.
3. "objects": An array of JSON objects, where each object has "item" (the name of the object), "color" (its primary color), and "position" (e.g., "center", "top-left", "foreground")."""
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "content": "office material on a table. describe all objects in the image and their positions to each other"}
                ]
            }
        ],
        max_tokens=10000,
        response_format={"type": "json_object",},
        stop=["Q:", "\n"], # Stop generating just before the model would generate a new question
    )

    print("raw response")
    print(response)

    return response['choices'][0]['message']['content']

def run_continuous_describe(llm, output_dir='descriptions', sleep_seconds=0):
    """
    Runs describe in a continuous loop, writing each response to a timestamped JSON file.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting continuous describe loop")
    print(f"Output directory: {output_dir}")
    print(f"Sleep interval: {sleep_seconds} seconds")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            image_file = get_latest_image('captures')
            print(f"Using latest image: {image_file}")
            # Check if image file exists
            if not os.path.exists(image_file):
                print(f"Warning: Image file {image_file} not found. Waiting...")
                time.sleep(sleep_seconds)
                continue
            
            # Generate timestamp for filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
            output_file = os.path.join(output_dir, f"description_{timestamp}.json")
            
            try:
                # Generate description
                print(f"Generating description at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
                description = generate_description(image_file, llm)
                
                # Create response object with metadata
                response_data = {
                    "timestamp": timestamp,
                    "iso_timestamp": datetime.datetime.now().isoformat(),
                    "image_file": image_file,
                    "description": json.loads(description) if description.strip().startswith('{') else description
                }
                
                # Write to JSON file
                with open(output_file, 'w') as f:
                    json.dump(response_data, f, indent=2)
                
                print(f"Description saved to: {output_file}")
                
            except Exception as e:
                print(f"Error generating description: {e}")
                # Still sleep to avoid tight error loop
            
            # Wait before next iteration
            time.sleep(sleep_seconds)
            
    except KeyboardInterrupt:
        print("\nStopping continuous describe loop...")
        print("Goodbye!")

def get_latest_image(folder='captures'):
    """Get the most recently created image file from the specified folder."""
    import os
    from pathlib import Path
    
    # Ensure the folder exists
    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        raise FileNotFoundError(f"The folder '{folder}' does not exist")
    
    # Find all image files in the folder
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    image_files = [f for f in folder_path.iterdir() 
                  if f.is_file() and f.suffix.lower() in image_extensions]
    
    if not image_files:
        raise FileNotFoundError(f"No image files found in '{folder}'")
    
    # Return the most recently created file
    return str(max(image_files, key=os.path.getctime))

if __name__ == '__main__':    
    llava_model = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-int4.gguf'
    llava_mmproj = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-mmproj-f16.gguf'
    
    """
    Generates a description for an image using a local LLaVA model.
    """
    chat_handler = Llava15ChatHandler(clip_model_path=llava_mmproj)

    # Initialize Llama with logging disabled
    llm = Llama(
        model_path=llava_model,
        chat_handler=chat_handler,
        n_ctx=8192,  # Larger context for better responses
        n_threads=8,  # Number of CPU threads to use
        n_batch=2048,
        verbose=True,
        seed=42,  # For reproducible results
    )

    # Run continuous describe loop
    run_continuous_describe(llm)