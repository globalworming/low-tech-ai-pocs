from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

def generate_description(image_path, model_path, mmproj_path):
    """
    Generates a description for an image using a local LLaVA model.
    """
    chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)

    llm = Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        n_ctx=2048,  # Context size
        n_threads=4, # Number of CPU threads to use
        verbose=False
    )

    image_bytes = open(image_path, "rb").read()

    response = llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are an assistant who describes images in a structured JSON format. Identify the main objects and their positions."
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{llm.detokenize(llm.tokenize(image_bytes)).decode('utf-8')}"}},
                    {"type": "text", "content": "Describe this image."}
                ]
            }
        ]
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