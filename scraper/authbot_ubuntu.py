#!/usr/bin/env python3
"""
Ubuntu Server Optimized Upwork Authentication Bot
Designed specifically for headless Linux environments
"""

import json
import time
import os
import sys
import platform
from seleniumbase import SB

def setup_virtual_display():
    """Setup virtual display for headless operation"""
    if platform.system().lower() == 'linux':
        try:
            import subprocess
            # Check if Xvfb is available
            subprocess.run(['which', 'Xvfb'], check=True, capture_output=True)
            
            # Set display environment variable
            os.environ['DISPLAY'] = ':99'
            
            # Check if Xvfb is already running
            try:
                subprocess.run(['pgrep', 'Xvfb'], check=True, capture_output=True)
                print("[Ubuntu Bot] ✅ Virtual display already running")
            except subprocess.CalledProcessError:
                # Start Xvfb
                print("[Ubuntu Bot] Starting virtual display...")
                subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1920x1080x24'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2)
                print("[Ubuntu Bot] ✅ Virtual display started")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[Ubuntu Bot] ⚠️ Xvfb not available, continuing without virtual display")

def get_upwork_headers_ubuntu():
    """Ubuntu-optimized header capture"""
    headers_found = None
    cookies_found = None
    
    # Setup virtual display for Linux
    setup_virtual_display()
    
    # Try browsers in Linux-optimized order
    browsers_to_try = ["firefox", "chrome"]
    
    for browser in browsers_to_try:
        print(f"[Ubuntu Bot] Attempting {browser.title()} browser...")
        
        try:
            # Browser configuration optimized for Ubuntu servers
            browser_options = {
                "uc": False,  # Disable UC mode for better compatibility
                "test": True,
                "locale": "en",
                "headless": True,  # Always headless on servers
                "browser": browser,
                "page_load_strategy": "eager"
            }
            
            with SB(**browser_options) as sb:
                print("[Ubuntu Bot] Browser started successfully")
                
                # Skip CDP commands for Firefox, use only for Chrome  
                if browser == "chrome":
                    try:
                        sb.driver.execute_cdp_cmd('Runtime.enable', {})
                        print("[Ubuntu Bot] ✅ Chrome optimizations applied")
                    except Exception:
                        print("[Ubuntu Bot] ⚠️ Chrome optimizations not available, continuing...")
                elif browser == "firefox":
                    print("[Ubuntu Bot] ✅ Firefox mode - no CDP commands needed")
                
                # Navigate to Upwork
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                sb.open(url)
                print(f"[Ubuntu Bot] Navigated to: {url}")
                
                # Wait for page load
                print("[Ubuntu Bot] Waiting for page load...")
                sb.sleep(8)
                
                # Handle Cloudflare if present
                print("[Ubuntu Bot] Checking for challenges...")
                for attempt in range(3):
                    try:
                        page_source = sb.get_page_source()
                        if any(phrase in page_source.lower() for phrase in 
                               ["just a moment", "checking your browser", "cloudflare"]):
                            print(f"[Ubuntu Bot] Challenge detected, waiting... (attempt {attempt+1})")
                            sb.sleep(10)
                        else:
                            print("[Ubuntu Bot] ✅ No challenge detected")
                            break
                    except Exception as e:
                        print(f"[Ubuntu Bot] Page check error: {e}")
                        sb.sleep(5)
                
                # Wait for job elements
                job_selectors = [
                    ".air3-card",
                    "[data-test='job-tile']",
                    ".job-tile",
                    ".up-card"
                ]
                
                jobs_found = False
                for selector in job_selectors:
                    try:
                        sb.wait_for_element(selector, timeout=15)
                        print(f"[Ubuntu Bot] ✅ Jobs found with selector: {selector}")
                        jobs_found = True
                        break
                    except Exception:
                        continue
                
                if not jobs_found:
                    print("[Ubuntu Bot] ⚠️ No job elements found, continuing with basic approach")
                
                # Get browser info
                try:
                    user_agent = sb.execute_script("return navigator.userAgent;")
                    current_url = sb.get_current_url()
                    print(f"[Ubuntu Bot] Current URL: {current_url}")
                except Exception as e:
                    print(f"[Ubuntu Bot] Browser info error: {e}")
                    user_agent = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ({browser.title()})"
                    current_url = "https://www.upwork.com"
                
                # Create headers
                headers_found = {
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Content-Type': 'application/json',
                    'User-Agent': user_agent,
                    'Referer': current_url,
                    'Origin': 'https://www.upwork.com',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin'
                }
                
                # Get cookies
                try:
                    cookies = {}
                    for cookie in sb.get_cookies():
                        cookies[cookie['name']] = cookie['value']
                    cookies_found = cookies
                    print(f"[Ubuntu Bot] ✅ Captured {len(cookies)} cookies from {browser}")
                    
                    # Success - break out of browser loop
                    print(f"[Ubuntu Bot] ✅ Successfully captured credentials with {browser.title()}!")
                    break
                    
                except Exception as e:
                    print(f"[Ubuntu Bot] Cookie capture error: {e}")
                    cookies_found = {}
                    
        except Exception as e:
            print(f"[Ubuntu Bot] ❌ {browser.title()} failed: {e}")
            continue
    
    # Save results
    if headers_found and cookies_found is not None:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Save headers
            headers_file = os.path.join(script_dir, "headers_upwork.json")
            with open(headers_file, "w") as f:
                json.dump(headers_found, f, indent=2)
            print(f"[Ubuntu Bot] ✅ Headers saved to {headers_file}")
            
            # Save cookies
            cookies_file = os.path.join(script_dir, "upwork_cookies.json") 
            with open(cookies_file, "w") as f:
                json.dump(cookies_found, f, indent=2)
            print(f"[Ubuntu Bot] ✅ Cookies saved to {cookies_file}")
            
            # Also save to job_details files for compatibility
            with open(os.path.join(script_dir, "job_details_headers.json"), "w") as f:
                json.dump(headers_found, f, indent=2)
            with open(os.path.join(script_dir, "job_details_cookies.json"), "w") as f:
                json.dump(cookies_found, f, indent=2)
            
            print(f"[Ubuntu Bot] 📊 Summary:")
            print(f"[Ubuntu Bot] Headers: {len(headers_found)} keys")
            print(f"[Ubuntu Bot] Cookies: {len(cookies_found)} keys")
            print(f"[Ubuntu Bot] User-Agent: {headers_found.get('User-Agent', 'N/A')[:80]}...")
            
            return True
            
        except Exception as e:
            print(f"[Ubuntu Bot] ❌ Save error: {e}")
            return False
    else:
        print("[Ubuntu Bot] ❌ Failed to capture credentials")
        return False

def main():
    """Main function for Ubuntu server"""
    print("=" * 60)
    print("UPWORK BOT - UBUNTU SERVER EDITION")
    print("=" * 60)
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        success = get_upwork_headers_ubuntu()
        elapsed_time = time.time() - start_time
        
        print(f"\n[Ubuntu Bot] Execution time: {elapsed_time:.2f} seconds")
        
        if success:
            print("[Ubuntu Bot] ✅ Authentication completed successfully!")
            print("[Ubuntu Bot] Ready to run the main bot!")
            return 0
        else:
            print("[Ubuntu Bot] ❌ Authentication failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n[Ubuntu Bot] ⚠️ Interrupted by user")
        return 2
    except Exception as e:
        print(f"[Ubuntu Bot] ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())