"""
LLM client for image description generation.
"""
import time
from typing import Dict, Any, Optional
from pathlib import Path
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

from .config import DEFAULT_MODEL_PARAMS, DEFAULT_GEN_PARAMS

def format_time(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s"

class LLMClient:
    """Client for interacting with the LLaMA language model."""
    
    def __init__(self, model_path: str, mmproj_path: str, **kwargs):
        """
        Initialize the LLM client.
        
        Args:
            model_path: Path to the LLaMA model file.
            mmproj_path: Path to the multimodal projection file.
            **kwargs: Additional arguments to pass to the Llama constructor.
        """
        # Set default parameters and update with any overrides
        params = DEFAULT_MODEL_PARAMS.copy()
        params.update(kwargs)
        
        # Initialize the chat handler for multimodal support
        chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)
        
        # Initialize the LLM
        self.llm = Llama(
            model_path=model_path,
            chat_handler=chat_handler,
            **params
        )
        
        # Store generation parameters
        self.gen_params = DEFAULT_GEN_PARAMS.copy()
    
    def describe_image(
        self, 
        image_path: str, 
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a description for an image.
        
        Args:
            image_path: Path to the image file.
            system_prompt: System prompt to use. If None, a default is used.
            user_prompt: User prompt to use. If None, a default is used.
            **kwargs: Additional generation parameters.
            
        Returns:
            Dictionary containing the generated description and metadata.
        """
        # Set default prompts if not provided
        if system_prompt is None:
            system_prompt = """You are an image analysis assistant that outputs structured JSON.
            Analyze the image and provide a JSON object with three keys:
            1. "summary": A brief one-sentence overview of the image.
            2. "setting": A description of the background, location, and lighting.
            3. "objects": An array of JSON objects, where each object has "item" (the name of the object), 
               "color" (its primary color), and "position" (e.g., "center", "top-left", "foreground")."""
        
        if user_prompt is None:
            user_prompt = "office material on a table. describe all objects in the image and their positions to each other"
        
        # Read and encode the image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_base64 = image_bytes.hex()
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "content": user_prompt}
                ]
            }
        ]
        
        # Set generation parameters
        gen_params = self.gen_params.copy()
        gen_params.update(kwargs)
        
        # Generate the description
        print("\nGenerating description...")
        start_time = time.time()
        
        response = self.llm.create_chat_completion(
            messages=messages,
            stream=True,
            **gen_params
        )
        
        # Process the streaming response
        full_response = ""
        tokens_received = 0
        start_gen_time = time.time()
        
        for chunk in response:
            delta = chunk['choices'][0]['delta']
            if 'content' in delta:
                token = delta['content']
                full_response += token
                tokens_received += 1
                
                # Update progress every 5 tokens
                if tokens_received % 5 == 0:
                    elapsed = time.time() - start_gen_time
                    tokens_per_sec = tokens_received / elapsed if elapsed > 0 else 0
                    remaining = max(0, len(full_response) * 0.75)  # Estimate remaining tokens
                    eta = remaining / tokens_per_sec if tokens_per_sec > 0 else 0
                    
                    print(f"\rTokens: {tokens_received} | "
                          f"Speed: {tokens_per_sec:.1f} tokens/s | "
                          f"ETA: {format_time(eta)}   ", 
                          end='', flush=True)
        
        # Calculate final statistics
        total_time = time.time() - start_time
        avg_speed = tokens_received / total_time if total_time > 0 else 0
        
        print(f"\n\nGeneration complete! Total time: {format_time(total_time)}")
        print(f"Average speed: {avg_speed:.1f} tokens/s")
        
        return {
            "content": full_response,
            "tokens_generated": tokens_received,
            "generation_time": total_time,
            "tokens_per_second": avg_speed
        }
