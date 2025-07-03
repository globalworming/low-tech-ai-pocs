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


    return response['choices'][0]['message']['content']

def run_continuous_describe(llm, image_file, output_dir='descriptions', sleep_seconds=0):
    """
    Runs describe in a continuous loop, writing each response to a timestamped JSON file.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting continuous describe loop for {image_file}")
    print(f"Output directory: {output_dir}")
    print(f"Sleep interval: {sleep_seconds} seconds")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
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

if __name__ == '__main__':
    image_file = 'webcam_capture.jpg'
    llava_model = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-int4.gguf'
    llava_mmproj = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-mmproj-f16.gguf'
    
    """
    Generates a description for an image using a local LLaVA model.
    """
    chat_handler = Llava15ChatHandler(clip_model_path=llava_mmproj)

    llm = Llama(
        model_path=llava_model,
        chat_handler=chat_handler,
        n_ctx=8192,  # Larger context for better responses
        n_threads=8, # Number of CPU threads to use
        n_batch=512,
        verbose=False,
        seed=42,  # For reproducible results
        temperature=0.1,  # Lower temperature for more focused responses
        top_p=0.9
    )

    # Run continuous describe loop
    run_continuous_describe(llm, image_file)