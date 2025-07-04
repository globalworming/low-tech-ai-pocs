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
            system_prompt = """
# summary
You are computer vison model that analyzes images and responds with structured JSON. Scenes usually revolve around office material on a wooden table.

## tone
- neutral
- professional
- blunt
- direct

## focus on
- verifiable physical properties like:
    - shapes
    - colors
    - size
    - count
    - relative positions
    - location

## response format
example for a single sticky note on a table with a marker next to it
```json
{
    "summary": "a sticky note on a table",
    "objects": [
        {
            "name": "sticky note",
            "color": "yellow",
            "shape": "rectangular",
            "size": "small",
            "count": 1,
            "relative_position": "on the table close to the marker",
            "location": "center of the table"
        },
        {
            "name": "marker",
            "color": "black",
            "shape": "pen",
            "size": "small",
            "count": 1,
            "relative_position": "left of yellow sticky note",
            "location": "table center left"
        }
    ]
}
```

## stop
- when you are done
- when you repeat yourself
"""
        
        if user_prompt is None:
            user_prompt = "Analyze this image and provide JSON according to the schema `Image Description Schema`"
        
        # Read and encode the image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        import base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
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
                #print(full_response)
                
                # Update progress every 5 tokens
                if tokens_received % 25 == 0:
                    elapsed = time.time() - start_gen_time
                    tokens_per_sec = tokens_received / elapsed if elapsed > 0 else 0
                    remaining = max(0, gen_params['max_tokens'] - tokens_received)  # Estimate remaining tokens
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
        
        # Parse and return the JSON response
        if not full_response.strip():
            print("Warning: Empty response from LLM")
            return {
                "error": "Empty response from LLM",
                "summary": "",
                "setting": "",
                "objects": []
            }
        
        try:
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON content between ```json and ``` or just parse the whole response
            json_match = re.search(r'```json\s*({.*?})\s*```', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON-like content
                json_match = re.search(r'{.*}', full_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = full_response.strip()
            
            result = json.loads(json_str)
            print(f"\nParsed JSON successfully: {json.dumps(result, indent=2)}")
            return result
            
        except json.JSONDecodeError as e:
            print(f"\nFailed to parse JSON: {e}")
            print(f"Raw response: {repr(full_response)}")
            return {
                "error": f"JSON parsing failed: {str(e)}",
                "raw_response": full_response,
                "summary": "",
                "setting": "",
                "objects": []
            }
