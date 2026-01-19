"""Fact Check Service (Optional)"""
import logging
from typing import List, Dict, Any
from app.services.slide_studio.ir.schema import SlideIR, DeckIR

logger = logging.getLogger(__name__)


class FactChecker:
    """Checks facts in slides against provided documents"""
    
    async def check_deck(
        self,
        deck_ir: DeckIR,
        documents: List[str] = None
    ) -> Dict[str, Any]:
        """
        Check facts in deck.
        
        Args:
            deck_ir: Deck IR
            documents: List of document texts for verification
            
        Returns:
            Fact check results
        """
        claims = []
        verified = []
        unverified = []
        
        # Extract claims from slides
        for slide in deck_ir.slides:
            for slot in slide.slots.values():
                if hasattr(slot, 'content'):
                    # Simple claim extraction (for Step 7)
                    # In production, this would use LLM to extract claims
                    claims.append({
                        "slide_id": slide.slide_id,
                        "slot_id": getattr(slot, 'slot_id', 'unknown'),
                        "claim": slot.content[:100] + "..." if len(slot.content) > 100 else slot.content,
                        "source": "generated"
                    })
        
        # For Step 7, mark all as unverified
        # In production, this would verify against documents
        unverified = claims
        
        return {
            "deck_id": deck_ir.deck_id,
            "claims": claims,
            "verified": verified,
            "unverified": unverified,
            "verification_rate": len(verified) / len(claims) if claims else 0.0
        }
    
    async def check_slide(
        self,
        slide_ir: SlideIR,
        documents: List[str] = None
    ) -> Dict[str, Any]:
        """Check facts in single slide"""
        # Similar to check_deck but for single slide
        claims = []
        
        for slot in slide_ir.slots.values():
            if hasattr(slot, 'content'):
                claims.append({
                    "slot_id": getattr(slot, 'slot_id', 'unknown'),
                    "claim": slot.content[:100] + "..." if len(slot.content) > 100 else slot.content,
                    "source": "generated"
                })
        
        return {
            "slide_id": slide_ir.slide_id,
            "claims": claims,
            "verified": [],
            "unverified": claims
        }


# Singleton instance
fact_checker = FactChecker()
