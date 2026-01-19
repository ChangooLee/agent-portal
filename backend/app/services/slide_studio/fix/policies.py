"""Reflection Loop Policies"""
from app.services.slide_studio.config import slide_studio_config
from app.services.slide_studio.ir.schema import SlideIR, QualityMetrics


class ReflectionPolicies:
    """Policies for reflection loop control"""
    
    def should_reflect(
        self,
        slide_ir: SlideIR,
        metrics: QualityMetrics,
        score: float,
        reflection_count: int
    ) -> bool:
        """
        Determine if slide should go through reflection.
        
        Args:
            slide_ir: Slide IR
            metrics: Quality metrics
            score: Current quality score
            reflection_count: Number of reflections already done
            
        Returns:
            True if should reflect
        """
        # Max reflection loops
        if reflection_count >= slide_studio_config.MAX_REFLECTION_LOOPS:
            return False
        
        # Score threshold
        if score >= slide_studio_config.MIN_SCORE_THRESHOLD:
            # Check for error issues
            error_issues = [
                issue for issue in slide_ir.issues
                if issue.get("severity") == "error"
            ]
            if not error_issues:
                return False  # Good enough
        
        # Has error issues -> must reflect
        error_issues = [
            issue for issue in slide_ir.issues
            if issue.get("severity") == "error"
        ]
        if error_issues:
            return True
        
        # Score below threshold -> reflect
        if score < slide_studio_config.MIN_SCORE_THRESHOLD:
            return True
        
        return False
    
    def should_finalize_with_warnings(
        self,
        slide_ir: SlideIR,
        metrics: QualityMetrics,
        score: float,
        reflection_count: int
    ) -> bool:
        """
        Determine if slide should be finalized with warnings.
        
        Args:
            slide_ir: Slide IR
            metrics: Quality metrics
            score: Current quality score
            reflection_count: Number of reflections already done
            
        Returns:
            True if should finalize with warnings
        """
        # Max reflections reached
        if reflection_count >= slide_studio_config.MAX_REFLECTION_LOOPS:
            # Has warnings but no errors
            error_issues = [
                issue for issue in slide_ir.issues
                if issue.get("severity") == "error"
            ]
            if not error_issues:
                return True
        
        return False


# Singleton instance
reflection_policies = ReflectionPolicies()
