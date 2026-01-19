"""Artifact Storage - PPTX/PDF/Thumbnail storage"""
import logging
from pathlib import Path
from typing import Optional
from app.services.slide_studio.config import slide_studio_config

logger = logging.getLogger(__name__)


class ArtifactStorage:
    """Stores and retrieves artifacts (PPTX, PDF, thumbnails)"""
    
    def __init__(self):
        self.base_path = Path(slide_studio_config.ARTIFACT_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_pptx(self, deck_id: str, pptx_path: str) -> str:
        """
        Save PPTX file.
        
        Args:
            deck_id: Deck ID
            pptx_path: Path to PPTX file
            
        Returns:
            Relative path for download
        """
        deck_dir = self.base_path / deck_id
        deck_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = deck_dir / f"{deck_id}.pptx"
        Path(pptx_path).rename(target_path)
        
        return f"/slides/{deck_id}/download/pptx"
    
    def save_pdf(self, deck_id: str, pdf_path: str) -> str:
        """
        Save PDF file.
        
        Args:
            deck_id: Deck ID
            pdf_path: Path to PDF file
            
        Returns:
            Relative path for download
        """
        deck_dir = self.base_path / deck_id
        deck_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = deck_dir / f"{deck_id}.pdf"
        Path(pdf_path).rename(target_path)
        
        return f"/slides/{deck_id}/download/pdf"
    
    def get_pptx_path(self, deck_id: str) -> Optional[Path]:
        """Get PPTX file path"""
        pptx_file = self.base_path / deck_id / f"{deck_id}.pptx"
        return pptx_file if pptx_file.exists() else None
    
    def get_pdf_path(self, deck_id: str) -> Optional[Path]:
        """Get PDF file path"""
        pdf_file = self.base_path / deck_id / f"{deck_id}.pdf"
        return pdf_file if pdf_file.exists() else None


# Singleton instance
artifact_storage = ArtifactStorage()
