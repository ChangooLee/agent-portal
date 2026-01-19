"""PDF Exporter - PPTX to PDF"""
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PDFExporter:
    """Exports PPTX to PDF using LibreOffice headless"""
    
    def export_pptx_to_pdf(self, pptx_path: str, pdf_path: str) -> Optional[str]:
        """
        Convert PPTX to PDF using LibreOffice headless.
        
        Args:
            pptx_path: Path to PPTX file
            pdf_path: Path to output PDF file
            
        Returns:
            Path to PDF file or None if failed
        """
        try:
            # Check if LibreOffice is available
            try:
                subprocess.run(
                    ["libreoffice", "--version"],
                    capture_output=True,
                    check=True
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("LibreOffice not available, PDF export skipped")
                return None
            
            # Convert using LibreOffice headless
            output_dir = Path(pdf_path).parent
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(output_dir),
                    pptx_path
                ],
                capture_output=True,
                check=True
            )
            
            # LibreOffice creates PDF with same name but .pdf extension
            expected_pdf = Path(pptx_path).with_suffix('.pdf')
            if expected_pdf.exists():
                # Move to desired path if different
                if str(expected_pdf) != pdf_path:
                    expected_pdf.rename(pdf_path)
                logger.info(f"Exported PDF to {pdf_path}")
                return pdf_path
            else:
                logger.error(f"PDF file not created at {expected_pdf}")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"LibreOffice conversion error: {e}")
            return None
        except Exception as e:
            logger.error(f"PDF export error: {e}")
            return None


# Singleton instance
pdf_exporter = PDFExporter()
