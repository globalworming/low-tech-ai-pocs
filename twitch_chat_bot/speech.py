import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from elevenlabs.client import ElevenLabs
from elevenlabs import play

# Initialize FastAPI app
app = FastAPI(title="Speech TTS Server")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ElevenLabs client
elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Speech TTS Server is running"}

@app.get("/tts")
async def text_to_speech(text: str):
    """Convert text to speech using ElevenLabs and play it"""
    try:
        # Convert text to speech
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id="N2lVS1w4EtoT3dr4eOWO",
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128",
        )
        
        # Play the audio
        play(audio)
        
        return {
            "message": "Audio generated and played successfully",
            "text": text,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating speech: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)