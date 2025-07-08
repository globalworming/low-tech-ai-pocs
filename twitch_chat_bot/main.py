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
                    "id": str(random.randint(1000, 9999)),
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

@app.post("/update_fighter")
async def update_fighter(fighter_data: FighterUpdate):
    """
    Test endpoint to update fighter information.
    Puts data into the queue which will be sent via SSE.
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
    
    # Generate a random additional event for testing
    await send_random_test_event()
    
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
    print("  - GET  /events - SSE stream")
    print("  - POST /update_fighter - Update fighter data")
    print("  - POST /test_event - Trigger test event")
    print("  - GET  /health - Health check")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
