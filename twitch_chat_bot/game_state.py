"""
Game State Management for Twitch Chat Bot
Tracks player information and game state for tournament-style gaming.
"""
from dataclasses import dataclass, field
from typing import Optional
import logging

LOGGER = logging.getLogger(__name__)


@dataclass
class Fighter:
    """Represents a worm in the game"""
    name: str = "FighterName"
    health: int = 3
    wins: int = 0
    
    def reset_health(self, health: int = 3) -> None:
        """Reset player health to specified amount"""
        self.health = health
        LOGGER.info(f"Reset {self.name}'s health to {health}")
    
    def reset_wins(self) -> None:
        """Reset player wins to 0"""
        self.wins = 0
        LOGGER.info(f"Reset {self.name}'s wins to 0")

    def take_damage(self, damage: int) -> None:
        """Apply damage to player"""
        self.health = max(0, self.health - damage)
        LOGGER.info(f"{self.name} took {damage} damage, health now: {self.health}")
    
    def heal(self, amount: int) -> None:
        """Heal player by specified amount"""
        self.health = min(100, self.health + amount)
        LOGGER.info(f"{self.name} healed {amount}, health now: {self.health}")
    
    def add_win(self) -> None:
        """Add a win to player's record"""
        self.wins += 1
        LOGGER.info(f"{self.name} won! Total wins: {self.wins}")
    
    def is_alive(self) -> bool:
        """Check if player is still alive"""
        return self.health > 0
    
    def to_dict(self) -> dict:
        """Convert player to dictionary"""
        return {
            "name": self.name,
            "health": self.health,
            "wins": self.wins
        }


@dataclass
class GameState:
    """Manages the overall game state"""
    p1: Fighter = field(default_factory=Fighter)
    p2: Fighter = field(default_factory=Fighter)
    
    def set_players(self, p1_name: str, p2_name: str) -> None:
        """Set player names and initialize game"""
        self.p1.name = p1_name
        self.p2.name = p2_name
        self.reset_game()
        LOGGER.info(f"Set players: {p1_name} vs {p2_name}")
    
    def reset_game(self) -> None:
        """Reset the game state"""
        self.p1.reset_health()
        self.p2.reset_health()
        self.p1.reset_wins()
        self.p2.reset_wins()
        LOGGER.info(f"Game reset")
    
    def end_game(self, winner: Optional[Fighter] = None) -> None:
        """End the current game"""
        if winner:
            winner.add_win()
            LOGGER.info(f"Game ended - {winner.name} wins!")
        else:
            LOGGER.info("Game ended - No winner")
    
    def check_game_over(self) -> bool:
        """Check if game is over and return winner if any"""
        if not self.p1.is_alive() and not self.p2.is_alive():
            # Draw
            self.end_game()
            return True
        elif not self.p1.is_alive():
            # P2 wins
            self.end_game(self.p2)
            return True
        elif not self.p2.is_alive():
            # P1 wins
            self.end_game(self.p1)
            return True
    
    def get_player_by_name(self, name: str) -> Optional[Fighter]:
        """Get player by name"""
        if self.p1.name.lower() == name.lower():
            return self.p1
        elif self.p2.name.lower() == name.lower():
            return self.p2
        return None
    
    def to_dict(self) -> dict:
        """Convert game state to dictionary"""
        return {
            "p1": self.p1.to_dict(),
            "p2": self.p2.to_dict(),
            "current_round": self.current_round
        }
    
    def get_status(self) -> str:
        """Get formatted status string"""
        return (f"Round {self.current_round} | "
                f"{self.p1.name}: {self.p1.health}HP ({self.p1.wins}W) | "
                f"{self.p2.name}: {self.p2.health}HP ({self.p2.wins}W)")


# Global game state instance
game_state = GameState()
