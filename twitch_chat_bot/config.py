"""Configuration file for Twitch Chat Bot"""
import os

# Twitch API Configuration
CLIENT_ID = os.getenv('TWITCH_CLIENT_ID', 'your_client_id_here')
CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET', 'your_client_secret_here')
BOT_ID = os.getenv('TWITCH_BOT_ID', 'your_bot_id_here')
OWNER_ID = os.getenv('TWITCH_OWNER_ID', 'your_owner_id_here')

BOT_NAME = os.getenv('TWITCH_BOT_NAME', 'your_bot_name')

# Cloud Function Configuration
CLOUD_FUNCTION_URL = os.getenv('CLOUD_FUNCTION_URL', 'your_cloud_function_url_here')

# Bot Settings
MESSAGE_MAX_LENGTH = 200
POST_INTERVAL_SECONDS = 60
