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
        n_ctx=4096,  # Larger context for better responses
        n_threads=8, # Number of CPU threads to use
        n_batch=512,
        verbose=True,
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
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "content": "Please describe what you see in this image in detail. Include objects, people, colors, and setting."}
                ]
            }
        ],
        max_tokens=200,
        temperature=0.1
    )
    # Log the full response for debugging
    print("Raw model response:")
    print(response)

    return response['choices'][0]['message']['content']

if __name__ == '__main__':
    image_file = 'webcam_capture.jpg'
    llava_model = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-int4.gguf'
    llava_mmproj = '/home/t430s/models/llava-llama-3/llava-llama-3-8b-v1_1-mmproj-f16.gguf'
    
    # Then, generate the description
    description = generate_description(image_file, llava_model, llava_mmproj)
    print("\n--- Generated Description ---")
    print(description)