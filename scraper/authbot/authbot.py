"""
Standalone Upwork Authentication Bot
Refreshes headers and cookies when authentication expires.
"""

import json
import time
from seleniumbase import SB
import os
import sys

def get_upwork_headers():
    """Get Upwork headers using SeleniumBase (SB) for Cloudflare bypass"""
    headers_found = None
    graphql_url = "https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch"

    try:
        print("[*] Starting SeleniumBase browser (Cloudflare bypass)...")
        with SB(uc=True, test=True, locale="en", headless=True) as sb:
            url = "https://www.upwork.com/nx/search/jobs/?q=python%20developer"
            sb.activate_cdp_mode(url)
            print("[*] Waiting for Cloudflare challenge to complete...")

            # Loop until job cards are loaded (Cloudflare bypassed)
            max_attempts = 10
            for attempt in range(max_attempts):
                sb.sleep(20)
                # Try clicking the captcha checkbox if present
                try:
                    sb.uc_gui_click_captcha()
                    print(f"[*] Attempt {attempt+1}: Clicked Cloudflare verify checkbox")
                except Exception:
                    print(f"[*] Attempt {attempt+1}: No captcha checkbox found")
                # Check if job cards are loaded
                if sb.is_element_visible(".air3-card"):
                    print("[✓] Cloudflare bypassed successfully")
                    break
                # Optionally, check for "Just a moment..." text
                page_source = sb.get_page_source()
                if "Just a moment" not in page_source and "Challenge - Upwork" not in page_source:
                    print("[✓] 'Just a moment...' page bypassed")
                    break
            else:
                print("[!] Cloudflare challenge not bypassed after max attempts")
                return False

            # Step 1: Wait for job cards to load
            print("[*] Waiting for job cards to load...")
            try:
                sb.wait_for_element(".air3-card", timeout=30)
                print("[✓] Page 1 loaded with job cards")
                sb.sleep(180)  # Ensure all elements are loaded
            except Exception:
                print("[!] Timeout waiting for job cards - checking page content...")
                page_title = sb.get_title()
                current_url = sb.get_current_url()
                print(f"[!] Current page title: {page_title}")
                print(f"[!] Current URL: {current_url}")

            # Step 2: Inject network monitoring and click page 2
            print("[*] Looking for page 2 button...")
            monitor_script = """
            window.capturedRequests = [];
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                const url = args[0];
                const options = args[1] || {};
                if (typeof url === 'string' && url.includes('visitorJobSearch')) {
                    window.capturedRequests.push({
                        url: url,
                        headers: options.headers || {},
                        method: options.method || 'GET',
                        type: 'fetch'
                    });
                }
                return originalFetch.apply(this, args);
            };
            const originalXHROpen = XMLHttpRequest.prototype.open;
            const originalXHRSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
                this._method = method;
                this._url = url;
                this._headers = {};
                return originalXHROpen.apply(this, arguments);
            };
            XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
                this._headers[header] = value;
                return XMLHttpRequest.prototype.setRequestHeader.call(this, header, value);
            };
            XMLHttpRequest.prototype.send = function(data) {
                if (this._url && this._url.includes('visitorJobSearch')) {
                    window.capturedRequests.push({
                        url: this._url,
                        method: this._method,
                        headers: this._headers || {},
                        data: data,
                        type: 'xhr'
                    });
                }
                return originalXHRSend.apply(this, arguments);
            };
            """
            sb.execute_script(monitor_script)
            print("[✓] Network monitoring script injected")

            page_2_selectors = [
                'button[data-ev-page_index="2"]',
                'a[data-ev-page_index="2"]',
                'button[aria-label="Go to page 2"]',
                'a[aria-label="Go to page 2"]',
                '.pagination button:nth-child(3)',
                '.pagination a:nth-child(3)'
            ]
            page_2_selector = None
            for selector in page_2_selectors:
                try:
                    if sb.is_element_visible(selector):
                        page_2_selector = selector
                        print(f"[✓] Found page 2 button using selector: {selector}")
                        break
                except Exception:
                    continue

            if page_2_selector:
                sb.scroll_to_bottom()
                time.sleep(10)
                sb.scroll_to_element(page_2_selector)
                time.sleep(10)
                try:
                    sb.click(page_2_selector)
                    print("[✓] Clicked on page 2")
                except Exception as click_error:
                    print(f"[!] Regular click failed: {click_error}")
                    print("[*] Trying JavaScript click...")
                    sb.execute_script("document.querySelector(arguments[0]).click();", page_2_selector)
                    print("[✓] Clicked on page 2 with JavaScript")
                print("[*] Waiting for GraphQL request...")
                time.sleep(10)
            else:
                print("[!] Could not find page 2 button with any selector")
                return False

            # Step 3: Check captured requests from JavaScript
            print("[*] Analyzing captured network requests...")
            try:
                captured_requests = sb.execute_script("return window.capturedRequests || [];")
                print(f"[*] JavaScript captured {len(captured_requests)} requests")
                if captured_requests:
                    latest_request = captured_requests[-1]
                    headers_found = latest_request.get('headers', {})
                    if not headers_found or len(headers_found) == 0:
                        print("[*] No headers in captured request, creating basic headers...")
                        user_agent = sb.execute_script("return navigator.userAgent;")
                        headers_found = {
                            'Accept': 'application/json, text/plain, */*',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Content-Type': 'application/json',
                            'User-Agent': user_agent,
                            'Referer': sb.get_current_url(),
                            'Origin': 'https://www.upwork.com'
                        }
                    print(f"[✓] Found GraphQL request: {latest_request['url']}")
                    print(f"[✓] Request type: {latest_request.get('type', 'unknown')}")
                else:
                    print("[!] No requests were captured by JavaScript monitor")
                    print("[*] Creating fallback headers...")
                    user_agent = sb.execute_script("return navigator.userAgent;")
                    headers_found = {
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Content-Type': 'application/json',
                        'User-Agent': user_agent,
                        'Referer': sb.get_current_url(),
                        'Origin': 'https://www.upwork.com'
                    }
            except Exception as e:
                print(f"[!] Error retrieving captured requests: {e}")
                return False

            # Step 4: Also capture cookies for enhanced authentication
            print("[*] Capturing cookies...")
            try:
                cookies = {}
                for cookie in sb.get_cookies():
                    cookies[cookie['name']] = cookie['value']
                print(f"[✓] Captured {len(cookies)} cookies")
                
                # Save cookies to separate file
                cookies_file = os.path.join(os.path.dirname(__file__), "upwork_cookies.json")
                with open(cookies_file, "w") as f:
                    json.dump(cookies, f, indent=2)
                print(f"[✓] Cookies saved to {cookies_file}")
                
            except Exception as e:
                print(f"[!] Error capturing cookies: {e}")

    except Exception as e:
        print(f"[!] Error during automation: {e}")
        return False

    # Step 5: Save headers to file
    if headers_found:
        headers_file = os.path.join(os.path.dirname(__file__), "headers_upwork.json")
        with open(headers_file, "w") as f:
            json.dump(headers_found, f, indent=2)
        print(f"[✓] Headers saved to {headers_file}")
        
        # Also save to job_details_headers.json for compatibility
        job_details_headers_file = os.path.join(os.path.dirname(__file__), "job_details_headers.json")
        with open(job_details_headers_file, "w") as f:
            json.dump(headers_found, f, indent=2)
        print(f"[✓] Headers also saved to {job_details_headers_file}")
        
        return True
    else:
        print("[!] No headers found")
        return False

def main():
    """Main function for standalone execution"""
    print("=" * 70)
    print("UPWORK AUTHENTICATION BOT")
    print("=" * 70)
    
    try:
        success = get_upwork_headers()
        
        if success:
            print("[✅] Authentication refresh completed successfully!")
            print("[✅] Headers and cookies have been saved!")
            sys.exit(0)  # Success exit code
        else:
            print("[❌] Authentication refresh failed!")
            sys.exit(1)  # Failure exit code
            
    except KeyboardInterrupt:
        print("\n[!] Authentication bot interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        sys.exit(1)
    
    print("=" * 70)

# Run the function if script is executed directly
if __name__ == "__main__":
    main()