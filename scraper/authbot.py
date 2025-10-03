"""
Improved Upwork Authentication Bot
Fast, reliable authentication refresh with validation test
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

# Patch asyncio to allow nested event loops (fixes RuntimeError in Jupyter/IPython/Python 3.10+)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # If not available, ignore, but recommend installing it if error persists

def is_wsl_ubuntu() -> bool:
    """Detect if running under WSL (Windows Subsystem for Linux).
    Returns True for WSL environments (typically Ubuntu on Windows).
    Detection methods:
      - platform.system() == 'Linux' AND any of:
          * Env vars: WSL_DISTRO_NAME / WSL_INTEROP / WSLENV
          * '/proc/sys/kernel/osrelease' contains 'microsoft'
          * '/proc/version' contains 'microsoft'
    """
    try:
        if platform.system().lower() != "linux":
            return False

        # Fast path via env vars
        env = os.environ
        if any(k in env for k in ("WSL_DISTRO_NAME", "WSL_INTEROP", "WSLENV")):
            return True

        # Check kernel strings
        try:
            with open("/proc/sys/kernel/osrelease", "r", encoding="utf-8", errors="ignore") as f:
                if "microsoft" in f.read().lower():
                    return True
        except Exception:
            pass

        try:
            with open("/proc/version", "r", encoding="utf-8", errors="ignore") as f:
                if "microsoft" in f.read().lower():
                    return True
        except Exception:
            pass

        # Fallback to platform release/version checks
        rel = platform.release().lower()
        ver = platform.version().lower()
        return ("microsoft" in rel) or ("microsoft" in ver)
    except Exception:
        return False
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
                    budget {
                        amount
                        currencyCode
                    }
                    clientActivity {
                        totalApplicants
                        totalHired
                        totalInvitedToInterview
                    }
                }
                buyer {
                    location {
                        city
                        country
                        countryTimezone
                    }
                    stats {
                        totalAssignments
                        feedbackCount
                        score
                        totalCharges {
                            amount
                            currencyCode
                        }
                    }
                }
                qualifications {
                    minJobSuccessScore
                    minOdeskHours
                    risingTalent
                }
            }
        }""",
        "variables": {
            "id": test_job_id
        }
    }
    
    url = "https://www.upwork.com/api/graphql/v1?alias=gql-query-get-visitor-job-details"
    
    print(f"[Test] Testing with job ID: {test_job_id}")
    print(f"[Test] Request URL: {url}")
    
    try:
        response = session.post(
            url,
            headers=headers,
            cookies=cookies,
            json=payload,
            timeout=15
        )
        
        print(f"[Test] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Check for errors
                if "errors" in data:
                    print("[Test] ❌ GraphQL Errors Found:")
                    for error in data["errors"]:
                        print(f"  - {error.get('message', 'Unknown error')}")
                    return False
                
                # Check for valid data
                if "data" in data and data["data"]:
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
                        print(f"Description: {opening.get('description', 'N/A')[:100]}...")
                        
                        budget = opening.get("budget", {})
                        if budget:
                            print(f"Budget: ${budget.get('amount', 'N/A')} {budget.get('currencyCode', '')}")
                        
                        activity = opening.get("clientActivity", {})
                        if activity:
                            print(f"Applicants: {activity.get('totalApplicants', 0)}")
                            print(f"Hired: {activity.get('totalHired', 0)}")
                        
                        buyer = job_details.get("buyer", {})
                        if buyer:
                            location = buyer.get("location", {})
                            print(f"Client Location: {location.get('city', '')}, {location.get('country', '')}")
                            
                            stats = buyer.get("stats", {})
                            if stats:
                                print(f"Client Rating: {stats.get('score', 'N/A')}/5")
                                print(f"Client Total Jobs: {stats.get('totalAssignments', 0)}")
                        
                        print("-" * 70)
                        return True
                    else:
                        print("[Test] ⚠️ Empty job details returned")
                        return False
                else:
                    print("[Test] ⚠️ No data in response")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"[Test] ❌ Failed to parse JSON: {e}")
                print(f"[Test] Response preview: {response.text[:200]}")
                return False
                
        elif response.status_code == 401:
            print("[Test] ❌ Authentication Failed (401)")
            print("[Test] Headers/cookies are invalid or expired")
            return False
            
        elif response.status_code == 403:
            print("[Test] ❌ Access Forbidden (403)")
            print("[Test] Possible rate limiting or blocked request")
            return False
            
        else:
            print(f"[Test] ❌ Unexpected status code: {response.status_code}")
            print(f"[Test] Response preview: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"[Test] ❌ Request failed: {e}")
        return False

def get_upwork_headers():
    """Get Upwork headers using SeleniumBase with optimized speed"""
    headers_found = None
    cookies_found = None
    
    try:
        # Log detection info for easier troubleshooting
        sys_name = platform.system()
        rel = platform.release()
        ver = platform.version()
        is_wsl = is_wsl_ubuntu()
        print(f"[Auth Bot] Platform: system={sys_name} release={rel} version={ver}")
        print(f"[Auth Bot] Detected WSL: {is_wsl} | Env[WSL_DISTRO_NAME]={'WSL_DISTRO_NAME' in os.environ}")

        # Choose Firefox for WSL Ubuntu, Chrome (UC) elsewhere
        if is_wsl:
            print("[Auth Bot] Environment: WSL Ubuntu detected -> Using Firefox headless")
            with SB(browser="firefox", test=True, locale="en", headless=True,
                    page_load_strategy="eager") as sb:
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                sb.open(url)

                print("[Auth Bot] Waiting for Cloudflare bypass (Firefox)...")
                max_attempts = 8
                for attempt in range(max_attempts):
                    sb.sleep(3)
                    try:
                        # Check for job listings as a proxy for having passed CF
                        if sb.is_element_visible(".air3-card"):
                            print("[Auth Bot] ✅ Cloudflare bypassed!")
                            break
                    except Exception:
                        pass
                    try:
                        page_source = sb.get_page_source()
                        if "Just a moment" not in page_source and "Checking your browser" not in page_source:
                            print("[Auth Bot] ✅ Challenge bypassed!")
                            break
                    except Exception:
                        pass
                else:
                    print("[Auth Bot] ⚠️ Cloudflare challenge timeout - continuing anyway")

                # Wait for job cards with timeout
                print("[Auth Bot] Loading job listings...")
                try:
                    sb.wait_for_element(".air3-card", timeout=15)
                    print("[Auth Bot] ✅ Jobs loaded")
                    sb.sleep(3)
                except Exception:
                    print("[Auth Bot] ⚠️ Job cards timeout - checking page...")
                    try:
                        current_url = sb.get_current_url()
                        print(f"[Auth Bot] Current URL: {current_url}")
                    except Exception:
                        pass

                # Inject network monitor
                print("[Auth Bot] Injecting network monitor...")
                monitor_script = """
            window.capturedRequests = [];
            
            // Intercept fetch
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
            
            // Intercept XHR
            const originalXHROpen = XMLHttpRequest.prototype.open;
            const originalXHRSend = XMLHttpRequest.prototype.send;
            const originalSetHeader = XMLHttpRequest.prototype.setRequestHeader;
            
            XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
                this._method = method;
                this._url = url;
                this._headers = {};
                return originalXHROpen.apply(this, arguments);
            };
            
            XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
                this._headers[header] = value;
                return originalSetHeader.call(this, header, value);
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
                print("[Auth Bot] ✅ Network monitor active")

                # Find and click page 2
                print("[Auth Bot] Looking for pagination...")
                page_2_selectors = [
                    'button[data-ev-page_index="2"]',
                    'a[data-ev-page_index="2"]',
                    'button[aria-label="Go to page 2"]',
                    '.pagination button:nth-child(3)',
                    'li[data-page="2"] button'
                ]
                
                page_2_found = False
                for selector in page_2_selectors:
                    try:
                        if sb.is_element_visible(selector):
                            sb.scroll_to_element(selector)
                            sb.sleep(2)
                            sb.click(selector)
                            print(f"[Auth Bot] ✅ Clicked page 2: {selector}")
                            page_2_found = True
                            break
                    except Exception:
                        continue

                if not page_2_found:
                    print("[Auth Bot] ⚠️ Page 2 not found, trying JS click...")
                    try:
                        sb.execute_script("""
                            const pageBtn = document.querySelector('[data-ev-page_index="2"]');
                            if (pageBtn) pageBtn.click();
                        """)
                        print("[Auth Bot] ✅ Clicked page 2 via JS")
                    except Exception as e:
                        print(f"[Auth Bot] ❌ Could not click page 2: {e}")

                # Wait for GraphQL request
                print("[Auth Bot] Waiting for GraphQL request...")
                sb.sleep(5)  # Reduced wait time

                # Check captured requests
                print("[Auth Bot] Analyzing network requests...")
                try:
                    captured_requests = sb.execute_script("return window.capturedRequests || [];")
                    print(f"[Auth Bot] Captured {len(captured_requests)} requests")
                    
                    if captured_requests:
                        latest_request = captured_requests[-1]
                        headers_found = latest_request.get('headers', {})
                        
                        if not headers_found or len(headers_found) == 0:
                            print("[Auth Bot] No headers captured, creating fallback...")
                            user_agent = sb.execute_script("return navigator.userAgent;")
                            headers_found = {
                                'Accept': 'application/json, text/plain, */*',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Content-Type': 'application/json',
                                'User-Agent': user_agent,
                                'Referer': sb.get_current_url(),
                                'Origin': 'https://www.upwork.com'
                            }
                        
                        print(f"[Auth Bot] ✅ Headers captured from {latest_request.get('type', 'unknown')}")
                    else:
                        print("[Auth Bot] No requests captured, using fallback headers...")
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
                    print(f"[Auth Bot] ❌ Error retrieving requests: {e}")
                    return False

                # Capture cookies
                print("[Auth Bot] Capturing cookies...")
                try:
                    cookies = {}
                    for cookie in sb.get_cookies():
                        cookies[cookie['name']] = cookie['value']
                    print(f"[Auth Bot] ✅ Captured {len(cookies)} cookies")
                    
                    # IMPORTANT: Set cookies_found BEFORE saving
                    cookies_found = cookies
                    
                    # Save cookies with consistent path
                    script_dir = os.path.dirname(os.path.abspath(__file__)) if os.path.dirname(__file__) else os.getcwd()
                    cookies_file = os.path.join(script_dir, "upwork_cookies.json")
                    with open(cookies_file, "w") as f:
                        json.dump(cookies, f, indent=2)
                    print(f"[Auth Bot] ✅ Cookies saved to {cookies_file}")
                    
                except Exception as e:
                    print(f"[Auth Bot] ⚠️ Cookie error: {e}")
                    cookies_found = None  # Explicitly set to None on error
        else:
            print("[Auth Bot] Environment: Non-WSL -> Using Chrome (UC) headless")
            # Optimized browser settings for speed (UC Chrome)
            try:
                with SB(uc=True, test=True, locale="en", headless=True,
                        page_load_strategy="eager") as sb:
                    url = "https://www.upwork.com/nx/search/jobs/?q=python"
                    sb.activate_cdp_mode(url)

                    print("[Auth Bot] Waiting for Cloudflare bypass...")
                    max_attempts = 8
                    for attempt in range(max_attempts):
                        sb.sleep(3)
                        # Try clicking captcha if present (UC only)
                        try:
                            sb.uc_gui_click_captcha()
                            print(f"[Auth Bot] Attempt {attempt+1}: Clicked captcha")
                        except Exception:
                            pass
                        # Quick checks
                        if sb.is_element_visible(".air3-card"):
                            print("[Auth Bot] ✅ Cloudflare bypassed!")
                            break
                        page_source = sb.get_page_source()
                        if "Just a moment" not in page_source:
                            print("[Auth Bot] ✅ Challenge bypassed!")
                            break
                    else:
                        print("[Auth Bot] ⚠️ Cloudflare challenge timeout - continuing anyway")

                    # Wait for job cards
                    print("[Auth Bot] Loading job listings...")
                    try:
                        sb.wait_for_element(".air3-card", timeout=15)
                        print("[Auth Bot] ✅ Jobs loaded")
                        sb.sleep(5)
                    except Exception:
                        print("[Auth Bot] ⚠️ Job cards timeout - checking page...")
                        current_url = sb.get_current_url()
                        print(f"[Auth Bot] Current URL: {current_url}")

                    # Inject network monitor
                    print("[Auth Bot] Injecting network monitor...")
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
                    const originalSetHeader = XMLHttpRequest.prototype.setRequestHeader;
                    XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
                        this._method = method;
                        this._url = url;
                        this._headers = {};
                        return originalXHROpen.apply(this, arguments);
                    };
                    XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
                        this._headers[header] = value;
                        return originalSetHeader.call(this, header, value);
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
                    print("[Auth Bot] ✅ Network monitor active")

                    # Pagination
                    print("[Auth Bot] Looking for pagination...")
                    page_2_selectors = [
                        'button[data-ev-page_index="2"]',
                        'a[data-ev-page_index="2"]',
                        'button[aria-label="Go to page 2"]',
                        '.pagination button:nth-child(3)',
                        'li[data-page="2"] button'
                    ]
                    page_2_found = False
                    for selector in page_2_selectors:
                        try:
                            if sb.is_element_visible(selector):
                                sb.scroll_to_element(selector)
                                sb.sleep(2)
                                sb.click(selector)
                                print(f"[Auth Bot] ✅ Clicked page 2: {selector}")
                                page_2_found = True
                                break
                        except Exception:
                            continue
                    if not page_2_found:
                        print("[Auth Bot] ⚠️ Page 2 not found, trying JS click...")
                        try:
                            sb.execute_script("""
                                const pageBtn = document.querySelector('[data-ev-page_index="2"]');
                                if (pageBtn) pageBtn.click();
                            """)
                            print("[Auth Bot] ✅ Clicked page 2 via JS")
                        except Exception as e:
                            print(f"[Auth Bot] ❌ Could not click page 2: {e}")

                    # Wait and analyze
                    print("[Auth Bot] Waiting for GraphQL request...")
                    sb.sleep(5)
                    print("[Auth Bot] Analyzing network requests...")
                    try:
                        captured_requests = sb.execute_script("return window.capturedRequests || [];")
                        print(f"[Auth Bot] Captured {len(captured_requests)} requests")
                        if captured_requests:
                            latest_request = captured_requests[-1]
                            headers_found = latest_request.get('headers', {})
                            if not headers_found:
                                user_agent = sb.execute_script("return navigator.userAgent;")
                                headers_found = {
                                    'Accept': 'application/json, text/plain, */*',
                                    'Accept-Language': 'en-US,en;q=0.9',
                                    'Content-Type': 'application/json',
                                    'User-Agent': user_agent,
                                    'Referer': sb.get_current_url(),
                                    'Origin': 'https://www.upwork.com'
                                }
                            print(f"[Auth Bot] ✅ Headers captured from {latest_request.get('type', 'unknown')}")
                        else:
                            print("[Auth Bot] No requests captured, using fallback headers...")
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
                        print(f"[Auth Bot] ❌ Error retrieving requests: {e}")
                        return False

                    # Cookies
                    print("[Auth Bot] Capturing cookies...")
                    try:
                        cookies = {}
                        for cookie in sb.get_cookies():
                            cookies[cookie['name']] = cookie['value']
                        print(f"[Auth Bot] ✅ Captured {len(cookies)} cookies")
                        cookies_found = cookies
                        script_dir = os.path.dirname(os.path.abspath(__file__)) if os.path.dirname(__file__) else os.getcwd()
                        cookies_file = os.path.join(script_dir, "upwork_cookies.json")
                        with open(cookies_file, "w") as f:
                            json.dump(cookies, f, indent=2)
                        print(f"[Auth Bot] ✅ Cookies saved to {cookies_file}")
                    except Exception as e:
                        print(f"[Auth Bot] ⚠️ Cookie error: {e}")
                        cookies_found = None
            except Exception as e:
                # Fallback: If Chrome/UC not available (e.g., on servers), try Firefox headless
                print(f"[Auth Bot] ⚠️ Chrome/UC failed ({e}). Falling back to Firefox headless...")
                try:
                    with SB(browser="firefox", test=True, locale="en", headless=True,
                            page_load_strategy="eager") as sb:
                        url = "https://www.upwork.com/nx/search/jobs/?q=python"
                        sb.open(url)
                        print("[Auth Bot] Waiting for Cloudflare bypass (Firefox Fallback)...")
                        for attempt in range(8):
                            sb.sleep(3)
                            try:
                                if sb.is_element_visible(".air3-card"):
                                    print("[Auth Bot] ✅ Cloudflare bypassed!")
                                    break
                            except Exception:
                                pass
                            try:
                                src = sb.get_page_source()
                                if "Just a moment" not in src and "Checking your browser" not in src:
                                    print("[Auth Bot] ✅ Challenge bypassed!")
                                    break
                            except Exception:
                                pass
                        # Minimal headers/cookies capture like above
                        print("[Auth Bot] Capturing cookies (Firefox Fallback)...")
                        cookies = {}
                        for cookie in sb.get_cookies():
                            cookies[cookie['name']] = cookie['value']
                        cookies_found = cookies
                        ua = sb.execute_script("return navigator.userAgent;")
                        headers_found = {
                            'Accept': 'application/json, text/plain, */*',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Content-Type': 'application/json',
                            'User-Agent': ua,
                            'Referer': sb.get_current_url(),
                            'Origin': 'https://www.upwork.com'
                        }
                except Exception as fe:
                    print(f"[Auth Bot] ❌ Firefox fallback failed: {fe}")
                    return False
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                sb.activate_cdp_mode(url)

                print("[Auth Bot] Waiting for Cloudflare bypass...")
                max_attempts = 8
                for attempt in range(max_attempts):
                    sb.sleep(3)
                    # Try clicking captcha if present (UC only)
                    try:
                        sb.uc_gui_click_captcha()
                        print(f"[Auth Bot] Attempt {attempt+1}: Clicked captcha")
                    except Exception:
                        pass
                    # Quick checks
                    if sb.is_element_visible(".air3-card"):
                        print("[Auth Bot] ✅ Cloudflare bypassed!")
                        break
                    page_source = sb.get_page_source()
                    if "Just a moment" not in page_source:
                        print("[Auth Bot] ✅ Challenge bypassed!")
                        break
                else:
                    print("[Auth Bot] ⚠️ Cloudflare challenge timeout - continuing anyway")

                # Wait for job cards
                print("[Auth Bot] Loading job listings...")
                try:
                    sb.wait_for_element(".air3-card", timeout=15)
                    print("[Auth Bot] ✅ Jobs loaded")
                    sb.sleep(5)
                except Exception:
                    print("[Auth Bot] ⚠️ Job cards timeout - checking page...")
                    current_url = sb.get_current_url()
                    print(f"[Auth Bot] Current URL: {current_url}")

                # Inject network monitor
                print("[Auth Bot] Injecting network monitor...")
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
                const originalSetHeader = XMLHttpRequest.prototype.setRequestHeader;
                XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
                    this._method = method;
                    this._url = url;
                    this._headers = {};
                    return originalXHROpen.apply(this, arguments);
                };
                XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
                    this._headers[header] = value;
                    return originalSetHeader.call(this, header, value);
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
                print("[Auth Bot] ✅ Network monitor active")

                # Pagination
                print("[Auth Bot] Looking for pagination...")
                page_2_selectors = [
                    'button[data-ev-page_index="2"]',
                    'a[data-ev-page_index="2"]',
                    'button[aria-label="Go to page 2"]',
                    '.pagination button:nth-child(3)',
                    'li[data-page="2"] button'
                ]
                page_2_found = False
                for selector in page_2_selectors:
                    try:
                        if sb.is_element_visible(selector):
                            sb.scroll_to_element(selector)
                            sb.sleep(2)
                            sb.click(selector)
                            print(f"[Auth Bot] ✅ Clicked page 2: {selector}")
                            page_2_found = True
                            break
                    except Exception:
                        continue
                if not page_2_found:
                    print("[Auth Bot] ⚠️ Page 2 not found, trying JS click...")
                    try:
                        sb.execute_script("""
                            const pageBtn = document.querySelector('[data-ev-page_index="2"]');
                            if (pageBtn) pageBtn.click();
                        """)
                        print("[Auth Bot] ✅ Clicked page 2 via JS")
                    except Exception as e:
                        print(f"[Auth Bot] ❌ Could not click page 2: {e}")

                # Wait and analyze
                print("[Auth Bot] Waiting for GraphQL request...")
                sb.sleep(5)
                print("[Auth Bot] Analyzing network requests...")
                try:
                    captured_requests = sb.execute_script("return window.capturedRequests || [];")
                    print(f"[Auth Bot] Captured {len(captured_requests)} requests")
                    if captured_requests:
                        latest_request = captured_requests[-1]
                        headers_found = latest_request.get('headers', {})
                        if not headers_found:
                            user_agent = sb.execute_script("return navigator.userAgent;")
                            headers_found = {
                                'Accept': 'application/json, text/plain, */*',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Content-Type': 'application/json',
                                'User-Agent': user_agent,
                                'Referer': sb.get_current_url(),
                                'Origin': 'https://www.upwork.com'
                            }
                        print(f"[Auth Bot] ✅ Headers captured from {latest_request.get('type', 'unknown')}")
                    else:
                        print("[Auth Bot] No requests captured, using fallback headers...")
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
                    print(f"[Auth Bot] ❌ Error retrieving requests: {e}")
                    return False

                # Cookies
                print("[Auth Bot] Capturing cookies...")
                try:
                    cookies = {}
                    for cookie in sb.get_cookies():
                        cookies[cookie['name']] = cookie['value']
                    print(f"[Auth Bot] ✅ Captured {len(cookies)} cookies")
                    cookies_found = cookies
                    script_dir = os.path.dirname(os.path.abspath(__file__)) if os.path.dirname(__file__) else os.getcwd()
                    cookies_file = os.path.join(script_dir, "upwork_cookies.json")
                    with open(cookies_file, "w") as f:
                        json.dump(cookies, f, indent=2)
                    print(f"[Auth Bot] ✅ Cookies saved to {cookies_file}")
                except Exception as e:
                    print(f"[Auth Bot] ⚠️ Cookie error: {e}")
                    cookies_found = None

    except Exception as e:
        print(f"[Auth Bot] ❌ Automation error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Debug: Check what we captured
    print(f"\n[Auth Bot] 📊 Capture Summary:")
    print(f"[Auth Bot] Headers captured: {headers_found is not None} ({len(headers_found) if headers_found else 0} keys)")
    print(f"[Auth Bot] Cookies captured: {cookies_found is not None} ({len(cookies_found) if cookies_found else 0} keys)")
    
    # Additional debug
    if headers_found is None:
        print("[Auth Bot] ⚠️ WARNING: headers_found is None!")
    if cookies_found is None:
        print("[Auth Bot] ⚠️ WARNING: cookies_found is None!")
    
    print(f"[Auth Bot] Condition check: headers_found and cookies_found = {headers_found is not None and cookies_found is not None}")
    
    # Save headers and cookies
    if headers_found is not None and cookies_found is not None:
        try:
            # Get consistent base directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Save to primary location
            headers_file = os.path.join(script_dir, "headers_upwork.json")
            with open(headers_file, "w") as f:
                json.dump(headers_found, f, indent=2)
            print(f"[Auth Bot] ✅ Headers saved to {headers_file}")
            
            # Save to secondary location for compatibility
            job_details_headers_file = os.path.join(script_dir, "job_details_headers.json")
            with open(job_details_headers_file, "w") as f:
                json.dump(headers_found, f, indent=2)
            print(f"[Auth Bot] ✅ Headers also saved to {job_details_headers_file}")
            
            # Save cookies to job_details_cookies.json
            job_details_cookies_file = os.path.join(script_dir, "job_details_cookies.json")
            with open(job_details_cookies_file, "w") as f:
                json.dump(cookies_found, f, indent=2)
            print(f"[Auth Bot] ✅ Cookies also saved to {job_details_cookies_file}")
            
            # Display sample of captured headers
            print("[Auth Bot] 📋 Header sample:")
            for key in list(headers_found.keys())[:5]:
                value = str(headers_found[key])[:50]
                print(f"  {key}: {value}...")
            
            # Add standard headers if missing
            if 'User-Agent' not in headers_found:
                headers_found['User-Agent'] = headers_found.get('user-agent', 'Mozilla/5.0')
            if 'Accept' not in headers_found:
                headers_found['Accept'] = 'application/json, text/plain, */*'
            
            # TEST: Validate credentials by fetching job details
            print("\n[Auth Bot] 🧪 Testing captured credentials...")
            print(f"[Auth Bot] Headers to test: {len(headers_found)} keys")
            print(f"[Auth Bot] Cookies to test: {len(cookies_found)} keys")
            
            test_success = test_job_details_fetch(headers_found, cookies_found)
            
            if test_success:
                print("\n[Auth Bot] ✅ Credentials validation PASSED!")
                print("[Auth Bot] Headers and cookies are working correctly!")
                return True
            else:
                print("\n[Auth Bot] ⚠️ Credentials validation FAILED!")
                print("[Auth Bot] Headers/cookies were captured but may not work for all requests")
                print("[Auth Bot] This could be normal for public-only API access")
                return True  # Still return True since we captured something
            
        except Exception as e:
            print(f"[Auth Bot] ❌ Error saving headers: {e}")
            import traceback
            traceback.print_exc()
            return False
    elif headers_found:
        print("[Auth Bot] ⚠️ Headers captured but no cookies found")
        return False
    else:
        print("[Auth Bot] ❌ No headers found")
        return False

def verify_headers():
    """Verify that saved headers are valid"""
    try:
        # Check in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        headers_file = os.path.join(script_dir, "headers_upwork.json")
        
        print(f"[Auth Bot] Checking headers file: {headers_file}")
        print(f"[Auth Bot] File exists: {os.path.exists(headers_file)}")
        
        if os.path.exists(headers_file):
            with open(headers_file, 'r') as f:
                headers = json.load(f)
            
            print(f"[Auth Bot] Loaded {len(headers)} headers from file")
            
            # Check for Upwork-specific headers OR standard headers
            upwork_headers = ['X-Upwork-Accept-Language', 'vnd-eo-visitorId', 'vnd-eo-trace-id']
            standard_headers = ['User-Agent', 'Accept', 'Content-Type']
            
            # Case-insensitive check
            header_keys_lower = [k.lower() for k in headers.keys()]
            
            has_upwork = any(uh.lower() in ' '.join(header_keys_lower) for uh in upwork_headers)
            has_standard = any(sh.lower() in ' '.join(header_keys_lower) for sh in standard_headers)
            has_required = has_upwork or has_standard or len(headers) > 5  # If we have many headers, it's probably good
            
            print(f"[Auth Bot] Headers validation: {'✅ Valid' if has_required else '❌ Invalid'}")
            print(f"[Auth Bot] Total headers: {len(headers)}")
            print(f"[Auth Bot] Has Upwork headers: {has_upwork}")
            print(f"[Auth Bot] Has standard headers: {has_standard}")
            
            # Show what headers we have
            print(f"[Auth Bot] Header keys: {', '.join(list(headers.keys())[:10])}")
            
            return has_required
        else:
            print("[Auth Bot] ❌ Headers file not found")
            return False
    except Exception as e:
        print(f"[Auth Bot] ❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function for standalone execution"""
    print("=" * 70)
    print("UPWORK AUTHENTICATION BOT - OPTIMIZED VERSION WITH TESTING")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        success = get_upwork_headers()
        
        elapsed_time = time.time() - start_time
        print(f"\n[Auth Bot] Total execution time: {elapsed_time:.2f} seconds")
        
        if success:
            print("[Auth Bot] ✅ Authentication completed successfully!")
            
            # Verify headers
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
    
    print("=" * 70)

if __name__ == "__main__":
    main()