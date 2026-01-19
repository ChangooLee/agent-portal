"""Repository for storing deck/slide state"""
from typing import Dict, Optional
from app.services.slide_studio.orchestrator.state import DeckState
from app.services.slide_studio.ir.schema import DeckIR
from app.services.slide_studio.ir.versioning import version_manager


class SlideStudioRepo:
    """In-memory repository for deck/slide state (Step 1)"""
    
    def __init__(self):
        # In-memory storage (dict)
        # In production, this would be Redis or DB
        self._decks: Dict[str, DeckState] = {}
        self._deck_irs: Dict[str, DeckIR] = {}
    
    def save_deck_state(self, deck_state: DeckState):
        """Save deck state"""
        self._decks[deck_state.deck_id] = deck_state
    
    def get_deck_state(self, deck_id: str) -> Optional[DeckState]:
        """Get deck state by ID"""
        return self._decks.get(deck_id)
    
    def save_deck_ir(self, deck_ir: DeckIR, create_version: bool = False):
        """Save deck IR"""
        self._deck_irs[deck_ir.deck_id] = deck_ir
        if create_version:
            version_manager.save_version(deck_ir.deck_id, deck_ir)
    
    def get_deck_ir(self, deck_id: str) -> Optional[DeckIR]:
        """Get deck IR by ID"""
        return self._deck_irs.get(deck_id)
    
    def delete_deck(self, deck_id: str):
        """Delete deck (cleanup)"""
        if deck_id in self._decks:
            del self._decks[deck_id]
        if deck_id in self._deck_irs:
            del self._deck_irs[deck_id]


# Singleton instance
slide_studio_repo = SlideStudioRepo()
