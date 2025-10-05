"""
Improved Upwork Authentication Bot - Fixed for Ubuntu/Firefox
Handles Cloudflare challenges properly across all platforms
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
import platform
import shutil
import tempfile
import tarfile
import stat
import urllib.request
import uuid
import zipfile

# Patch asyncio to allow nested event loops
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

def test_job_details_fetch(headers, cookies):
    """Test fetching job details with captured credentials"""
    print("\n" + "=" * 70)
    print("TESTING JOB DETAILS FETCH")
    print("=" * 70)
    
    test_job_id = "~0140c36fa1e87afd2a"
    
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
                        print("[Test] ❌ GraphQL Errors:")
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
                print(f"[Test] ❌ Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            if attempt < attempts:
                print(f"[Test] ⚠️ Attempt {attempt} failed: {e}. Retrying...")
                time.sleep(backoff)
                backoff *= 2
                continue
            print(f"[Test] ❌ Request failed: {e}")
            return False
    return False

def _enrich_headers(raw_headers, cookies, referer_url):
    """Normalize and enrich headers for Upwork GraphQL"""
    if not raw_headers:
        raw_headers = {}
    
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
    
    if cookies:
        for k in cookies.keys():
            if 'visitor' in k.lower() and 'visitor' not in ' '.join(normalized.keys()).lower():
                normalized.setdefault('vnd-eo-visitorId', cookies[k])
                break
    
    normalized.setdefault('Sec-Fetch-Site', 'same-origin')
    normalized.setdefault('Sec-Fetch-Mode', 'cors')
    normalized.setdefault('Sec-Fetch-Dest', 'empty')
    
    if 'sec-ch-ua' not in {k.lower(): v for k,v in normalized.items()}:
        normalized['sec-ch-ua'] = '"Chromium";v="121", "Not(A:Brand";v="8"'
    normalized.setdefault('sec-ch-ua-mobile', '?0')
    normalized.setdefault('sec-ch-ua-platform', '"Windows"')
    
    normalized.setdefault('apollographql-client-name', 'web')
    normalized.setdefault('apollographql-client-version', '1.4')
    
    return normalized

def _attempt_extract_visitor_ids(driver):
    """Extract visitor/trace IDs from localStorage or cookies"""
    try:
        ids = driver.execute_script(
            """
            const out = {visitor:null, trace:null, storage:{}, cookies:{}};
            try {
              for (let i=0;i<localStorage.length;i++) {
                const k = localStorage.key(i);
                const v = localStorage.getItem(k);
                out.storage[k]=v;
                if(!out.visitor && /visitor/i.test(k) && v && v.length < 80) out.visitor = v;
                if(!out.trace && /trace/i.test(k) && v && v.length < 80) out.trace = v;
              }
              const cookies = document.cookie.split(';');
              for(let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if(name && value) {
                  out.cookies[name] = value;
                  if(!out.visitor && /visitor/i.test(name) && value.length < 80) out.visitor = value;
                  if(!out.trace && /trace/i.test(name) && value.length < 80) out.trace = value;
                }
              }
              if(!out.visitor) {
                for(const [k,v] of Object.entries(out.storage)) {
                  if(/eo.*visitor|visitor.*id|user.*id/i.test(k) && v && v.length > 10 && v.length < 50) {
                    out.visitor = v;
                    break;
                  }
                }
              }
              try {
                for(let i=0;i<sessionStorage.length;i++) {
                  const k = sessionStorage.key(i);
                  const v = sessionStorage.getItem(k);
                  if(/visitor/i.test(k) && v && v.length > 10 && v.length < 80) {
                    out.visitor = v;
                    break;
                  }
                }
              } catch(e) {}
            } catch(e) { out.error = e.toString(); }
            return out;
            """
        )
        visitor = ids.get('visitor') if isinstance(ids, dict) else None
        trace = ids.get('trace') if isinstance(ids, dict) else None
        print(f"[Auth Bot] 🔍 Storage: {len(ids.get('storage', {}))} items, {len(ids.get('cookies', {}))} cookies")
        if visitor:
            print(f"[Auth Bot] 🔑 Visitor ID found: {visitor[:12]}...")
        return visitor, trace
    except Exception as e:
        print(f"[Auth Bot] ⚠️ Visitor ID extraction failed: {e}")
        return None, None

def _ensure_visitor_id(headers, base_dir):
    """Ensure headers contain a stable vnd-eo-visitorId"""
    try:
        if not headers:
            return headers
        
        for k in headers.keys():
            if k.lower() == 'vnd-eo-visitorid':
                return headers
        
        vid_file = os.path.join(base_dir, 'visitor_id.txt')
        visitor_id = None
        if os.path.exists(vid_file):
            try:
                with open(vid_file, 'r') as f:
                    candidate = f.read().strip()
                if candidate and 8 <= len(candidate) <= 64:
                    visitor_id = candidate
                    print(f"[Auth Bot] ♻️ Reusing visitor ID: {visitor_id[:12]}...")
            except Exception:
                pass
        
        if not visitor_id:
            visitor_id = uuid.uuid4().hex
            try:
                with open(vid_file, 'w') as f:
                    f.write(visitor_id)
                print(f"[Auth Bot] 🆕 Generated visitor ID: {visitor_id[:12]}...")
            except Exception:
                pass
        
        headers['vnd-eo-visitorId'] = visitor_id
        return headers
    except Exception as e:
        print(f"[Auth Bot] ⚠️ _ensure_visitor_id error: {e}")
        return headers

def _verify_page_loaded(driver, max_attempts=10):
    """Verify that we're on the actual Upwork page, not Cloudflare challenge"""
    print("[Auth Bot] Verifying page loaded...")
    
    for attempt in range(max_attempts):
        try:
            current_url = driver.current_url if hasattr(driver, 'current_url') else driver.get_current_url()
            
            # Check if still on Cloudflare challenge
            if 'challenge-platform' in current_url or 'cdn-cgi' in current_url:
                print(f"[Auth Bot] Attempt {attempt + 1}: Still on Cloudflare challenge")
                time.sleep(3)
                continue
            
            # Check page source for Cloudflare indicators
            page_source = driver.page_source if hasattr(driver, 'page_source') else driver.get_page_source()
            
            if "Just a moment" in page_source or "challenge-platform" in page_source:
                print(f"[Auth Bot] Attempt {attempt + 1}: Cloudflare challenge detected in page source")
                time.sleep(3)
                continue
            
            # Check for Upwork-specific elements
            try:
                # Try to find job cards or other Upwork elements
                if hasattr(driver, 'find_elements'):
                    from selenium.webdriver.common.by import By
                    elements = driver.find_elements(By.CSS_SELECTOR, ".air3-card, [data-test='job-tile'], article")
                else:
                    elements = driver.find_elements_by_css_selector(".air3-card, [data-test='job-tile'], article")
                
                if elements:
                    print(f"[Auth Bot] ✅ Page loaded successfully on attempt {attempt + 1}")
                    return True
                    
            except Exception:
                pass
            
            print(f"[Auth Bot] Attempt {attempt + 1}: Upwork elements not found yet")
            time.sleep(3)
            
        except Exception as e:
            print(f"[Auth Bot] Attempt {attempt + 1}: Error checking page: {e}")
            time.sleep(3)
    
    print("[Auth Bot] ⚠️ Could not verify page loaded after all attempts")
    return False

