#!/usr/bin/env python3
"""
Create animated GIF from sequential screenshots
Uses browser automation to capture each step
"""
import asyncio
from playwright.async_api import async_playwright
from PIL import Image
import glob
from pathlib import Path

async def capture_demo_steps():
    """Capture screenshots of each interaction step"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        screenshots_dir = Path('./demo-screenshots')
        screenshots_dir.mkdir(exist_ok=True)
        
        step = 0
        
        # Step 1: Initial page
        await page.goto('http://localhost:3010')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 2: Click Use menu
        await page.click('button:has-text("Use")')
        await asyncio.sleep(1)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 3: Navigate to chat
        await page.click('a[href*="/c"]', timeout=5000)
        await asyncio.sleep(2)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 4: Type message
        await page.fill('textarea[placeholder*="Message"]', 'Hello!')
        await asyncio.sleep(0.5)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 5: Send message
        await page.click('button[type="submit"]', timeout=5000)
        await asyncio.sleep(3)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 6: Build menu
        await page.click('button:has-text("Build")')
        await asyncio.sleep(1)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 7: LLM management
        await page.click('a[href*="/build/llm"]', timeout=5000)
        await asyncio.sleep(2)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 8: Operate menu
        await page.click('button:has-text("Operate")')
        await asyncio.sleep(1)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        step += 1
        
        # Step 9: Monitoring
        await page.click('a[href*="/operate/monitoring"]', timeout=5000)
        await asyncio.sleep(2)
        await page.screenshot(path=f'{screenshots_dir}/step_{step:02d}.png')
        
        await browser.close()
        
        # Create GIF from screenshots
        print("Creating GIF from screenshots...")
        images = []
        for img_path in sorted(glob.glob(f'{screenshots_dir}/step_*.png')):
            images.append(Image.open(img_path))
        
        if images:
            output_gif = Path('./webui/demo-from-screenshots.gif')
            images[0].save(
                output_gif,
                save_all=True,
                append_images=images[1:],
                duration=1000,  # 1 second per frame
                loop=0
            )
            print(f"GIF created: {output_gif}")

if __name__ == '__main__':
    asyncio.run(capture_demo_steps())
