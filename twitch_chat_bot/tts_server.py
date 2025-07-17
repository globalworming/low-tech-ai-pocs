import asyncio
import hashlib
import os
import io
import soundfile as sf
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response
import outetts

# Initialize FastAPI app
app = FastAPI(title="TTS Server")

# Directory to store generated WAV files
WAV_DIR = Path("tts_cache")
WAV_DIR.mkdir(exist_ok=True)

# Global TTS interface
interface = None
speaker = None

# Track of ongoing generations to prevent duplicates
generating: Dict[str, asyncio.Event] = {}

def init_tts():
    """Initialize the TTS interface and speaker"""
    global interface, speaker
    
    interface = outetts.Interface(
        config=outetts.ModelConfig.auto_config(
            model=outetts.Models.VERSION_1_0_SIZE_1B,
            backend=outetts.Backend.LLAMACPP,
            quantization=outetts.LlamaCppQuantization.FP16
        )
    )

def text_to_filename(speakerJson: str, text: str) -> str:
    """Convert text to a safe filename using hash"""
    # Create a hash of the text for consistent filename
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"{text_hash}.wav"

async def generate_tts_async(text: str, filename: str, speakerJson: str = "speek.json") -> None:

        
    # Load speaker configuration
    speaker = interface.load_speaker(speakerJson)

    """Generate TTS audio asynchronously"""
    try:
        # Generate audio
        output = interface.generate(
            config=outetts.GenerationConfig(
                text=text,
                speaker=speaker
            )
        )
        
        # Save to file
        filepath = WAV_DIR / filename
        output.save(str(filepath))
        
        # Mark generation as complete
        if text in generating:
            generating[text].set()
            
    except Exception as e:
        print(f"Error generating TTS for '{text}': {e}")
        # Clean up on error
        if text in generating:
            generating[text].set()

@app.on_event("startup")
async def startup_event():
    """Initialize TTS on startup"""
    init_tts()
    print("TTS Server started successfully!")

@app.get("/tts")
async def get_tts(text: str = Query(..., description="Text to convert to speech"), speakerJson: str = "speak.json"):
    """
    Get TTS audio for the given text.
    
    Returns:
    - 200: WAV file if it exists
    - 503: Service unavailable if generation is in progress
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty")
    filename = text_to_filename(speakerJson, text)
    filepath = WAV_DIR / filename
    
    # Check if file already exists
    if filepath.exists():
        # Return the existing WAV file
        with open(filepath, "rb") as f:
            wav_data = f.read()
        
        return Response(
            content=wav_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "public, max-age=3600"
            }
        )
    
    # Check if generation is already in progress
    if text in generating:
        raise HTTPException(
            status_code=503, 
            detail="Audio generation in progress, please try again later"
        )
    
    # Start generation
    generating[text] = asyncio.Event()
    
    # Start async generation task
    asyncio.create_task(generate_tts_async(text, filename, speakerJson))
    
    raise HTTPException(
        status_code=503,
        detail="Audio generation started, please try again in a few seconds"
    )

@app.get("/status")
async def get_status():
    """Get server status and cache info"""
    cache_files = list(WAV_DIR.glob("*.wav"))
    return {
        "status": "running",
        "cache_size": len(cache_files),
        "generating_count": len(generating),
        "cache_files": [f.name for f in cache_files]
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TTS Server is running",
        "usage": "GET /tts?text=your_text_here&speakerJson=speak.json"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
