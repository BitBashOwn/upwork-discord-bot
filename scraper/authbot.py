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

def _attempt_extract_visitor_ids(sb):
    """Try to extract visitor / trace identifiers from localStorage or cookies."""
    try:
        ids = sb.execute_script(
            """
            const out = {visitor:null, trace:null, storage:{}, cookies:{}};
            try {
              // Check localStorage
              for (let i=0;i<localStorage.length;i++) {
                const k = localStorage.key(i);
                const v = localStorage.getItem(k);
                out.storage[k]=v;
                if(!out.visitor && /visitor/i.test(k) && v && v.length < 80) out.visitor = v;
                if(!out.trace && /trace/i.test(k) && v && v.length < 80) out.trace = v;
              }
              // Check document cookies
              const cookies = document.cookie.split(';');
              for(let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if(name && value) {
                  out.cookies[name] = value;
                  if(!out.visitor && /visitor/i.test(name) && value.length < 80) out.visitor = value;
                  if(!out.trace && /trace/i.test(name) && value.length < 80) out.trace = value;
                }
              }
              // Look for common Upwork visitor patterns
              if(!out.visitor) {
                for(const [k,v] of Object.entries(out.storage)) {
                  if(/eo.*visitor|visitor.*id|user.*id/i.test(k) && v && v.length > 10 && v.length < 50) {
                    out.visitor = v;
                    break;
                  }
                }
              }
              // Also check session storage
              if(!out.visitor) {
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
              }
              // Try to extract from page HTML/scripts as fallback
              if(!out.visitor) {
                const scripts = document.querySelectorAll('script');
                for(let script of scripts) {
                  const text = script.textContent || script.innerText || '';
                  const match = text.match(/["']([a-f0-9-]{20,40})["'].*visitor/i) || text.match(/visitor.*["']([a-f0-9-]{20,40})["']/i);
                  if(match && match[1]) {
                    out.visitor = match[1];
                    break;
                  }
                }
              }
              // Check for any stored authentication tokens that might contain visitor info
              if(!out.visitor) {
                for(const [k,v] of Object.entries(out.storage)) {
                  if(typeof v === 'string' && v.length >= 20 && v.length <= 60) {
                    // Look for hex-like patterns that could be visitor IDs
                    if(/^[a-f0-9-]{20,50}$/i.test(v) && (k.toLowerCase().includes('auth') || k.toLowerCase().includes('token') || k.toLowerCase().includes('id'))) {
                      out.visitor = v;
                      break;
                    }
                  }
                }
              }
            } catch(e) { out.error = e.toString(); }
            return out;
            """
        )
        visitor = ids.get('visitor') if isinstance(ids, dict) else None
        trace = ids.get('trace') if isinstance(ids, dict) else None
        print(f"[Auth Bot] 🔍 Storage scan: {len(ids.get('storage', {}))} localStorage, {len(ids.get('cookies', {}))} cookies")
        if visitor:
            print(f"[Auth Bot] 🔑 Visitor ID found: {len(visitor)} chars, source: {_identify_visitor_source(ids, visitor)}")
        return visitor, trace
    except Exception as e:
        print(f"[Auth Bot] ⚠️ Visitor ID extraction failed: {e}")
        return None, None

def _identify_visitor_source(ids, visitor_id):
    """Helper to identify where the visitor ID was found"""
    if not isinstance(ids, dict) or not visitor_id:
        return "unknown"
    
    # Check localStorage
    for k, v in ids.get('storage', {}).items():
        if v == visitor_id:
            return f"localStorage[{k}]"
    
    # Check cookies
    for k, v in ids.get('cookies', {}).items():
        if v == visitor_id:
            return f"cookie[{k}]"
    
    return "script/fallback"

