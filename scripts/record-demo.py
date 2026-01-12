#!/usr/bin/env python3
"""
Record browser interactions and create animated GIF demo
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import subprocess
import os

async def record_demo():
    """Record a demo of Agent Portal interactions"""
    async with async_playwright() as p:
        # Launch browser with video recording
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir='./recordings/',
            record_video_size={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Get login credentials from environment or use defaults
        login_email = os.getenv('DEMO_LOGIN_EMAIL', 'lchangoo@gmail.com')
        login_password = os.getenv('DEMO_LOGIN_PASSWORD', 'xxxxxxxx')
        
        # Navigate directly to auth page to show login process
        print("Navigating to login page...")
        await page.goto('http://localhost:3010/auth', wait_until='networkidle')
        await asyncio.sleep(3)  # Wait for page to fully render
        
        # Check if we're redirected away (already logged in)
        current_url = page.url
        print(f"After navigation to /auth: {current_url}")
        
        if '/auth' not in current_url:
            print("⚠️  Already logged in (redirected away from /auth)")
            print("   Logging out first to show login process...")
            # Try to find logout button or go to settings
            try:
                # Look for user menu
                user_menu = page.locator('button').filter(has_text='User').or_(page.locator('[aria-label*="User"]')).first()
                if await user_menu.count() > 0:
                    await user_menu.click()
                    await asyncio.sleep(1)
                    # Look for logout/sign out
                    logout_btn = page.locator('button:has-text("Sign out"), button:has-text("Logout"), button:has-text("로그아웃")').first()
                    if await logout_btn.count() > 0:
                        await logout_btn.click()
                        await asyncio.sleep(2)
                        # Navigate back to auth
                        await page.goto('http://localhost:3010/auth', wait_until='networkidle')
                        await asyncio.sleep(3)
                        print("   ✅ Logged out, now on login page")
                    else:
                        print("   ⚠️  Could not find logout button, continuing...")
                else:
                    print("   ⚠️  Could not find user menu, trying direct auth access...")
                    # Force clear session by going to auth with query param
                    await page.goto('http://localhost:3010/auth?logout=true', wait_until='networkidle')
                    await asyncio.sleep(3)
            except Exception as e:
                print(f"   ⚠️  Logout attempt failed: {e}")
                print("   Continuing - might already be on login page...")
        
        # Final check - are we on auth page now?
        current_url = page.url
        if '/auth' not in current_url:
            print("⚠️  Still not on auth page - might be already logged in")
            print("   Will try to proceed with demo anyway...")
        else:
            print("✅ On login page, ready to perform login...")
        
        # Demo sequence
        print("Starting demo recording...")
        
        # 1. Perform login if needed
        current_url = page.url
        print(f"Current URL before login check: {current_url}")
        
        # If already logged in (not on /auth), skip login
        if '/auth' not in current_url:
            print("✅ Already logged in, proceeding with demo...")
        else:
            # We're on auth page, need to login
            print("Login required, performing login...")
            
            try:
                # Wait longer for Svelte to fully render the login form
                print("   Waiting for login form to render...")
                await asyncio.sleep(5)  # Give Svelte more time to render
                
                # Wait for email input specifically - this is the most reliable selector
                try:
                    # Wait for email input to appear
                    await page.wait_for_selector('input[type="email"]', timeout=15000, state='visible')
                    print("   ✅ Email input found")
                except:
                    # Check if we're still on auth page
                    current_check = page.url
                    if '/auth' not in current_check:
                        print("   ✅ Already logged in (redirected away from /auth), skipping login")
                        # Skip login and continue to demo
                    else:
                        # Try waiting for label text instead
                        try:
                            await page.wait_for_selector('label:has-text("Email"), label:has-text("이메일")', timeout=5000)
                            print("   Email label found, waiting for input...")
                            await asyncio.sleep(2)
                        except:
                            print("   ⚠️  Login form elements not found")
                            # Take screenshot
                            await page.screenshot(path='login-form-not-found.png', full_page=True)
                            print("   Screenshot saved to login-form-not-found.png")
                            # Check URL again
                            final_check = page.url
                            if '/auth' not in final_check:
                                print("   ✅ Redirected away - already logged in")
                            else:
                                raise Exception("Login form not found and still on /auth page")
                
                # Try to find all input fields to see what's available
                all_inputs = await page.locator('input').all()
                print(f"   Found {len(all_inputs)} input fields on page")
                
                # Find email input - use the most specific selector first
                email_input = None
                
                # Check if we're still on auth page (might have been redirected)
                current_url_check = page.url
                if '/auth' not in current_url_check:
                    print("   ✅ Already logged in, skipping login inputs")
                    email_input = None
                else:
                    # We're on auth page, find the email input
                    # Wait for "Email" label or placeholder text to appear first
                    try:
                        await page.wait_for_selector('input[type="email"], input[name="email"], label:has-text("Email"), label:has-text("이메일")', timeout=15000)
                        print("   ✅ Login form elements detected")
                    except:
                        print("   ⚠️  Login form elements not found, waiting longer...")
                        await asyncio.sleep(3)
                    
                    try:
                        email_input = page.locator('input[type="email"]').first()
                        await email_input.wait_for(state='visible', timeout=10000)
                        print("   ✅ Found email input with input[type='email']")
                    except:
                        try:
                            email_input = page.locator('input[name="email"]').first()
                            await email_input.wait_for(state='visible', timeout=10000)
                            print("   ✅ Found email input with input[name='email']")
                        except:
                            print("   ⚠️  Email input not found after waiting")
                            # Check URL again - might have been redirected
                            url_check = page.url
                            if '/auth' not in url_check:
                                print("   ✅ Redirected away - already logged in")
                                email_input = None
                            else:
                                # Take screenshot
                                await page.screenshot(path='email-input-not-found.png', full_page=True)
                                print("   Screenshot saved to email-input-not-found.png")
                                email_input = None
                
                if not email_input:
                    # Last resort: try to find any visible input
                    print("   Trying to find any visible input field...")
                    for i, inp in enumerate(all_inputs):
                        try:
                            if await inp.is_visible():
                                input_type = await inp.get_attribute('type')
                                input_name = await inp.get_attribute('name')
                                print(f"      Input {i}: type={input_type}, name={input_name}, visible=True")
                                if input_type != 'password':
                                    email_input = inp
                                    print(f"   ✅ Using input {i} as email field")
                                    break
                        except:
                            continue
                
                if not email_input:
                    # Take screenshot for debugging
                    await page.screenshot(path='login-debug-no-input.png', full_page=True)
                    print("   ⚠️  Could not find email input field")
                    print("   Checking if already logged in...")
                    # Check current URL
                    check_url = page.url
                    if '/auth' not in check_url:
                        print("   ✅ Not on auth page - already logged in!")
                        # Continue without login
                    else:
                        print("   ❌ Still on auth page but no input found")
                        print("   Screenshot saved to login-debug-no-input.png")
                        # Try to continue anyway - might work if already logged in
                        print("   Attempting to continue...")
                        await asyncio.sleep(2)
                        # Don't raise - try to continue
                        email_input = None  # Mark as not found but continue
                
                if email_input:
                    # Clear and fill email
                    await email_input.click()
                    await asyncio.sleep(0.3)
                    await email_input.fill('')  # Clear first
                    await asyncio.sleep(0.2)
                    await email_input.type(login_email, delay=50)  # Type character by character
                    await asyncio.sleep(0.5)
                    
                    # Verify email was entered
                    email_value = await email_input.input_value()
                    print(f"   Email entered: {email_value[:10]}...")
                else:
                    print("   Skipping email input (not found or already logged in)")
                    # Check if we're still on auth page
                    if '/auth' in page.url:
                        raise Exception("Email input not found but still on auth page")
                    # Otherwise continue (already logged in)
                
                # Find password input
                password_input = None
                password_selectors = [
                    'input[type="password"]',
                    'input[name="current-password"]',
                    'input[autocomplete="current-password"]'
                ]
                
                for selector in password_selectors:
                    try:
                        password_input = page.locator(selector).first()
                        if await password_input.count() > 0:
                            await password_input.wait_for(state='visible', timeout=5000)
                            print(f"   Found password input with selector: {selector}")
                            break
                    except:
                        continue
                
                if not password_input or await password_input.count() == 0:
                    if email_input:
                        raise Exception("Could not find password input field")
                    else:
                        print("   Skipping password input (email also not found - might be already logged in)")
                        password_input = None
                
                if password_input:
                    # Clear and fill password
                    await password_input.click()
                    await asyncio.sleep(0.3)
                    await password_input.fill('')  # Clear first
                    await asyncio.sleep(0.2)
                    await password_input.type(login_password, delay=50)  # Type character by character
                    await asyncio.sleep(0.5)
                    
                    # Verify password was entered (length check)
                    password_value = await password_input.input_value()
                    print(f"   Password entered: {'*' * len(password_value)} ({len(password_value)} chars)")
                else:
                    print("   Skipping password input")
                
                # Find and click submit button
                submit_button = None
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Sign in")',
                    'button:has-text("Authenticate")',
                    'button:has-text("로그인")',
                    'form button[type="submit"]'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = page.locator(selector).first()
                        if await submit_button.count() > 0:
                            await submit_button.wait_for(state='visible', timeout=3000)
                            print(f"   Found submit button with selector: {selector}")
                            break
                    except:
                        continue
                
                if email_input and password_input:
                    if not submit_button or await submit_button.count() == 0:
                        raise Exception("Could not find submit button")
                    
                    # Click submit
                    print("   Clicking submit button...")
                    await submit_button.click()
                    await asyncio.sleep(1)
                    
                    # Wait for navigation away from /auth
                    print("   Waiting for login to complete...")
                    try:
                        await page.wait_for_url(lambda url: '/auth' not in url, timeout=15000)
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)
                        print("✅ Login successful!")
                    except Exception as e:
                        current_url_after = page.url
                        if '/auth' in current_url_after:
                            print(f"⚠️  Still on auth page after login attempt: {current_url_after}")
                            print(f"   Error: {e}")
                            # Take a screenshot for debugging
                            await page.screenshot(path='login-debug.png')
                            print("   Screenshot saved to login-debug.png")
                        else:
                            print("✅ Login successful (redirect detected)")
                            await asyncio.sleep(2)
                else:
                    print("   Skipping login (inputs not found - might already be logged in)")
                    # Check if we're already logged in
                    current_check = page.url
                    if '/auth' not in current_check:
                        print("   ✅ Already logged in, proceeding...")
                    else:
                        print("   ⚠️  Still on auth page but inputs not found")
                        await asyncio.sleep(2)
                        
            except Exception as e:
                print(f"⚠️  Login attempt failed: {e}")
                import traceback
                traceback.print_exc()
                # Take screenshot for debugging
                try:
                    await page.screenshot(path='login-error.png', full_page=True)
                    print("   Error screenshot saved to login-error.png")
                except:
                    pass
                # Don't raise - try to continue anyway (might already be logged in)
                print("   Continuing anyway - might already be logged in...")
                await asyncio.sleep(2)
        else:
            print("Already logged in or redirected away from auth page")
        
        # 2. Wait for page to fully load after login
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        # 2. Click on "Use" tab (role tab) - try multiple selectors
        try:
            use_tab = page.get_by_role('button', name='Use').first()
            if await use_tab.count() > 0:
                await use_tab.click()
                await asyncio.sleep(1)
        except:
            try:
                await page.click('button:has-text("Use")', timeout=3000)
                await asyncio.sleep(1)
            except:
                print("Could not find Use tab, proceeding...")
        
        # 3. Navigate to Chat
        await page.goto('http://localhost:3010/c')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        # 4. Type a message in chat
        try:
            # Wait for textarea to be available
            textarea = page.locator('textarea').first()
            await textarea.wait_for(state='visible', timeout=5000)
            await textarea.fill('Hello, how can you help me?')
            await asyncio.sleep(1)
            
            # 5. Send message - try multiple selectors
            try:
                send_button = page.locator('button[type="submit"]').first()
                await send_button.click()
            except:
                # Try alternative: button with send icon or text
                send_button = page.locator('button').filter(has=page.locator('svg')).first()
                await send_button.click()
            
            await asyncio.sleep(4)  # Wait for response
        except Exception as e:
            print(f"Could not send message: {e}")
        
        # 6. Navigate to Build menu
        try:
            build_tab = page.get_by_role('button', name='Build').first()
            if await build_tab.count() > 0:
                await build_tab.click()
                await asyncio.sleep(2)
        except:
            try:
                await page.click('button:has-text("Build")', timeout=3000)
                await asyncio.sleep(2)
            except:
                print("Could not find Build tab, navigating directly...")
        
        # 7. Navigate to LLM management
        await page.goto('http://localhost:3010/build/llm')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        # 8. Navigate to Operate menu
        try:
            operate_tab = page.get_by_role('button', name='Operate').first()
            if await operate_tab.count() > 0:
                await operate_tab.click()
                await asyncio.sleep(2)
        except:
            try:
                await page.click('button:has-text("Operate")', timeout=3000)
                await asyncio.sleep(2)
            except:
                print("Could not find Operate tab, navigating directly...")
        
        # 9. Navigate to Monitoring page
        await page.goto('http://localhost:3010/operate/monitoring')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        print("Demo recording completed!")
        
        # Close browser (this will finalize the video)
        await context.close()
        await browser.close()
        
        # Find the recorded video file
        recordings_dir = Path('./recordings')
        video_files = list(recordings_dir.glob('*.webm'))
        
        if video_files:
            latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
            print(f"Video recorded: {latest_video}")
            
            # Convert to GIF using ffmpeg
            output_gif = Path('./webui/demo-new.gif')
            print("Converting to GIF...")
            
            # Check if ffmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], 
                             capture_output=True, check=True)
                
                subprocess.run([
                    'ffmpeg', '-i', str(latest_video),
                    '-vf', 'fps=10,scale=1280:-1:flags=lanczos',
                    '-y', str(output_gif)
                ], check=True)
                
                print(f"✅ GIF created: {output_gif}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"⚠️  ffmpeg not found. Video saved at: {latest_video}")
                print("   To convert to GIF, install ffmpeg:")
                print("   brew install ffmpeg")
                print("   Then run:")
                print(f"   ffmpeg -i {latest_video} -vf fps=10,scale=1280:-1:flags=lanczos -y {output_gif}")
        else:
            print("No video file found!")

if __name__ == '__main__':
    asyncio.run(record_demo())
