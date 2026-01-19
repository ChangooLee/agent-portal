"""Quality Metrics Calculation"""
from app.services.slide_studio.ir.schema import SlideIR, QualityMetrics
from app.services.slide_studio.verify.heuristic import heuristic_verifier
from app.services.slide_studio.config import slide_studio_config


class QualityMetricsCalculator:
    """Calculates quality metrics for slides"""
    
    def calculate_metrics(self, slide_ir: SlideIR) -> QualityMetrics:
        """
        Calculate quality metrics for a slide.
        
        Args:
            slide_ir: Slide IR
            
        Returns:
            QualityMetrics
        """
        issues = heuristic_verifier.verify_slide(slide_ir)
        
        overflow_count = sum(1 for issue in issues if issue.get("type") == "overflow")
        overlap_count = sum(1 for issue in issues if issue.get("type") == "overlap")
        margin_violation_count = sum(1 for issue in issues if issue.get("type") == "margin_violation")
        
        # Find min font size
        min_font_size = None
        for slot in slide_ir.slots.values():
            if hasattr(slot, 'style') and slot.style and slot.style.font_size:
                if min_font_size is None or slot.style.font_size < min_font_size:
                    min_font_size = slot.style.font_size
        
        # Count text slots
        text_slot_count = sum(
            1 for slot in slide_ir.slots.values()
            if slot.slot_type in ["text", "bullet"]
        )
        total_slot_count = len(slide_ir.slots)
        
        # Calculate native text ratio
        native_text_ratio = text_slot_count / total_slot_count if total_slot_count > 0 else 0.0
        
        # Estimate max text per slide
        max_text_per_slide = sum(
            len(slot.content) if hasattr(slot, 'content') else 0
            for slot in slide_ir.slots.values()
            if slot.slot_type == "text"
        )
        
        return QualityMetrics(
            overflow_count=overflow_count,
            overlap_count=overlap_count,
            margin_violation_count=margin_violation_count,
            min_font_size=min_font_size,
            max_text_per_slide=max_text_per_slide,
            native_text_ratio=native_text_ratio
        )
    
    def calculate_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate quality score (0-100).
        
        엄격한 평가 기준 적용:
        - overflow: -15 (심각한 문제)
        - overlap: -20 (매우 심각)
        - font_too_small: -8
        - 콘텐츠 품질 페널티 추가 예정
        
        Args:
            metrics: QualityMetrics
            
        Returns:
            Score (0-100)
        """
        score = 100.0
        
        # Penalties (엄격화)
        score -= metrics.overflow_count * 15.0  # -15 per overflow (기존 -10)
        score -= metrics.overlap_count * 20.0  # -20 per overlap (기존 -15)
        score -= metrics.margin_violation_count * 3.0  # -3 per margin violation (기존 -2)
        
        # Font size penalty (강화)
        if metrics.min_font_size and metrics.min_font_size < slide_studio_config.MIN_FONT_SIZE:
            score -= 8.0  # 기존 -5
        
        # Text per slide penalty (if too much)
        if metrics.max_text_per_slide and metrics.max_text_per_slide > 1000:
            score -= 5.0
        
        # Native text ratio bonus (축소)
        if metrics.native_text_ratio >= slide_studio_config.TARGET_NATIVE_TEXT_RATIO:
            score += 3.0  # 기존 +5
        
        # 콘텐츠 품질 페널티 (if slide_ir available)
        # Note: We need to pass slide_ir separately since QualityMetrics doesn't include it
        # For now, this is called from orchestrator with slide_ir context
        
        return max(0.0, min(100.0, score))


# Singleton instance
quality_metrics_calculator = QualityMetricsCalculator()