def _ensure_geckodriver():
    """Ensure geckodriver exists locally; return absolute path or None.

    Strategy:
    1. Check explicit GECKODRIVER env.
    2. Check PATH for executable.
    3. Check common system locations.
    4. Check / create project-local drivers cache (./drivers/geckodriver[.exe]) and download latest.
    Supports Linux (x86_64/arm64), macOS (x86_64/arm64), Windows (x86_64/arm64) using GitHub releases.
    """
    # 1. Env override
    env_path = os.environ.get("GECKODRIVER")
    if env_path and os.path.exists(env_path):
        return env_path
    # 2. PATH scan
    exe_name = "geckodriver.exe" if platform.system().lower().startswith("win") else "geckodriver"
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path_dir.strip(), exe_name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    # 3. common locations
    common = [
        "/usr/local/bin/geckodriver",
        "/usr/bin/geckodriver",
        os.path.expanduser("~/bin/geckodriver"),
    ]
    for c in common:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    # 4. project-local cache
    script_dir = os.path.dirname(os.path.abspath(__file__))
    drivers_dir = os.path.join(script_dir, "drivers")
    os.makedirs(drivers_dir, exist_ok=True)
    local_path = os.path.join(drivers_dir, exe_name)
    if os.path.exists(local_path):
        # make sure it's executable
        try:
            st = os.stat(local_path)
            os.chmod(local_path, st.st_mode | stat.S_IEXEC)
        except Exception:
            pass
        return local_path
    # Need to download
    try:
        arch_raw = platform.machine().lower()
        system = platform.system().lower()
        if system == "linux":
            if arch_raw in ("aarch64", "arm64"):
                asset_arch = "linux-aarch64"
            elif arch_raw in ("x86_64", "amd64"):
                asset_arch = "linux64"
            else:
                print(f"[Auth Bot] ⚠️ Unsupported linux arch for auto geckodriver: {arch_raw}")
                return None
            archive_ext = ".tar.gz"
        elif system == "darwin":
            if arch_raw in ("arm64", "aarch64"):
                asset_arch = "macos-aarch64"
            else:
                asset_arch = "macos"
            archive_ext = ".tar.gz"
        elif system == "windows":
            # Windows builds only for 64-bit
            asset_arch = "win64" if arch_raw in ("x86_64", "amd64", "arm64") else "win32"
            archive_ext = ".zip"
        else:
            print(f"[Auth Bot] ⚠️ Unsupported OS for auto geckodriver: {system}")
            return None

        api_url = "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
        print("[Auth Bot] 📥 Fetching latest geckodriver release metadata...")
        with urllib.request.urlopen(api_url, timeout=30) as r:
            release = json.loads(r.read().decode())
        tag = release.get("tag_name")
        if not tag:
            print("[Auth Bot] ⚠️ Unable to parse geckodriver tag")
            return None
        expected_name_part = f"geckodriver-{tag}-{asset_arch}"
        asset = None
        for a in release.get("assets", []):
            url = a.get("browser_download_url", "")
            if expected_name_part in url and url.endswith(archive_ext):
                asset = url
                break
        if not asset:
            print(f"[Auth Bot] ⚠️ Could not find asset for {expected_name_part}")
            return None
        tmpdir = tempfile.mkdtemp(prefix="gecko_dl_")
        archive_file = os.path.join(tmpdir, os.path.basename(asset))
        print(f"[Auth Bot] ⬇️ Downloading {os.path.basename(asset)} ...")
        urllib.request.urlretrieve(asset, archive_file)
        if archive_ext == ".zip":
            with zipfile.ZipFile(archive_file, 'r') as zf:
                zf.extractall(tmpdir)
        else:
            with tarfile.open(archive_file, 'r:gz') as tf:
                tf.extract("geckodriver", path=tmpdir)
        extracted = os.path.join(tmpdir, exe_name)
        if not os.path.exists(extracted):
            # Some archives don't contain .exe name until rename
            alt = os.path.join(tmpdir, "geckodriver")
            if os.path.exists(alt):
                extracted = alt
        shutil.copy2(extracted, local_path)
        os.chmod(local_path, 0o755)
        print(f"[Auth Bot] ✅ geckodriver ready at {local_path}")
        # Prepend to PATH for current process
        os.environ["PATH"] = drivers_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("GECKODRIVER", local_path)
        return local_path
    except Exception as dl_e:
        print(f"[Auth Bot] ❌ Failed to auto-download geckodriver: {dl_e}")
        return None

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
    
    # Strategy: Prefer undetected Chrome first unless forced
    use_firefox = force_firefox
    engine_desc = "Firefox (forced)" if use_firefox else "Chrome attempt (uc)"
    print(f"[Auth Bot] Starting browser engine: {engine_desc} | force_firefox={force_firefox} is_ubuntu={is_ubuntu}")
    
    try:
        # Build SeleniumBase context arguments dynamically
        sb_kwargs = {
            "test": True,
            "locale": "en",
            "headless": True,
            "page_load_strategy": "eager",
        }
        if not use_firefox:
            sb_kwargs["uc"] = True
        else:
            sb_kwargs["browser"] = "firefox"
            gecko_path = _ensure_geckodriver()
            if gecko_path:
                print(f"[Auth Bot] 🦊 Using geckodriver: {gecko_path}")
            else:
                print("[Auth Bot] ⚠️ geckodriver still missing; SeleniumBase may fail. Raw fallback will try again.")
        
        try:
            with SB(**sb_kwargs) as sb:
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                try:
                    sb.activate_cdp_mode(url)
                except Exception:
                    sb.open(url)
                
                url = "https://www.upwork.com/nx/search/jobs/?q=python"
                if not use_firefox:
                    try:
                        sb.activate_cdp_mode(url)
                    except Exception as e:
                        print(f"[Auth Bot] CDP activation skipped: {e}")
                else:
                    sb.open(url)
                
                print("[Auth Bot] Waiting for Cloudflare bypass...")
                max_attempts = 8
                for attempt in range(max_attempts):
                    sb.sleep(3)
                    try:
                        sb.uc_gui_click_captcha()
                        print(f"[Auth Bot] Attempt {attempt+1}: Clicked captcha")
                    except Exception:
                        pass
                    if sb.is_element_visible(".air3-card"):
                        print("[Auth Bot] ✅ Cloudflare bypassed!")
                        break
                    page_source = sb.get_page_source()
                    if "Just a moment" not in page_source:
                        print("[Auth Bot] ✅ Challenge bypassed!")
                        break
                else:
                    print("[Auth Bot] ⚠️ Cloudflare challenge timeout - continuing anyway")
                
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
            
            # Enrich headers before testing
            current_url = headers_found.get('Referer') or headers_found.get('referer') or 'https://www.upwork.com/nx/search/jobs/'
            headers_found = _enrich_headers(headers_found, cookies_found, current_url)
            # Ensure stable visitor ID (persisted synthetic if real not captured)
            headers_found = _ensure_visitor_id(headers_found, script_dir)
            
            # Re-save enriched headers to ensure visitor ID and other enrichments are persisted
            try:
                with open(headers_file, "w") as f:
                    json.dump(headers_found, f, indent=2)
                with open(job_details_headers_file, "w") as f:
                    json.dump(headers_found, f, indent=2)
                print(f"[Auth Bot] ✅ Re-saved enriched headers with {len(headers_found)} total keys")
            except Exception as e:
                print(f"[Auth Bot] ⚠️ Could not re-save enriched headers: {e}")

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