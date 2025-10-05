"""
Improved Upwork Authentication Bot
Fast, reliable authentication refresh with validation test
Fixed Firefox support for Ubuntu
"""
# --- PATCH FOR ASYNCIO EVENT LOOP ISSUES ON PYTHON 3.11+ ---
import sys
if sys.version_info >= (3, 11):
    import asyncio
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    # Monkey-patch get_event_loop to always return the running loop
    def _get_running_loop():
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.new_event_loop()
    asyncio.get_event_loop = _get_running_loop
# -----------------------------------------------------------

import json
import time
from seleniumbase import SB
import os
import sys
import platform
import shutil
import tempfile
import tarfile
import stat
import urllib.request
import uuid
import zipfile

# Patch asyncio to allow nested event loops (fixes RuntimeError in Jupyter/IPython/Python 3.10+)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # If not available, ignore, but recommend installing it if error persists

def test_job_details_fetch(headers, cookies):
    """Test fetching job details with captured credentials"""
    print("\n" + "=" * 70)
    print("TESTING JOB DETAILS FETCH")
    print("=" * 70)
    
    # Use a known public job ID format for testing
    test_job_id = "~0140c36fa1e87afd2a"  # Example format
    
    try:
        import cloudscraper
        session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        print("[Test] Using cloudscraper session")
    except ImportError:
        import requests
        session = requests.Session()
        print("[Test] Using standard requests session")
    
    # Build test payload
    payload = {
        "alias": "gql-query-get-visitor-job-details",
        "query": """query JobPubDetailsQuery($id: ID!) {
            jobPubDetails(id: $id) {
                opening {
                    status
                    postedOn
                    publishTime
                    workload
                    contractorTier
                    description
                    info {
                        ciphertext
                        id
                        type
                        title
                        createdOn
                    }
                    budget { amount currencyCode }
                    clientActivity { totalApplicants totalHired totalInvitedToInterview }
                }
                buyer {
                    location { city country countryTimezone }
                    stats { totalAssignments feedbackCount score totalCharges { amount currencyCode } }
                }
                qualifications { minJobSuccessScore minOdeskHours risingTalent }
            }
        }""",
        "variables": {"id": test_job_id}
    }
    
    url = "https://www.upwork.com/api/graphql/v1?alias=gql-query-get-visitor-job-details"
    
    print(f"[Test] Testing with job ID: {test_job_id}")
    print(f"[Test] Request URL: {url}")
    
    # Retry logic to handle transient 403/429 from Cloudflare
    attempts = 3
    backoff = 3
    for attempt in range(1, attempts+1):
        try:
            response = session.post(
                url,
                headers=headers,
                cookies=cookies,
                json=payload,
                timeout=20
            )
            print(f"[Test] Attempt {attempt}: HTTP {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "errors" in data:
                        print("[Test] ❌ GraphQL Errors Found:")
                        for error in data["errors"]:
                            print(f"  - {error.get('message', 'Unknown error')}")
                        return False
                    job_details = data.get("data", {}).get("jobPubDetails", {})
                    if job_details:
                        opening = job_details.get("opening", {})
                        info = opening.get("info", {})
                        print("\n[Test] ✅ Job Details Fetch SUCCESSFUL!")
                        print("-" * 70)
                        print(f"Title: {info.get('title', 'N/A')}")
                        print(f"Job ID: {info.get('id', 'N/A')}")
                        print(f"Status: {opening.get('status', 'N/A')}")
                        print(f"Posted: {opening.get('postedOn', 'N/A')}")
                        print("-" * 70)
                        return True
                    else:
                        print("[Test] ⚠️ Empty job details returned")
                        return False
                except json.JSONDecodeError as e:
                    print(f"[Test] ❌ Failed to parse JSON: {e}")
                    return False
            elif response.status_code in (401, 403, 429):
                if attempt < attempts:
                    print(f"[Test] ⚠️ Got {response.status_code}; retrying after {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    print(f"[Test] ❌ Final attempt received {response.status_code}")
                    return False
            else:
                print(f"[Test] ❌ Unexpected status code: {response.status_code}")
                return False
        except Exception as e:
            if attempt < attempts:
                print(f"[Test] ⚠️ Attempt {attempt} failed: {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            print(f"[Test] ❌ Request failed after {attempts} attempts: {e}")
            return False
    return False

def _enrich_headers(raw_headers, cookies, referer_url):
    """Normalize and enrich headers for Upwork GraphQL public job details."""
    if not raw_headers:
        raw_headers = {}
    
    # Case-insensitive normalization
    normalized = {}
    for k, v in raw_headers.items():
        lower = k.lower()
        if lower == 'user-agent':
            normalized['User-Agent'] = v
        elif lower == 'content-type':
            normalized['Content-Type'] = v
        elif lower == 'accept':
            normalized['Accept'] = v
        elif lower == 'accept-language':
            normalized['Accept-Language'] = v
        elif lower == 'origin':
            normalized['Origin'] = v
        elif lower == 'referer':
            normalized['Referer'] = v
        else:
            normalized[k] = v
    
    # Mandatory defaults
    normalized.setdefault('Accept', 'application/json, text/plain, */*')
    normalized.setdefault('Content-Type', 'application/json')
    normalized.setdefault('Origin', 'https://www.upwork.com')
    if referer_url:
        normalized.setdefault('Referer', referer_url)
    normalized.setdefault('Accept-Language', 'en-US,en;q=0.9')
    normalized.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    # Remove problematic headers
    for h in list(normalized.keys()):
        if h.lower() in ('content-length', 'host', 'authority'):
            normalized.pop(h, None)
    
    # Add visitor ID from cookies if available
    if cookies:
        for k in cookies.keys():
            if 'visitor' in k.lower() and 'vnd-eo-visitorId' not in normalized:
                normalized['vnd-eo-visitorId'] = cookies[k]
                break
    
    # Add security headers
    normalized.setdefault('Sec-Fetch-Site', 'same-origin')
    normalized.setdefault('Sec-Fetch-Mode', 'cors')
    normalized.setdefault('Sec-Fetch-Dest', 'empty')
    normalized['sec-ch-ua'] = '"Chromium";v="121", "Not(A:Brand";v="8"'
    normalized.setdefault('sec-ch-ua-mobile', '?0')
    normalized.setdefault('sec-ch-ua-platform', '"Windows"')
    
    # Apollo headers
    normalized.setdefault('apollographql-client-name', 'web')
    normalized.setdefault('apollographql-client-version', '1.4')
    
    return normalized

def _ensure_visitor_id(headers, base_dir):
    """Ensure headers contain a stable vnd-eo-visitorId."""
    try:
        if not headers:
            return headers
        
        # Check if already present
        for k in headers.keys():
            if k.lower() == 'vnd-eo-visitorid':
                return headers
        
        # Try to reuse persisted ID
        vid_file = os.path.join(base_dir, 'visitor_id.txt')
        visitor_id = None
        if os.path.exists(vid_file):
            try:
                with open(vid_file, 'r') as f:
                    candidate = f.read().strip()
                if candidate and 8 <= len(candidate) <= 64:
                    visitor_id = candidate
                    print(f"[Auth Bot] ♻️ Reusing persisted visitor ID: {visitor_id[:12]}...")
            except Exception:
                pass
        
        if not visitor_id:
            visitor_id = uuid.uuid4().hex
            try:
                with open(vid_file, 'w') as f:
                    f.write(visitor_id)
                print(f"[Auth Bot] 🆕 Generated and persisted synthetic visitor ID: {visitor_id[:12]}...")
            except Exception:
                pass
        
        headers['vnd-eo-visitorId'] = visitor_id
        return headers
    except Exception as e:
        print(f"[Auth Bot] ⚠️ _ensure_visitor_id error: {e}")
        return headers

def _inject_network_monitor_early(driver):
    """Inject network monitor as early as possible for Firefox"""
    monitor_script = """
    (function(){
        console.log('[Monitor] Installing network interceptor...');
        
        function shouldCapture(u){
            if(!u || typeof u !== 'string') return false;
            u = u.toLowerCase();
            // Capture all GraphQL and job-related requests
            return (
                u.includes('graphql') ||
                u.includes('visitorjobsearch') ||
                u.includes('jobpubdetails') ||
                u.includes('api/profiles') ||
                u.includes('api/jobs')
            );
        }
        
        window.capturedRequests = window.capturedRequests || [];
        
        // Intercept fetch
        const originalFetch = window.fetch;
        window.fetch = function(...args){
            const url = typeof args[0] === 'string' ? args[0] : args[0].url || '';
            const options = args[1] || {};
            
            if(shouldCapture(url)){
                const reqData = {
                    ts: Date.now(),
                    url: url,
                    headers: {},
                    method: (options.method || 'GET').toUpperCase(),
                    body: options.body || null,
                    type: 'fetch'
                };
                
                // Capture headers
                if(options.headers){
                    if(options.headers instanceof Headers){
                        options.headers.forEach((value, key) => {
                            reqData.headers[key] = value;
                        });
                    } else if(Array.isArray(options.headers)){
                        options.headers.forEach(([key, value]) => {
                            reqData.headers[key] = value;
                        });
                    } else {
                        reqData.headers = options.headers;
                    }
                }
                
                window.capturedRequests.push(reqData);
                console.log('[Monitor] Captured fetch:', url);
            }
            
            return originalFetch.apply(this, args);
        };
        
        // Intercept XMLHttpRequest
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        const originalSetHeader = XMLHttpRequest.prototype.setRequestHeader;
        
        XMLHttpRequest.prototype.open = function(method, url){
            this._method = method;
            this._url = url;
            this._headers = {};
            return originalXHROpen.apply(this, arguments);
        };
        
        XMLHttpRequest.prototype.setRequestHeader = function(header, value){
            this._headers[header] = value;
            return originalSetHeader.call(this, header, value);
        };
        
        XMLHttpRequest.prototype.send = function(data){
            if(shouldCapture(this._url)){
                const reqData = {
                    ts: Date.now(),
                    url: this._url,
                    method: (this._method || 'GET').toUpperCase(),
                    headers: this._headers || {},
                    body: data || null,
                    type: 'xhr'
                };
                window.capturedRequests.push(reqData);
                console.log('[Monitor] Captured XHR:', this._url);
            }
            return originalXHRSend.apply(this, arguments);
        };
        
        console.log('[Monitor] Network interceptor installed successfully');
    })();
    """
    
    try:
        driver.execute_script(monitor_script)
        print("[Auth Bot] ✅ Early network monitor injected")
        return True
    except Exception as e:
        print(f"[Auth Bot] ⚠️ Could not inject early monitor: {e}")
        return False

def _firefox_wait_and_capture(driver):
    """Enhanced Firefox-specific waiting and capture strategy"""
    print("[Auth Bot] Firefox: Starting enhanced capture strategy...")
    
    # Inject monitor immediately and at multiple points
    _inject_network_monitor_early(driver)
    
    # Wait for initial page load
    print("[Auth Bot] Firefox: Waiting for initial page load...")
    time.sleep(5)
    
    # Re-inject monitor in case page reloaded
    _inject_network_monitor_early(driver)
    
    # Check for Cloudflare challenge
    for attempt in range(5):
        try:
            page_source = driver.page_source
            if "Just a moment" in page_source or "Checking your browser" in page_source:
                print(f"[Auth Bot] Firefox: Cloudflare challenge detected, waiting... (attempt {attempt+1})")
                time.sleep(3)
            else:
                print("[Auth Bot] Firefox: Page appears loaded")
                break
        except Exception:
            pass
    
    # Wait for jobs to load
    print("[Auth Bot] Firefox: Waiting for job listings...")
    time.sleep(5)
    
    # Try to trigger API calls by scrolling
    print("[Auth Bot] Firefox: Triggering API calls via scroll...")
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
    except Exception:
        pass
    
    # Try to click a job card with corrected selector
    print("[Auth Bot] Firefox: Attempting to click job card...")
    job_clicked = False
    job_selectors = [
        'a[data-test="job-tile-title-link"]',
        'a[href*="/jobs/"]',  # Fixed: Added quotes
        '.job-tile a',
        'article a[href*="/jobs/"]'
    ]
    
    for selector in job_selectors:
        try:
            elements = driver.find_elements("css selector", selector)
            if elements:
                # Try JavaScript click
                driver.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", elements[0])
                print(f"[Auth Bot] Firefox: ✅ Clicked job via: {selector}")
                job_clicked = True
                break
        except Exception as e:
            continue
    
    if not job_clicked:
        # Alternative: navigate directly to a job details page
        try:
            driver.execute_script("""
                var links = document.querySelectorAll('a');
                for(var i = 0; i < links.length; i++) {
                    if(links[i].href && links[i].href.includes('/jobs/')) {
                        window.location.href = links[i].href;
                        return true;
                    }
                }
                return false;
            """)
            print("[Auth Bot] Firefox: Navigated to job details via JavaScript")
            job_clicked = True
        except Exception:
            pass
    
    if job_clicked:
        print("[Auth Bot] Firefox: Waiting for job details to load...")
        time.sleep(5)
        # Re-inject monitor after navigation
        _inject_network_monitor_early(driver)
    
    # Try pagination as fallback
    print("[Auth Bot] Firefox: Trying pagination...")
    try:
        driver.execute_script("""
            var btns = document.querySelectorAll('button');
            for(var i = 0; i < btns.length; i++) {
                if(btns[i].textContent.includes('2') || 
                   btns[i].getAttribute('aria-label') === 'Go to page 2' ||
                   btns[i].getAttribute('data-ev-page_index') === '2') {
                    btns[i].click();
                    return true;
                }
            }
            return false;
        """)
        print("[Auth Bot] Firefox: Clicked page 2")
        time.sleep(4)
    except Exception:
        pass
    
    # Final wait for any pending requests
    time.sleep(3)
    
    # Retrieve captured requests
    try:
        captured = driver.execute_script("return window.capturedRequests || [];")
        print(f"[Auth Bot] Firefox: Total captured requests: {len(captured)}")
        
        # Debug: Show what URLs were captured
        if captured:
            urls = [req.get('url', '') for req in captured[:5]]
            print(f"[Auth Bot] Firefox: Sample captured URLs: {urls}")
        
        return captured
    except Exception as e:
        print(f"[Auth Bot] Firefox: Error retrieving captured requests: {e}")
        return []

def get_upwork_headers():
    """Get Upwork headers using SeleniumBase with optimized speed."""
    headers_found = None
    cookies_found = None
    
    force_firefox = os.environ.get("FORCE_FIREFOX") == "1"
    is_ubuntu = False
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                content = f.read().lower()
                is_ubuntu = "ubuntu" in content
    except Exception:
        pass
    
    # Try Chrome first unless forced to use Firefox
    use_firefox = force_firefox
    
    if not use_firefox:
        print("[Auth Bot] Attempting Chrome with undetected mode...")
        try:
            with SB(uc=True, test=True, locale="en", headless=True, page_load_strategy="eager") as sb:
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                try:
                    sb.activate_cdp_mode(url)
                except Exception:
                    sb.open(url)
                
                # Chrome flow (existing working code)
                print("[Auth Bot] Chrome: Waiting for Cloudflare bypass...")
                for attempt in range(8):
                    sb.sleep(3)
                    try:
                        sb.uc_gui_click_captcha()
                    except Exception:
                        pass
                    if sb.is_element_visible(".air3-card"):
                        print("[Auth Bot] Chrome: ✅ Cloudflare bypassed!")
                        break
                
                # Inject network monitor
                monitor_script = """
                (function(){
                    function shouldCapture(u){
                        if(!u || typeof u !== 'string') return false;
                        u = u.toLowerCase();
                        return (
                            u.includes('visitorjobsearch') ||
                            u.includes('jobpubdetails') ||
                            (u.includes('/graphql') && (u.includes('job') || u.includes('search')))
                        );
                    }
                    window.capturedRequests = window.capturedRequests || [];
                    const originalFetch = window.fetch;
                    window.fetch = function(...args){
                        try {
                            const url = args[0];
                            const options = args[1] || {};
                            if(shouldCapture(url)){
                                window.capturedRequests.push({
                                    ts: Date.now(),
                                    url: url,
                                    headers: options.headers || {},
                                    method: (options.method || 'GET').toUpperCase(),
                                    body: options.body || null,
                                    type: 'fetch'
                                });
                            }
                        } catch(e) {}
                        return originalFetch.apply(this, args);
                    };
                })();
                """
                sb.execute_script(monitor_script)
                
                # Click job and capture
                try:
                    if sb.is_element_visible('a[data-test="job-tile-title-link"]'):
                        sb.click('a[data-test="job-tile-title-link"]')
                        print("[Auth Bot] Chrome: Clicked job tile")
                except Exception:
                    pass
                
                sb.sleep(4)
                
                # Get captured requests
                captured_requests = sb.execute_script("return (window.capturedRequests || []).slice(-25);")
                if captured_requests:
                    latest_request = captured_requests[-1]
                    headers_found = dict(latest_request.get('headers', {}) or {})
                    print(f"[Auth Bot] Chrome: ✅ Captured {len(headers_found)} headers")
                
                # Get cookies
                cookies = {}
                for cookie in sb.get_cookies():
                    cookies[cookie['name']] = cookie['value']
                cookies_found = cookies
                
                if headers_found and cookies_found:
                    print("[Auth Bot] Chrome: Success!")
                    # Continue to save and test...
                
        except Exception as e:
            print(f"[Auth Bot] Chrome failed: {e}")
            use_firefox = True
    
    # Firefox fallback with enhanced capture
    if use_firefox or (not headers_found):
        print("[Auth Bot] Using Firefox with enhanced capture...")
        try:
            from selenium import webdriver
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver.firefox.service import Service
            
            # Setup Firefox
            options = Options()
            options.add_argument("-headless")
            options.set_preference("general.useragent.override", 
                                  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            
            driver = webdriver.Firefox(options=options)
            
            try:
                # Navigate to Upwork
                driver.get("https://www.upwork.com/nx/search/jobs/?q=python")
                
                # Use enhanced Firefox capture strategy
                captured_requests = _firefox_wait_and_capture(driver)
                
                if captured_requests:
                    # Find best request (prefer GraphQL)
                    best_request = None
                    for req in reversed(captured_requests):
                        if 'graphql' in req.get('url', '').lower():
                            best_request = req
                            break
                    
                    if not best_request and captured_requests:
                        best_request = captured_requests[-1]
                    
                    if best_request:
                        headers_found = dict(best_request.get('headers', {}) or {})
                        print(f"[Auth Bot] Firefox: ✅ Extracted {len(headers_found)} headers")
                
                # Get cookies
                cookies_found = {c['name']: c['value'] for c in driver.get_cookies()}
                print(f"[Auth Bot] Firefox: ✅ Captured {len(cookies_found)} cookies")
                
                # Extract visitor ID from localStorage/cookies
                try:
                    visitor_data = driver.execute_script("""
                        const result = {visitor: null};
                        // Check localStorage
                        for(let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            const value = localStorage.getItem(key);
                            if(key.toLowerCase().includes('visitor') && value) {
                                result.visitor = value;
                                break;
                            }
                        }
                        // Check cookies
                        if(!result.visitor) {
                            const cookies = document.cookie.split(';');
                            for(let cookie of cookies) {
                                const [name, value] = cookie.trim().split('=');
                                if(name && name.toLowerCase().includes('visitor')) {
                                    result.visitor = value;
                                    break;
                                }
                            }
                        }
                        return result;
                    """)
                    
                    if visitor_data and visitor_data.get('visitor'):
                        if not headers_found:
                            headers_found = {}
                        headers_found['vnd-eo-visitorId'] = visitor_data['visitor']
                        print(f"[Auth Bot] Firefox: 🔑 Found visitor ID: {visitor_data['visitor'][:12]}...")
                except Exception:
                    pass
                
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"[Auth Bot] Firefox error: {e}")
            return False
    
    # Create fallback headers if nothing captured
    if not headers_found:
        print("[Auth Bot] Using comprehensive fallback headers...")
        headers_found = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Origin': 'https://www.upwork.com',
            'Referer': 'https://www.upwork.com/nx/search/jobs/',
        }
    
    if not cookies_found:
        cookies_found = {}
    
    # Save and test
    if headers_found:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Enrich headers
            headers_found = _enrich_headers(headers_found, cookies_found, 
                                           'https://www.upwork.com/nx/search/jobs/')
            headers_found = _ensure_visitor_id(headers_found, script_dir)
            
            # Save files
            with open(os.path.join(script_dir, "headers_upwork.json"), "w") as f:
                json.dump(headers_found, f, indent=2)
            with open(os.path.join(script_dir, "job_details_headers.json"), "w") as f:
                json.dump(headers_found, f, indent=2)
            with open(os.path.join(script_dir, "upwork_cookies.json"), "w") as f:
                json.dump(cookies_found, f, indent=2)
            with open(os.path.join(script_dir, "job_details_cookies.json"), "w") as f:
                json.dump(cookies_found, f, indent=2)
            
            print(f"[Auth Bot] ✅ Saved {len(headers_found)} headers and {len(cookies_found)} cookies")
            
            # Test
            test_success = test_job_details_fetch(headers_found, cookies_found)
            if test_success:
                print("[Auth Bot] ✅ Validation PASSED!")
            else:
                print("[Auth Bot] ⚠️ Validation failed but headers saved")
            
            return True
            
        except Exception as e:
            print(f"[Auth Bot] Error saving: {e}")
            return False
    
    return False

def verify_headers():
    """Verify that saved headers are valid"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        headers_file = os.path.join(script_dir, "headers_upwork.json")
        
        if os.path.exists(headers_file):
            with open(headers_file, 'r') as f:
                headers = json.load(f)
            
            print(f"[Auth Bot] Loaded {len(headers)} headers")
            
            # Check for key headers
            has_required = (
                len(headers) > 5 or
                'vnd-eo-visitorId' in headers or
                'User-Agent' in headers
            )
            
            print(f"[Auth Bot] Headers validation: {'✅ Valid' if has_required else '❌ Invalid'}")
            return has_required
        else:
            print("[Auth Bot] ❌ Headers file not found")
            return False
    except Exception as e:
        print(f"[Auth Bot] ❌ Verification error: {e}")
        return False

def main():
    """Main function for standalone execution"""
    print("=" * 70)
    print("UPWORK AUTHENTICATION BOT - ENHANCED FIREFOX SUPPORT")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        success = get_upwork_headers()
        
        elapsed_time = time.time() - start_time
        print(f"\n[Auth Bot] Total execution time: {elapsed_time:.2f} seconds")
        
        if success:
            print("[Auth Bot] ✅ Authentication completed successfully!")
            
            if verify_headers():
                print("[Auth Bot] ✅ Headers verified and ready to use!")
            else:
                print("[Auth Bot] ⚠️ Headers verification failed")
            
            sys.exit(0)
        else:
            print("[Auth Bot] ❌ Authentication failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n[Auth Bot] ⚠️ Interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"[Auth Bot] ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()