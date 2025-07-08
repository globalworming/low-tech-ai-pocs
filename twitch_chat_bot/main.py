import asyncio
import json
import random
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Initialize FastAPI app
app = FastAPI(title="Twitch Chat Bot SSE Server")

# Message broker using asyncio.Queue
message_queue: asyncio.Queue = asyncio.Queue()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class FighterUpdate(BaseModel):
    fighter: str
    description: str

class TestEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Twitch Chat Bot SSE Server is running"}

@app.get("/events")
async def stream_events(request: Request):
    """
    SSE endpoint that streams events to connected clients.
    Keeps connection alive and sends messages from the queue.
    """
    async def event_generator():
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break
            
            try:
                # Wait for a message in the queue with timeout
                message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                
                # Format message for SSE
                event_data = {
                    "id": str(random.randint(100000, 999999)),
                    "event": message.get("event_type", "update"),
                    "data": json.dumps(message.get("data", {}))
                }
                
                yield event_data
                
            except asyncio.TimeoutError:
                # Send keepalive ping every second
                yield {
                    "event": "ping",
                    "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})
                }
    
    return EventSourceResponse(event_generator())

@app.get("/start_round")
async def start_round(duration: int = 50):
    """
    start the on screen countdown
    """
    message = {
        "event_type": "start_round",
        "data": {
            "timestamp": asyncio.get_event_loop().time(),
            "duration": duration
        }
    }
    
    await message_queue.put(message)
    
    return {"status": "success", "message": "Round started"}

@app.get("/think")
async def think(p1: str = "what next", p2: str = "what next"):
    message = {
        "event_type": "think",
        "data": {
            "timestamp": asyncio.get_event_loop().time(),
            "p1": p1,
            "p2": p2
        }
    }
    
    await message_queue.put(message)
    
    return {"status": "success", "message": "updated thinking"}

@app.get("/show")
async def show(summary: str = "FIXME"):
    message = {
        "event_type": "show",
        "data": {
            "timestamp": asyncio.get_event_loop().time(),
            "summary": summary
        }
    }
    
    await message_queue.put(message)
    
    return {"status": "success", "message": "show result"}

@app.get("/hide")
async def hide():
    message = {
        "event_type": "hide",
        "data": {
            "timestamp": asyncio.get_event_loop().time(),
        }
    }
    
    await message_queue.put(message)
    
    return {"status": "success", "message": "hide result"}

@app.get("/state")
async def state(p1Name: str = "P1", p2Name: str = "P2", p1Health: int = 3, p2Health: int = 3, p1Wins: int = 0, p2Wins: int = 0):
    """
    Update game state information
    Example: /state?p1Name=Fighter1&p2Name=Fighter2&p1Health=2&p2Health=3&p1Wins=1&p2Wins=0
    """
    message = {
        "event_type": "state",
        "data": {
            "timestamp": asyncio.get_event_loop().time(),
            "p1Name": p1Name,
            "p2Name": p2Name,
            "p1Health": p1Health,
            "p2Health": p2Health,
            "p1Wins": p1Wins,
            "p2Wins": p2Wins
        }
    }
    await message_queue.put(message)
    return {"status": "success", "message": "state updated"}

@app.post("/update_fighter")
async def update_fighter(fighter_data: FighterUpdate):
    """
    update fighter information
    """
    message = {
        "event_type": "fighter_update",
        "data": {
            "fighter": fighter_data.fighter,
            "description": fighter_data.description,
            "timestamp": asyncio.get_event_loop().time()
        }
    }
    
    await message_queue.put(message)
    
    return {"status": "success", "message": "Fighter updated and events queued"}

@app.get("/test_event")
async def trigger_test_event():
    """
    Endpoint to manually trigger a test event.
    """
    await send_random_test_event()
    return {"status": "success", "message": "Test event sent"}

async def send_random_test_event():
    """
    Helper function to send a random SSE event for testing.
    """
    test_events = [
        {
            "event_type": "fighter_update",
            "data": {
                "fighter": f"fighter{random.randint(1, 2)}",
                "description": f"Test update from server: {random.randint(1, 1000)}",
                "timestamp": asyncio.get_event_loop().time()
            }
        },
    ]
    
    random_event = random.choice(test_events)
    await message_queue.put(random_event)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "queue_size": message_queue.qsize(),
        "timestamp": asyncio.get_event_loop().time()
    }

# Background task to send periodic test events (optional)
@app.on_event("startup")
async def startup_event():
    """
    Optional: Start background task for periodic events
    """
    print("SSE Server started successfully!")
    print("Available endpoints:")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