def get_upwork_headers():
    """Get Upwork headers using SeleniumBase with improved Cloudflare bypass"""
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

    # For Ubuntu, prefer Firefox with enhanced options
    use_firefox = force_firefox or is_ubuntu
    engine_desc = "Firefox (Ubuntu/Forced)" if use_firefox else "Chrome (uc)"
    print(f"[Auth Bot] Engine: {engine_desc} | Ubuntu={is_ubuntu}")

    try:
        sb_kwargs = {
            "test": True,
            "locale": "en",
            "headless": True,
            "page_load_strategy": "normal",  # Changed from eager to normal for better Cloudflare handling
        }
        
        if not use_firefox:
            sb_kwargs["uc"] = True
        else:
            sb_kwargs["browser"] = "firefox"
            # NOTE: SeleniumBase doesn't support firefox_prefs parameter
            # Firefox preferences would need to be set via profile or other methods
            # For now, we'll use default Firefox settings

        try:
            with SB(**sb_kwargs) as sb:
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                
                if not use_firefox:
                    try:
                        sb.activate_cdp_mode(url)
                    except Exception:
                        sb.open(url)
                else:
                    sb.open(url)

                print("[Auth Bot] Waiting for Cloudflare bypass...")
                
                # Enhanced Cloudflare bypass
                max_cf_attempts = 15  # Increased from 8
                for attempt in range(max_cf_attempts):
                    time.sleep(4)  # Longer wait between attempts
                    
                    try:
                        sb.uc_gui_click_captcha()
                        print(f"[Auth Bot] Attempt {attempt+1}: Clicked captcha")
                    except Exception:
                        pass
                    
                    # Check if we've bypassed
                    current_url = sb.get_current_url()
                    page_source = sb.get_page_source()
                    
                    # More comprehensive check
                    is_challenge = (
                        "challenge-platform" in current_url or
                        "cdn-cgi" in current_url or
                        "Just a moment" in page_source or
                        "Checking your browser" in page_source
                    )
                    
                    if not is_challenge:
                        # Double-check with element presence
                        try:
                            if sb.is_element_visible(".air3-card") or sb.is_element_visible("[data-test='job-tile']"):
                                print(f"[Auth Bot] ✅ Cloudflare bypassed on attempt {attempt+1}!")
                                break
                        except:
                            pass
                    
                    if attempt == max_cf_attempts - 1:
                        print("[Auth Bot] ❌ Could not bypass Cloudflare challenge")
                        print(f"[Auth Bot] Current URL: {current_url}")
                        return False
                
                # Wait for jobs to actually load
                print("[Auth Bot] Loading job listings...")
                try:
                    sb.wait_for_element(".air3-card, [data-test='job-tile'], article", timeout=20)
                    print("[Auth Bot] ✅ Jobs loaded")
                    time.sleep(5)
                except Exception as e:
                    print(f"[Auth Bot] ⚠️ Job elements not found: {e}")
                    # Verify we're actually on the right page
                    current_url = sb.get_current_url()
                    if "challenge" in current_url or "cdn-cgi" in current_url:
                        print("[Auth Bot] ❌ Still on Cloudflare challenge page")
                        return False

                print("[Auth Bot] Injecting network monitor...")
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
                    const originalXHROpen = XMLHttpRequest.prototype.open;
                    const originalXHRSend = XMLHttpRequest.prototype.send;
                    const originalSetHeader = XMLHttpRequest.prototype.setRequestHeader;
                    XMLHttpRequest.prototype.open = function(method, url, async, user, password){
                        this._method = method;
                        this._url = url;
                        this._headers = {};
                        return originalXHROpen.apply(this, arguments);
                    };
                    XMLHttpRequest.prototype.setRequestHeader = function(header, value){
                        try { this._headers[header] = value; } catch(e) {}
                        return originalSetHeader.call(this, header, value);
                    };
                    XMLHttpRequest.prototype.send = function(data){
                        try {
                            if(shouldCapture(this._url)){
                                window.capturedRequests.push({
                                    ts: Date.now(),
                                    url: this._url,
                                    method: (this._method || 'GET').toUpperCase(),
                                    headers: this._headers || {},
                                    body: data || null,
                                    type: 'xhr'
                                });
                            }
                        } catch(e) {}
                        return originalXHRSend.apply(this, arguments);
                    };
                })();
                """
                try:
                    sb.execute_script(monitor_script)
                    print("[Auth Bot] ✅ Network monitor active")
                except Exception as e:
                    print(f"[Auth Bot] ⚠️ Could not inject monitor: {e}")

                # Trigger pagination to capture search request
                print("[Auth Bot] Triggering pagination...")
                time.sleep(3)
                try:
                    # Fix the selector syntax error
                    sb.execute_script("""
                        const pageBtn = document.querySelector('[data-ev-page_index="2"]');
                        if (pageBtn) pageBtn.click();
                    """)
                    print("[Auth Bot] ✅ Pagination triggered")
                    time.sleep(4)
                except Exception as e:
                    print(f"[Auth Bot] ⚠️ Pagination failed: {e}")

                # Click on a job to trigger GraphQL request
                print("[Auth Bot] Triggering job details request...")
                try:
                    # Fixed selector syntax
                    sb.execute_script("""
                        const jobLink = document.querySelector('a[href*="/jobs/"]');
                        if (jobLink) jobLink.click();
                    """)
                    print("[Auth Bot] ✅ Job clicked")
                    time.sleep(5)
                except Exception as e:
                    print(f"[Auth Bot] ⚠️ Job click failed: {e}")

                print("[Auth Bot] Analyzing network requests...")
                try:
                    captured_requests = sb.execute_script("return (window.capturedRequests || []).slice(-25);")
                    print(f"[Auth Bot] Captured {len(captured_requests)} requests")
                    
                    if captured_requests:
                        # Prefer job details GraphQL request
                        preferred = None
                        for req in reversed(captured_requests):
                            if 'jobpubdetails' in req.get('url','').lower():
                                preferred = req
                                break
                        
                        latest_request = preferred or captured_requests[-1]
                        headers_found = dict(latest_request.get('headers', {}) or {})
                        print(f"[Auth Bot] ✅ Headers captured from {latest_request.get('type', 'unknown')}")
                    else:
                        print("[Auth Bot] ⚠️ No requests captured, using fallback headers")
                        headers_found = {}
                    
                    # Extract visitor IDs
                    if headers_found and not any(k.lower() == 'vnd-eo-visitorid' for k in headers_found.keys()):
                        print("[Auth Bot] Extracting visitor ID...")
                        vid, trace = _attempt_extract_visitor_ids(sb)
                        if vid:
                            headers_found['vnd-eo-visitorId'] = vid
                        if trace:
                            headers_found['vnd-eo-trace-id'] = trace
                    
                except Exception as e:
                    print(f"[Auth Bot] ❌ Error retrieving requests: {e}")
                    headers_found = {}

                print("[Auth Bot] Capturing cookies...")
                try:
                    cookies = {}
                    for cookie in sb.get_cookies():
                        cookies[cookie['name']] = cookie['value']
                    print(f"[Auth Bot] ✅ Captured {len(cookies)} cookies")
                    cookies_found = cookies
                    
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    with open(os.path.join(script_dir, "upwork_cookies.json"), "w") as f:
                        json.dump(cookies, f, indent=2)
                except Exception as e:
                    print(f"[Auth Bot] ⚠️ Cookie error: {e}")
                    cookies_found = {}
                    
        except Exception as sb_error:
            # Provide richer diagnostics to track the root cause
            import traceback as _tb
            print(f"[Auth Bot] ❌ SeleniumBase error: {sb_error}")
            _tb.print_exc()
            # Common cause: misnamed kwargs (e.g., firefox_pref -> firefox_prefs)
            if "split" in str(sb_error) and isinstance(sb_kwargs.get("firefox_prefs"), dict):
                print("[Auth Bot] 💡 Hint: Confirm SeleniumBase version supports 'firefox_prefs'.")
            return False

    except Exception as e:
        print(f"[Auth Bot] ❌ Automation error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Save and test headers
    if headers_found is not None and cookies_found is not None:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Enrich headers
            current_url = headers_found.get('Referer') or 'https://www.upwork.com/nx/search/jobs/'
            headers_found = _enrich_headers(headers_found, cookies_found, current_url)
            headers_found = _ensure_visitor_id(headers_found, script_dir)
            
            # Save headers
            headers_file = os.path.join(script_dir, "headers_upwork.json")
            with open(headers_file, "w") as f:
                json.dump(headers_found, f, indent=2)
            print(f"[Auth Bot] ✅ Headers saved to {headers_file}")
            
            job_details_headers_file = os.path.join(script_dir, "job_details_headers.json")
            with open(job_details_headers_file, "w") as f:
                json.dump(headers_found, f, indent=2)
            
            job_details_cookies_file = os.path.join(script_dir, "job_details_cookies.json")
            with open(job_details_cookies_file, "w") as f:
                json.dump(cookies_found, f, indent=2)
            
            print(f"[Auth Bot] Headers: {len(headers_found)} keys, Cookies: {len(cookies_found)} keys")
            
            # Test credentials
            print("\n[Auth Bot] 🧪 Testing credentials...")
            test_success = test_job_details_fetch(headers_found, cookies_found)
            
            if test_success:
                print("\n[Auth Bot] ✅ Credentials validation PASSED!")
                return True
            else:
                print("\n[Auth Bot] ⚠️ Credentials validation FAILED!")
                print("[Auth Bot] Headers/cookies may not work for all requests")
                return True  # Still return True since we captured something
            
        except Exception as e:
            print(f"[Auth Bot] ❌ Error saving headers: {e}")
            return False
    else:
        print("[Auth Bot] ❌ No headers or cookies captured")
        return False

def verify_headers():
    """Verify that saved headers are valid"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        headers_file = os.path.join(script_dir, "headers_upwork.json")
        
        if os.path.exists(headers_file):
            with open(headers_file, 'r') as f:
                headers = json.load(f)
            
            header_keys_lower = [k.lower() for k in headers.keys()]
            has_required = len(headers) > 5 and any(h in header_keys_lower for h in ['user-agent', 'accept'])
            
            print(f"[Auth Bot] Headers validation: {'✅ Valid' if has_required else '❌ Invalid'}")
            print(f"[Auth Bot] Total headers: {len(headers)}")
            
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
    print("UPWORK AUTHENTICATION BOT - FIXED FOR UBUNTU/FIREFOX")
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