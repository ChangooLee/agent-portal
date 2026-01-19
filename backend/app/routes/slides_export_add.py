# Add these to slides.py after line 325

class ExportRequest(BaseModel):
    """Export request"""
    formats: List[str] = Field(["pptx"], description="Export formats: pptx, pdf")


@router.post("/{deck_id}/export")
@api_router.post("/{deck_id}/export")
async def export_deck(deck_id: str, request: ExportRequest):
    """Export deck to PPTX/PDF"""
    from fastapi.responses import FileResponse
    deck_state = slide_studio_repo.get_deck_state(deck_id)
    if not deck_state:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    # Get deck IR
    deck_ir = slide_studio_repo.get_deck_ir(deck_id)
    if not deck_ir:
        # Build deck IR from states
        from app.services.slide_studio.ir.schema import DeckIR
        slides_ir = [
            slide_state.ir
            for slide_state in deck_state.slides.values()
            if slide_state.ir
        ]
        deck_ir = DeckIR(
            deck_id=deck_id,
            title=deck_state.title,
            slides=slides_ir
        )
        slide_studio_repo.save_deck_ir(deck_ir)
    
    from app.services.slide_studio.export.pptx_exporter import pptx_exporter
    from app.services.slide_studio.export.pdf_exporter import pdf_exporter
    from app.services.slide_studio.store.artifact import artifact_storage
    import tempfile
    
    results = {}
    
    # Export PPTX
    if "pptx" in request.formats:
        try:
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                pptx_path = tmp.name
            
            pptx_exporter.export_deck(deck_ir, pptx_path)
            download_path = artifact_storage.save_pptx(deck_id, pptx_path)
            results["pptx"] = download_path
        except Exception as e:
            logger.error(f"PPTX export error: {e}")
            results["pptx"] = None
    
    # Export PDF
    if "pdf" in request.formats:
        pptx_file = artifact_storage.get_pptx_path(deck_id)
        if pptx_file:
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    pdf_path = tmp.name
                
                pdf_result = pdf_exporter.export_pptx_to_pdf(str(pptx_file), pdf_path)
                if pdf_result:
                    download_path = artifact_storage.save_pdf(deck_id, pdf_path)
                    results["pdf"] = download_path
                else:
                    results["pdf"] = None
            except Exception as e:
                logger.error(f"PDF export error: {e}")
                results["pdf"] = None
        else:
            results["pdf"] = None
    
    return {
        "status": "exported",
        "deck_id": deck_id,
        "formats": results
    }


@router.get("/{deck_id}/download/{format}")
@api_router.get("/{deck_id}/download/{format}")
async def download_artifact(deck_id: str, format: str):
    """Download exported artifact"""
    from fastapi.responses import FileResponse
    from app.services.slide_studio.store.artifact import artifact_storage
    
    if format == "pptx":
        file_path = artifact_storage.get_pptx_path(deck_id)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="PPTX file not found")
        return FileResponse(
            path=str(file_path),
            filename=f"{deck_id}.pptx",
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    elif format == "pdf":
        file_path = artifact_storage.get_pdf_path(deck_id)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        return FileResponse(
            path=str(file_path),
            filename=f"{deck_id}.pdf",
            media_type="application/pdf"
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
