"""Playwright Verifier (Optional) - Advanced DOM-based verification"""
import logging
from typing import List, Dict, Any, Optional
from app.services.slide_studio.ir.schema import SlideIR
from app.services.slide_studio.preview.renderer import preview_renderer

logger = logging.getLogger(__name__)


class PlaywrightVerifier:
    """Playwright-based verification (optional)"""
    
    def __init__(self):
        self.available = self._check_availability()
        self._playwright_available = self.available
    
    def _check_availability(self) -> bool:
        """Check if Playwright is available"""
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            logger.warning("Playwright not available, skipping advanced verification")
            return False
    
    def verify_slide_with_playwright(self, slide_ir: SlideIR) -> List[Dict[str, Any]]:
        """
        Verify slide using Playwright (synchronous version for compatibility).
        
        Args:
            slide_ir: Slide IR
            
        Returns:
            List of issues found
        """
        if not self.available:
            return []
        
        try:
            from playwright.sync_api import sync_playwright
            
            # Render HTML
            html = preview_renderer.render_html(slide_ir)
            
            issues = []
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set viewport to slide size
                page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Load HTML
                page.set_content(html)
                page.wait_for_timeout(500)  # Wait for fonts
                
                # Check overflow
                overflow_issues = self._check_overflow_dom(page)
                issues.extend(overflow_issues)
                
                # Check overlap
                overlap_issues = self._check_overlap_dom(page)
                issues.extend(overlap_issues)
                
                browser.close()
            
            return issues
            
        except Exception as e:
            logger.error(f"Playwright verification failed: {e}")
            return []
    
    def _check_overflow_dom(self, page) -> List[Dict[str, Any]]:
        """Check overflow using DOM"""
        issues = []
        try:
            overflow_elements = page.evaluate("""
                () => {
                    const elements = [];
                    document.querySelectorAll('.slide-preview > *').forEach(el => {
                        const rect = el.getBoundingClientRect();
                        const parent = el.parentElement;
                        const parentRect = parent.getBoundingClientRect();
                        if (rect.right > parentRect.right || rect.bottom > parentRect.bottom ||
                            rect.left < parentRect.left || rect.top < parentRect.top) {
                            elements.push({
                                class: el.className,
                                overflow: true
                            });
                        }
                    });
                    return elements;
                }
            """)
            
            for elem in overflow_elements:
                issues.append({
                    "type": "overflow",
                    "severity": "error",
                    "message": f"Element {elem['class']} overflows container"
                })
        except Exception as e:
            logger.error(f"Overflow check failed: {e}")
        return issues
    
    def _check_overlap_dom(self, page) -> List[Dict[str, Any]]:
        """Check overlap using DOM"""
        issues = []
        try:
            overlaps = page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('.slide-preview > *');
                    const overlaps = [];
                    for (let i = 0; i < elements.length; i++) {
                        for (let j = i + 1; j < elements.length; j++) {
                            const rect1 = elements[i].getBoundingClientRect();
                            const rect2 = elements[j].getBoundingClientRect();
                            if (!(rect1.right < rect2.left || rect1.left > rect2.right ||
                                  rect1.bottom < rect2.top || rect1.top > rect2.bottom)) {
                                overlaps.push({
                                    element1: elements[i].className,
                                    element2: elements[j].className
                                });
                            }
                        }
                    }
                    return overlaps;
                }
            """)
            
            for overlap in overlaps:
                issues.append({
                    "type": "overlap",
                    "severity": "error",
                    "message": f"Elements {overlap['element1']} and {overlap['element2']} overlap"
                })
        except Exception as e:
            logger.error(f"Overlap check failed: {e}")
        return issues
    
    async def verify_slide(
        self,
        slide_ir: SlideIR,
        html_preview: str
    ) -> List[Dict[str, Any]]:
        """
        Verify slide using Playwright DOM inspection.
        
        Args:
            slide_ir: Slide IR
            html_preview: HTML preview string
            
        Returns:
            List of issues
        """
        if not self.available:
            return []
        
        issues = []
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Load HTML preview
                await page.set_content(html_preview)
                
                # Check for overflow
                overflow_elements = await page.evaluate("""
                    () => {
                        const elements = [];
                        document.querySelectorAll('*').forEach(el => {
                            if (el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight) {
                                elements.push({
                                    tag: el.tagName,
                                    class: el.className,
                                    overflowX: el.scrollWidth > el.clientWidth,
                                    overflowY: el.scrollHeight > el.clientHeight
                                });
                            }
                        });
                        return elements;
                    }
                """)
                
                for elem in overflow_elements:
                    issues.append({
                        "severity": "error",
                        "type": "dom_overflow",
                        "message": f"Element {elem['tag']} overflows container",
                        "details": elem
                    })
                
                # Check for overlaps
                overlaps = await page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll('[class*="slot"]');
                        const overlaps = [];
                        for (let i = 0; i < elements.length; i++) {
                            for (let j = i + 1; j < elements.length; j++) {
                                const rect1 = elements[i].getBoundingClientRect();
                                const rect2 = elements[j].getBoundingClientRect();
                                if (!(rect1.right < rect2.left || rect1.left > rect2.right ||
                                      rect1.bottom < rect2.top || rect1.top > rect2.bottom)) {
                                    overlaps.push({
                                        element1: elements[i].className,
                                        element2: elements[j].className
                                    });
                                }
                            }
                        }
                        return overlaps;
                    }
                """)
                
                for overlap in overlaps:
                    issues.append({
                        "severity": "error",
                        "type": "dom_overlap",
                        "message": "Elements overlap in DOM",
                        "details": overlap
                    })
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Playwright verification error: {e}")
        
        return issues


# Singleton instance
playwright_verifier = PlaywrightVerifier()
