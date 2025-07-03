from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
import base64

def generate_description(image_path, model_path, mmproj_path):
    """
    Generates a description for an image using a local LLaVA model.
    """
    chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)

    llm = Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        n_ctx=8192,  # Larger context for better responses
        n_threads=8, # Number of CPU threads to use
        n_batch=512,
        verbose=False,
        seed=42,  # For reproducible results
        temperature=0.1,  # Lower temperature for more focused responses
        top_p=0.9
    )

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
                    {"type": "text", "content": "office material on a table. describe the objects in the image."}
                ]
            }
        ],
        max_tokens=8000,
        response_format={"type": "json_object",},
        stop=["Q:", "\n"], # Stop generating just before the model would generate a new question
    )


    return response['choices'][0]['message']['content']

if __name__ == '__main__':
    image_file = 'webcam_capture.jpg'
    llava_model = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-int4.gguf'
    llava_mmproj = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-mmproj-f16.gguf'
    
    # Then, generate the description
    description = generate_description(image_file, llava_model, llava_mmproj)
    print("\n--- Generated Description ---")
    print(description)