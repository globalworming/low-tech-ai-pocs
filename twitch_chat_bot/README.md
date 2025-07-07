# Minimal Twitch Chat Bot

Stream Twitch chat with minimal functionality:
- Store latest `P1:` and `P2:` messages per user (max 200 chars)
- POST to cloud function every 60 seconds
- Clear messages after successful POST

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Twitch Application
1. Go to [Twitch Developer Console](https://dev.twitch.tv/console)
2. Create new application
3. Set callback URL: `http://localhost:3000/auth/callback`
4. Note your `CLIENT_ID` and `CLIENT_SECRET`

### 3. Configure Environment Variables
Create `.env` file or set environment variables:
```bash
TWITCH_CLIENT_ID=your_client_id_here
TWITCH_CLIENT_SECRET=your_client_secret_here
TWITCH_BOT_ID=your_bot_user_id
TWITCH_OWNER_ID=your_personal_user_id
CLOUD_FUNCTION_URL=https://your-cloud-function-url
```

### 4. OAuth Setup (Automatic)
The bot uses AutoBot for automatic OAuth handling:
1. Run the bot: `python bot.py`
2. Bot starts OAuth server on `localhost:4343`
3. Visit `http://localhost:4343/oauth?scopes=user:read:chat%20user:write:chat%20user:bot&force_verify=true` (as bot account)
4. Visit `http://localhost:4343/oauth?scopes=channel:bot&force_verify=true` (as your account)
5. Tokens are automatically stored in `tokens.db`

### 5. Run Bot
```bash
python bot.py
```

**Note**: OAuth tokens are automatically managed - no manual token generation needed!

## Usage

- Users type `P1: message` to store P1 message
- Users type `P2: message` to store P2 message
- Bot posts all stored messages to cloud function every 60 seconds
- Messages are cleared after successful POST

## Cloud Function Payload

The bot sends JSON payload:
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "p1_messages": {
    "username1": "message content",
    "username2": "another message"
  },
  "p2_messages": {
    "username1": "p2 message content"
  }
}
```
