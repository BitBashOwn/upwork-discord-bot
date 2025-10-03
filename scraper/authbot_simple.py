#!/usr/bin/env python3
"""
Super Simple Upwork Authentication Bot for Ubuntu
Minimal approach with maximum compatibility
"""

import json
import time
import os
import sys
import platform
from seleniumbase import SB

def simple_upwork_auth():
    """Simple, robust authentication approach"""
    print("=" * 60)
    print("SIMPLE UPWORK AUTH - UBUNTU EDITION")
    print("=" * 60)
    
    # Try Firefox first (most stable on Linux)
    browsers = ["firefox", "chrome"]
    
    for browser in browsers:
        print(f"\n🌐 Trying {browser.title()}...")
        
        try:
            # Minimal, safe options
            with SB(test=True, headless=True, browser=browser) as sb:
                print(f"✅ {browser.title()} started successfully")
                
                # Navigate to Upwork
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                print(f"📍 Navigating to: {url}")
                sb.open(url)
                
                # Wait for page load
                print("⏳ Waiting for page load...")
                sb.sleep(8)
                
                # Check if we can get basic page info
                try:
                    current_url = sb.get_current_url()
                    print(f"📍 Current URL: {current_url}")
                except Exception:
                    current_url = "https://www.upwork.com"
                
                # Get user agent
                try:
                    user_agent = sb.execute_script("return navigator.userAgent;")
                    print(f"🌐 User Agent: {user_agent[:80]}...")
                except Exception:
                    if browser == "firefox":
                        user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
                    else:
                        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                    print(f"🌐 Fallback User Agent: {user_agent[:80]}...")
                
                # Create basic headers
                headers = {
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
                cookies = {}
                try:
                    for cookie in sb.get_cookies():
                        cookies[cookie['name']] = cookie['value']
                    print(f"🍪 Captured {len(cookies)} cookies")
                except Exception as e:
                    print(f"⚠️ Cookie capture failed: {e}")
                    cookies = {}
                
                # Save results
                script_dir = os.path.dirname(os.path.abspath(__file__))
                
                # Save headers
                headers_file = os.path.join(script_dir, "headers_upwork.json")
                with open(headers_file, "w") as f:
                    json.dump(headers, f, indent=2)
                print(f"💾 Headers saved: {headers_file}")
                
                # Save cookies
                cookies_file = os.path.join(script_dir, "upwork_cookies.json")
                with open(cookies_file, "w") as f:
                    json.dump(cookies, f, indent=2)
                print(f"💾 Cookies saved: {cookies_file}")
                
                # Also save compatibility files
                with open(os.path.join(script_dir, "job_details_headers.json"), "w") as f:
                    json.dump(headers, f, indent=2)
                with open(os.path.join(script_dir, "job_details_cookies.json"), "w") as f:
                    json.dump(cookies, f, indent=2)
                print("💾 Compatibility files saved")
                
                print(f"\n✅ SUCCESS with {browser.title()}!")
                print(f"📊 Headers: {len(headers)} keys")
                print(f"📊 Cookies: {len(cookies)} keys")
                print("🎉 Ready to run the main bot!")
                
                return True
                
        except Exception as e:
            print(f"❌ {browser.title()} failed: {e}")
            continue
    
    print("\n❌ All browsers failed!")
    print("💡 Troubleshooting tips:")
    print("1. Check if Firefox is installed: firefox --version")
    print("2. Check virtual display: echo $DISPLAY")
    print("3. Try running with: DISPLAY=:99 python3 authbot_simple.py")
    return False

def main():
    start_time = time.time()
    
    try:
        success = simple_upwork_auth()
        elapsed = time.time() - start_time
        
        print(f"\n⏱️ Total time: {elapsed:.2f} seconds")
        
        if success:
            print("✅ Authentication completed!")
            return 0
        else:
            print("❌ Authentication failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 2
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())