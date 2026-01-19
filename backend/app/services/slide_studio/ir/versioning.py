"""Versioning - Snapshot/Restore/Diff"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.slide_studio.ir.schema import DeckIR

logger = logging.getLogger(__name__)


class Version:
    """Version snapshot"""
    def __init__(self, version_id: str, label: str, deck_ir: DeckIR, created_at: datetime):
        self.version_id = version_id
        self.label = label
        self.deck_ir = deck_ir
        self.created_at = created_at


class VersionManager:
    """Manages deck versions"""
    
    def __init__(self):
        self.versions: Dict[str, List[Version]] = {}  # deck_id -> versions
    
    def save_version(self, deck_id: str, deck_ir: DeckIR, label: Optional[str] = None) -> str:
        """
        Save version snapshot.
        
        Args:
            deck_id: Deck ID
            deck_ir: Deck IR to snapshot
            label: Optional label
            
        Returns:
            Version ID
        """
        import uuid
        version_id = str(uuid.uuid4())
        
        if not label:
            label = f"v{len(self.versions.get(deck_id, [])) + 1}"
        
        version = Version(
            version_id=version_id,
            label=label,
            deck_ir=deck_ir.model_copy(deep=True),  # Deep copy
            created_at=datetime.now()
        )
        
        if deck_id not in self.versions:
            self.versions[deck_id] = []
        
        self.versions[deck_id].append(version)
        
        return version_id
    
    def get_versions(self, deck_id: str) -> List[Dict[str, Any]]:
        """Get all versions for deck"""
        versions = self.versions.get(deck_id, [])
        return [
            {
                "version_id": v.version_id,
                "label": v.label,
                "created_at": v.created_at.isoformat(),
                "slide_count": len(v.deck_ir.slides)
            }
            for v in versions
        ]
    
    def get_version(self, deck_id: str, version_id: str) -> Optional[DeckIR]:
        """Get specific version"""
        versions = self.versions.get(deck_id, [])
        for version in versions:
            if version.version_id == version_id:
                return version.deck_ir.model_copy(deep=True)
        return None
    
    def restore_version(self, deck_id: str, version_id: str) -> Optional[DeckIR]:
        """Restore version (returns DeckIR)"""
        return self.get_version(deck_id, version_id)
    
    def diff_versions(
        self,
        deck_id: str,
        version_id1: str,
        version_id2: str
    ) -> Dict[str, Any]:
        """Calculate diff between two versions"""
        v1 = self.get_version(deck_id, version_id1)
        v2 = self.get_version(deck_id, version_id2)
        
        if not v1 or not v2:
            return {"error": "Version not found"}
        
        # Simple diff (for Step 6)
        diff = {
            "slide_count_diff": len(v2.slides) - len(v1.slides),
            "slides_added": [],
            "slides_removed": [],
            "slides_modified": []
        }
        
        # Compare slides
        v1_slide_ids = {s.slide_id for s in v1.slides}
        v2_slide_ids = {s.slide_id for s in v2.slides}
        
        diff["slides_added"] = list(v2_slide_ids - v1_slide_ids)
        diff["slides_removed"] = list(v1_slide_ids - v2_slide_ids)
        
        # Find modified slides
        for slide2 in v2.slides:
            if slide2.slide_id in v1_slide_ids:
                slide1 = next(s for s in v1.slides if s.slide_id == slide2.slide_id)
                if slide1.model_dump_json() != slide2.model_dump_json():
                    diff["slides_modified"].append(slide2.slide_id)
        
        return diff


# Singleton instance
version_manager = VersionManager()
