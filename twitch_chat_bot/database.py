import asqlite
from twitchio import eventsub
from config import BOT_ID
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

async def setup_database(db: asqlite.Pool) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    """Setup token database and return existing tokens/subscriptions"""
    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    
    async with db.acquire() as connection:
        await connection.execute(query)
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")
        
        tokens = []
        subs = []
        
        for row in rows:
            tokens.append((row["token"], row["refresh"]))
            subs.extend([eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=BOT_ID)])
    
    return tokens, subs
