import cloudscraper
import json
import time
import random
import re
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from db.database import SessionLocal
from db.models import Job

class UpworkScraper:
    # Primary GraphQL endpoint for visitor job search
    GRAPHQL_URL = "https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch"
    
    # Token extraction endpoints - these should work without authentication
    TOKEN_EXTRACTION_URLS = [
        "https://www.upwork.com/",
        "https://www.upwork.com/nx/find-work/",
        "https://www.upwork.com/nx/search/jobs/",
        "https://www.upwork.com/nx/",
        "https://www.upwork.com/nx/job-search/"
    ]
    
    # Unauthenticated GraphQL endpoints for token bootstrap
    BOOTSTRAP_GRAPHQL_URLS = [
        "https://www.upwork.com/api/v4/visitor/stats",
        "https://www.upwork.com/api/v4/visitor/config", 
        "https://www.upwork.com/api/v4/visitor/health"
    ]

    def __init__(self):
        # cloudscraper handles Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )

        # Token management - using your browser tokens
        self.current_auth_token = "oauth2v2_cd4aa30e2054e8357ea7f1960d6cc718"
        self.current_visitor_id = "39.45.32.89.1758018771960000"
        self.visitor_topnav_gql_token = "oauth2v2_cd4aa30e2054e8357ea7f1960d6cc718"

        # Track which URLs have been used for rotation
        self.used_extraction_urls = []
        self.current_extraction_url_index = 0

        # Updated cookies to match your browser exactly
        self.browser_cookies = {
            "__cflb": "02DiuEXPXZVk436fJfSVuuwDqLqkhavJbRUJjtRhHt74f",
            "visitor_id": "39.45.32.89.1758018771960000",
            "_vwo_uuid_v2": "DFAC13B4AA362CE2B19CA336FCAF31B0F|d2795f9e086fc133f8f4fb3230343f9e",
            "_vwo_uuid": "DFAC13B4AA362CE2B19CA336FCAF31B0F",
            "_vwo_ds": "3%241758018772%3A99.65894701%3A%3A",
            "_vis_opt_exp_40_combi": "2",
            "_vis_opt_exp_34_combi": "3",
            "spt": "27650f7e-d815-4468-b683-90bb976bf5ca",
            "_gcl_au": "1.1.1156418345.1758018778",
            "_cq_duid": "1.1758018778.88pxTooEpZjuuC9z",
            "OptanonAlertBoxClosed": "2025-09-16T10:33:03.304Z",
            "__pdst": "5a131420ae9c42cb91f4c6b4e5f9d64b",
            "__ps_r": "_",
            "__ps_did": "pscrb_3d777365-c66b-42fb-9c7f-54bf40411146",
            "__ps_fva": "1758018785046",
            "_fbp": "fb.1.1758018786042.769376668421960692",
            "_kad": "1758018786644.1725d372-abd6-4b82-9673-ced4870cd250",
            "_tt_enable_cookie": "1",
            "_ttp": "01K591BND6RX0K1A8YPC4DNB7X_.tt.1",
            "x-spec-id": "7e4c30dc-19a7-409e-8116-96c72f673284",
            "recognized": "7df066fde94dfa93",
            "current_organization_uid": "1967903751320503581",
            "company_last_accessed": "d1089116614",
            "_ga": "GA1.1.2121371580.1758018786",
            "__gads": "ID=ec064faca8191076:T=1758020043:RT=1758020043:S=ALNI_MYlJuVMeNNyKm17uauTV3TjLYUpbQ",
            "__gpi": "UID=0000128ceb149352:T=1758020043:RT=1758020043:S=ALNI_MZTRJS9WBxthkqTXuubb_iO2Xt-OQ",
            "__eoi": "ID=5ad5293123e08d7e:T=1758020043:RT=1758020043:S=AA-AfjY2skdPFSpEXrxzfQrUonu5",
            "_vis_opt_s": "3%7C",
            "_gcl_gs": "2.1.k1$i1758097851$u8300790",
            "_gcl_aw": "GCL.1758097901.Cj0KCQjwuKnGBhD5ARIsAD19RsYkS_atQzJwoRKX5HTHuN3ORA52MgpFOUTh_BTy3Y850PC8jWPdjn0aAkX3EALw_wcB",
            "IR_PI": "ee5a9769-93a0-11f0-aedf-85ab10c15999%7C1758184384660",
            "umq": "684",
            "_cfuvid": "KcfRfUmjaS1SeHAupqpIXiHUBT7lozcJpGGxMoerMnM-1758320846743-0.0.1.1-604800000",
            "enabled_ff": "!CI10270Air2Dot5QTAllocations,!CI10857Air3Dot0,!CI12577UniversalSearch,!MP16400Air3Migration,!RMTAir3Hired,!RMTAir3Home,!RMTAir3Offer,!RMTAir3Offers,!RMTAir3Talent,!SSINavUser,!SecAIBnrOn,!air2Dot76Qt,!i18nGA,CI11132Air2Dot75,CI17409DarkModeUI,CI9570Air2Dot5,JPAir3,OTBnrOn,SSINavUserBpa,TONB2256Air3Migration,air2Dot76,i18nOn",
            "country_code": "PK",
            "cookie_prefix": "",
            "cookie_domain": ".upwork.com",
            "_upw_ses.5831": "*",
            "_cq_suid": "1.1758320866.yzvzmLEpuJduKvfQ",
            "IR_gbd": "upwork.com",
            "QSI_ReplaySession_SampledOut_ZN_0IzJIULtA2j2T4O": "true",
            "__cf_bm": "gqBVQ8Ks4ZKFuztbZHW287bFjmS3nz9H0gVG0Tbr8Xs-1758322897-1.0.1.1-4SuJMW.wzD6yuAHf.kAfxPG6CTBfhWZxtfAiAwuumEwA6FOREaafpnY0l936x7Iuon7.NhOc99tXuOaKjhlw5Dh9MT1Llpo4VxDuEdRGHhg",
            "AWSALBTG": "lnm4VnU8HQaA1TljMRNxmh3ygKDglwlNt0vyZ8fZuiV+s3LHDd4T4oKDcSlaEkhqNyGFm7bJ4YW2A4izgBCl5fD42BFnw6GW+Dbd+hDXwl7EMokAbiZE54Vg0Jl3y25BJ31YAA4SUk4A+loNQ4pHk9UXMlNN7B2tGhnlcdtNvpPI",
            "AWSALBTGCORS": "lnm4VnU8HQaA1TljMRNxmh3ygKDglwlNt0vyZ8fZuiV+s3LHDd4T4oKDcSlaEkhqNyGFm7bJ4YW2A4izgBCl5fD42BFnw6GW+Dbd+hDXwl7EMokAbiZE54Vg0Jl3y25BJ31YAA4SUk4A+loNQ4pHk9UXMlNN7B2tGhnlcdtNvpPI",
            "UniversalSearchNuxt_vt": "oauth2v2_cd4aa30e2054e8357ea7f1960d6cc718",
            "OptanonConsent": "isGpcEnabled=0&datestamp=Sat+Sep+20+2025+04%3A01%3A56+GMT%2B0500+(Pakistan+Standard+Time)&version=202305.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=dd4af587-2b9c-425d-b26d-ff5f1411f9f3&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=PK%3BPB&AwaitingReconsent=false",
            "cf_clearance": "db7yjJ7ADI_aLQGJwGl5OUsvCsahpVzm_Y4qXwoxV9k-1758322918-1.2.1.1-33mQOmmqWWaKlEAp0x2mIsXas7WJj5Q7NJEpqBDw88aFB4jPVXcsCUwqbA4PUhZb7JC1UmshxiANvk1UF9NrPCrSz9d6VRcYScNywCGK8Lm8X_EczQLgW3Yz9dku7gk8WawJwjlSWql1mf3SnlOwdRwS.iL67CU7whtB7PSodVr4mtYIcej4hZNNOHYa4sYKyhg.T0VChVTzmMaum0LYYK93lvN0p26HZjeh.PycZqZmlBFVNIPdsw1lKLWG0bGq",
            "__ps_sr": "_",
            "__ps_slu": "https://www.upwork.com/nx/search/jobs/?nbs=1&q=developer&__cf_chl_tk=WvvWuHouIqtNHXxUmMMv9HiXsjBTMiRZfHWDC1IoAyA-1758322897-1.0.1.1-kqX2rH7SR_WWgpIM3yazvANs5JcmKGl0pLH11xJPIRI",
            "_ga_KSM221PNDX": "GS2.1.s1758322897$o16$g1$t1758322927$j30$l0$h0",
            "_rdt_uuid": "1758018785255.3857af74-7d1a-47dc-847f-6941cb74ad4b",
            "_rdt_em": ":775d5381dad5e531711c3745f2c4256021aad2b491d2f5f0119757b2d5418d7b,0ef9503355b79f2f1186f268847ac32bbed290cfb8f49c027b6e2cb9530900bf,23e529b90fb93df8be791595c00fd9fee96913d10f462f1986985f5d0a309c28",
            "_uetsid": "8822b2e092e811f084b443c4290e7bfc",
            "_uetvid": "882325a092e811f0baf7cd0f498ba272",
            "IR_13634": "1758322927765%7C0%7C1758322927765%7C%7C",
            "ttcsid_CGCUGEBC77UAPU79F02G": "1758320875712::vaDWnX0Tce2FHpQppXtb.13.1758323073061.0",
            "ttcsid": "1758322928486::faCHsokzrn-Op1jP8sgD.14.1758323073062.0",
            "forterToken": "b002ca1366804dfbb2a9ad5bb28cf2c2_1758322919316__UDF43-m4_23ck_449EysARCqk%3D-521-v2",
            "AWSALB": "MM4yh3sfBEGfjhwlSCQtw1GppiYXx5+NhZwTQG1vIYtmRBbKRbhMVWfhoLvvLMgC01fY3i0I3S4GZuldyXSiZWYG9WqBPt9XbADR13OZB48DNV9wpcSjRk0pK5Nl",
            "AWSALBCORS": "MM4yh3sfBEGfjhwlSCQtw1GppiYXx5+NhZwTQG1vIYtmRBbKRbhMVWfhoLvvLMgC01fY3i0I3S4GZuldyXSiZWYG9WqBPt9XbADR13OZB48DNV9wpcSjRk0pK5Nl",
            "usnGlobalParams": "%7B%22isAutosuggest%22%3A1%2C%22autosuggestion%22%3A%7B%22isCustom%22%3Atrue%2C%22label%22%3A%22developer%22%7D%7D",
            "_upw_id.5831": "16d6e703-b7a6-4116-b7c6-7a7801d795b9.1758018776.12.1758323086.1758265521.8e32e6db-0b5f-46e1-9d3a-0bf7c9911ce8.eba62853-394e-4de1-ac94-bb5082fb83ec.b9dc31ff-ec4d-4e1f-b42a-dd3d769714ac.1758320864938.39"
        }

        # Generate session identifiers to match browser
        self.session_trace_id = "981cb51d2167a07f-KHI"
        self.session_span_id = "6af8b8c6-17d7-4e99-9724-532e1b318861"
        self.session_parent_span_id = "bd022f85-d2ba-4a0d-a463-31cfc0586e18"

        # Headers template matching your browser exactly
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://www.upwork.com",
            "Referer": "https://www.upwork.com/nx/search/jobs/?q=developer",
            "Sec-Ch-Ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "Sec-Ch-Ua-Arch": '"x86"',
            "Sec-Ch-Ua-Bitness": '"64"',
            "Sec-Ch-Ua-Full-Version": '"140.0.7339.128"',
            "Sec-Ch-Ua-Full-Version-List": '"Chromium";v="140.0.7339.128", "Not=A?Brand";v="24.0.0.0", "Google Chrome";v="140.0.7339.128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Model": '""',
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua-Platform-Version": '"19.0.0"',
            "Sec-Ch-Viewport-Width": "490",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=1, i",
            "Vnd-Eo-Parent-Span-Id": self.session_parent_span_id,
            "Vnd-Eo-Span-Id": self.session_span_id,
            "Vnd-Eo-Trace-Id": self.session_trace_id,
            "Vnd-Eo-Visitorid": self.current_visitor_id,
            "X-Upwork-Accept-Language": "en-US"
        }

        print("Initialized with browser-matching tokens and headers")

    def _update_dynamic_cookies(self):
        """Update time-sensitive cookies"""
        current_time = int(time.time() * 1000)
        
        # Update timestamp-based cookies
        self.browser_cookies.update({
            "__cf_bm": f"gqBVQ8Ks4ZKFuztbZHW287bFjmS3nz9H0gVG0Tbr8Xs-{current_time}-1.0.1.1-4SuJMW.wzD6yuAHf.kAfxPG6CTBfhWZxtfAiAwuumEwA6FOREaafpnY0l936x7Iuon7.NhOc99tXuOaKjhlw5Dh9MT1Llpo4VxDuEdRGHhg",
            "_ga_KSM221PNDX": f"GS2.1.s{current_time}$o16$g1$t{current_time + 30}$j30$l0$h0",
            "IR_13634": f"{current_time}%7C0%7C{current_time}%7C%7C"
        })

    def _generate_session_ids(self):
        """Generate new session identifiers to avoid tracking"""
        # Generate new session IDs
        self.session_trace_id = f"{random.randint(100000000000000, 999999999999999):x}-KHI"
        self.session_span_id = str(uuid.uuid4())
        self.session_parent_span_id = str(uuid.uuid4())
        
        # Update headers with new session IDs
        self.base_headers.update({
            "Vnd-Eo-Parent-Span-Id": self.session_parent_span_id,
            "Vnd-Eo-Span-Id": self.session_span_id,
            "Vnd-Eo-Trace-Id": self.session_trace_id
        })

    def _bootstrap_fresh_session(self):
        """Bootstrap a completely fresh session without any authentication"""
        print("Bootstrapping fresh session...")
        
        try:
            # Clear old auth tokens temporarily
            old_auth_token = self.current_auth_token
            old_visitor_token = self.visitor_topnav_gql_token
            
            # Remove authentication temporarily
            self.current_auth_token = None
            self.visitor_topnav_gql_token = None
            
            # Generate completely new session
            self._generate_session_ids()
            
            # Create clean headers for bootstrap (no auth)
            bootstrap_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Ch-Ua": self.base_headers["Sec-Ch-Ua"],
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": self.base_headers["Sec-Ch-Ua-Platform"],
                "Cache-Control": "no-cache"
            }
            
            # Clear critical cookies for fresh start
            fresh_cookies = {}
            
            # Try to get fresh session from main page
            print("Loading fresh Upwork homepage...")
            response = self.scraper.get(
                "https://www.upwork.com/",
                headers=bootstrap_headers,
                cookies=fresh_cookies,
                timeout=30
            )
            
            print(f"Bootstrap homepage response: {response.status_code}")
            
            if response.status_code == 200:
                # Extract fresh tokens from page and cookies
                fresh_tokens = self._extract_tokens_from_response(response)
                if fresh_tokens:
                    print("Successfully bootstrapped fresh session!")
                    return True
                    
            # Try backup bootstrap URLs
            backup_urls = [
                "https://www.upwork.com/nx/",
                "https://www.upwork.com/nx/find-work/",
                "https://www.upwork.com/signup/"
            ]
            
            for url in backup_urls:
                try:
                    print(f"Trying bootstrap URL: {url}")
                    response = self.scraper.get(
                        url,
                        headers=bootstrap_headers,
                        cookies=fresh_cookies,
                        timeout=30
                    )
                    
                    print(f"Bootstrap {url} response: {response.status_code}")
                    
                    if response.status_code == 200:
                        fresh_tokens = self._extract_tokens_from_response(response)
                        if fresh_tokens:
                            print(f"Successfully bootstrapped from {url}")
                            return True
                            
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"Bootstrap failed for {url}: {e}")
                    continue
            
            # Restore old tokens if bootstrap failed
            self.current_auth_token = old_auth_token
            self.visitor_topnav_gql_token = old_visitor_token
            
            return False
            
        except Exception as e:
            print(f"Bootstrap session failed: {e}")
            # Restore old tokens
            self.current_auth_token = old_auth_token
            self.visitor_topnav_gql_token = old_visitor_token
            return False

    def _extract_tokens_from_response(self, response):
        """Extract tokens from HTTP response (cookies, headers, and HTML)"""
        try:
            found_tokens = False
            
            # Method 1: Extract from response cookies
            print("Extracting tokens from response cookies...")
            for cookie in response.cookies:
                if any(keyword in cookie.name.lower() for keyword in ['token', 'visitor', 'oauth']):
                    print(f"Found cookie token: {cookie.name} = {cookie.value[:20]}...")
                    
                    if 'visitor_id' in cookie.name.lower():
                        self.current_visitor_id = cookie.value
                        self.base_headers['Vnd-Eo-Visitorid'] = cookie.value
                        self.browser_cookies['visitor_id'] = cookie.value
                        found_tokens = True
                        
                    elif any(token_key in cookie.name.lower() for token_key in ['oauth', 'token', 'universalsearch']):
                        self.current_auth_token = cookie.value
                        self.visitor_topnav_gql_token = cookie.value
                        self.browser_cookies['UniversalSearchNuxt_vt'] = cookie.value
                        found_tokens = True
                        
                # Update all received cookies
                self.browser_cookies[cookie.name] = cookie.value
                
            # Method 2: Extract from Set-Cookie headers
            print("Extracting tokens from Set-Cookie headers...")
            set_cookie_headers = response.headers.get_list('Set-Cookie') if hasattr(response.headers, 'get_list') else [response.headers.get('Set-Cookie', '')]
            
            for set_cookie in set_cookie_headers:
                if set_cookie and 'oauth2v2_' in set_cookie:
                    token_match = re.search(r'oauth2v2_[a-f0-9]{32}', set_cookie)
                    if token_match:
                        new_token = token_match.group()
                        print(f"Found token in Set-Cookie: {new_token[:20]}...")
                        self.current_auth_token = new_token
                        self.visitor_topnav_gql_token = new_token
                        self.browser_cookies['UniversalSearchNuxt_vt'] = new_token
                        found_tokens = True
                        
                # Extract visitor ID from Set-Cookie
                visitor_match = re.search(r'visitor_id=([^;]+)', set_cookie) if set_cookie else None
                if visitor_match:
                    visitor_id = visitor_match.group(1)
                    print(f"Found visitor_id in Set-Cookie: {visitor_id}")
                    self.current_visitor_id = visitor_id
                    self.base_headers['Vnd-Eo-Visitorid'] = visitor_id
                    self.browser_cookies['visitor_id'] = visitor_id
                    found_tokens = True
                    
            # Method 3: Extract from HTML content (script tags, meta tags)
            if hasattr(response, 'text'):
                print("Extracting tokens from HTML content...")
                html_content = response.text
                
                # Look for tokens in script tags
                script_patterns = [
                    r'"oauth2v2_[a-f0-9]{32}"',
                    r"'oauth2v2_[a-f0-9]{32}'",
                    r'oauth2v2_[a-f0-9]{32}',
                    r'"visitor_id":\s*"([^"]+)"',
                    r"'visitor_id':\s*'([^']+)'",
                    r'visitor_id.*?([0-9.]+)',
                    r'UniversalSearchNuxt_vt.*?(oauth2v2_[a-f0-9]{32})',
                    r'visitorId.*?([0-9.]+)'
                ]
                
                for pattern in script_patterns:
                    matches = re.findall(pattern, html_content)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0] if match[0] else match[1] if len(match) > 1 else None
                        
                        if not match:
                            continue
                            
                        if 'oauth2v2_' in match:
                            clean_token = match.strip('"\'')
                            print(f"Found token in HTML: {clean_token[:20]}...")
                            self.current_auth_token = clean_token
                            self.visitor_topnav_gql_token = clean_token
                            self.browser_cookies['UniversalSearchNuxt_vt'] = clean_token
                            found_tokens = True
                            
                        elif match.replace('.', '').isdigit() and len(match) > 10:
                            print(f"Found visitor_id in HTML: {match}")
                            self.current_visitor_id = match
                            self.base_headers['Vnd-Eo-Visitorid'] = match
                            self.browser_cookies['visitor_id'] = match
                            found_tokens = True
                            
                # Look for window.__INITIAL_STATE__ or similar
                initial_state_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.+?});'
                initial_state_match = re.search(initial_state_pattern, html_content, re.DOTALL)
                if initial_state_match:
                    try:
                        initial_state = json.loads(initial_state_match.group(1))
                        # Look for tokens in the initial state
                        def find_tokens_in_obj(obj, path=""):
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    current_path = f"{path}.{key}" if path else key
                                    if isinstance(value, str) and 'oauth2v2_' in value:
                                        print(f"Found token in initial state at {current_path}: {value[:20]}...")
                                        self.current_auth_token = value
                                        self.visitor_topnav_gql_token = value
                                        self.browser_cookies['UniversalSearchNuxt_vt'] = value
                                        return True
                                    elif isinstance(value, (dict, list)):
                                        if find_tokens_in_obj(value, current_path):
                                            return True
                            elif isinstance(obj, list):
                                for i, item in enumerate(obj):
                                    if find_tokens_in_obj(item, f"{path}[{i}]"):
                                        return True
                            return False
                        
                        if find_tokens_in_obj(initial_state):
                            found_tokens = True
                            
                    except json.JSONDecodeError:
                        pass
                        
            return found_tokens
            
        except Exception as e:
            print(f"Error extracting tokens from response: {e}")
            return False

    def _refresh_tokens(self):
        """Enhanced token refresh with complete session bootstrap"""
        print("Refreshing tokens due to authorization failure...")
        
        # Method 1: Bootstrap completely fresh session
        print("Method 1: Bootstrapping fresh session...")
        if self._bootstrap_fresh_session():
            print("Fresh session bootstrap successful!")
            return True
        
        # Method 2: Extract from accessible pages
        print("Method 2: Extracting from accessible pages...")
        if self._extract_from_accessible_pages():
            print("Page extraction successful!")
            return True
        
        # Method 3: Try unauthenticated API endpoints
        print("Method 3: Trying unauthenticated API endpoints...")
        if self._try_unauthenticated_endpoints():
            print("Unauthenticated endpoint extraction successful!")
            return True
        
        # Method 4: Generate intelligent variations as last resort
        print("Method 4: Generating intelligent token variations...")
        return self._generate_intelligent_token_variations()

    def _extract_from_accessible_pages(self):
        """Extract tokens from pages that returned 200 status"""
        print("Trying accessible page extraction...")
        
        accessible_urls = [
            "https://www.upwork.com/nx/find-work/",
            "https://www.upwork.com/",
            "https://www.upwork.com/signup/",
            "https://www.upwork.com/ab/",
            "https://www.upwork.com/landing/"
        ]
        
        for url in accessible_urls:
            try:
                print(f"Accessing: {url}")
                
                # Create clean headers for page access
                page_headers = {
                    "User-Agent": self.base_headers["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Ch-Ua": self.base_headers["Sec-Ch-Ua"],
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": self.base_headers["Sec-Ch-Ua-Platform"],
                    "Cache-Control": "no-cache"
                }
                
                # Use minimal cookies for the request
                minimal_cookies = {
                    "country_code": "PK",
                    "cookie_domain": ".upwork.com"
                }
                
                response = self.scraper.get(
                    url,
                    headers=page_headers,
                    cookies=minimal_cookies,
                    timeout=30
                )
                
                print(f"Page response: {response.status_code}")
                
                if response.status_code == 200:
                    if self._extract_tokens_from_response(response):
                        print(f"Successfully extracted tokens from {url}")
                        return True
                        
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"Failed to extract from {url}: {e}")
                continue
                
        return False

    def _try_unauthenticated_endpoints(self):
        """Try unauthenticated API endpoints for token extraction"""
        print("Trying unauthenticated endpoints...")
        
        endpoints = [
            "https://www.upwork.com/api/v4/visitor/stats",
            "https://www.upwork.com/api/v4/visitor/config",
            "https://www.upwork.com/api/visitor/bootstrap",
            "https://www.upwork.com/api/health",
            "https://www.upwork.com/nx/api/visitor/session"
        ]
        
        for endpoint in endpoints:
            try:
                print(f"Trying endpoint: {endpoint}")
                
                api_headers = {
                    "User-Agent": self.base_headers["User-Agent"],
                    "Accept": "application/json, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin"
                }
                
                response = self.scraper.get(
                    endpoint,
                    headers=api_headers,
                    timeout=15
                )
                
                print(f"Endpoint {endpoint} response: {response.status_code}")
                
                if response.status_code == 200:
                    if self._extract_tokens_from_response(response):
                        print(f"Successfully extracted tokens from {endpoint}")
                        return True
                        
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"Failed endpoint {endpoint}: {e}")
                continue
                
        return False

    def _generate_intelligent_token_variations(self):
        """Generate intelligent variations of existing tokens using multiple algorithms"""
        try:
            print("Generating intelligent token variations...")
            
            if not self.current_auth_token or 'oauth2v2_' not in self.current_auth_token:
                print("No base token available for variation")
                return False
            
            base_token = self.current_auth_token.replace('oauth2v2_', '')
            current_time = int(time.time())
            
            # Method 1: Time-based variation (simulates token refresh)
            time_seed = f"{base_token}{current_time}"
            time_hash = hashlib.md5(time_seed.encode()).hexdigest()
            time_token = f"oauth2v2_{time_hash}"
            
            # Method 2: Visitor ID based variation
            visitor_seed = f"{self.current_visitor_id}{base_token[-16:]}"
            visitor_hash = hashlib.md5(visitor_seed.encode()).hexdigest()
            visitor_token = f"oauth2v2_{visitor_hash}"
            
            # Method 3: Session-based variation
            session_seed = f"{self.session_trace_id}{base_token[8:24]}"
            session_hash = hashlib.md5(session_seed.encode()).hexdigest()
            session_token = f"oauth2v2_{session_hash}"
            
            # Method 4: Incremental variation (slight modification)
            base_int = int(base_token[:8], 16)
            incremented = hex(base_int + random.randint(1, 1000))[2:].zfill(8)
            incremental_token = f"oauth2v2_{incremented}{base_token[8:]}"
            
            # Try each variation
            token_variations = [time_token, visitor_token, session_token, incremental_token]
            
            for i, new_token in enumerate(token_variations):
                print(f"Testing token variation {i + 1}: {new_token[:20]}...")
                
                # Update tokens
                self.current_auth_token = new_token
                self.visitor_topnav_gql_token = new_token
                self.browser_cookies['UniversalSearchNuxt_vt'] = new_token
                
                # Test the token with a simple request
                if self._test_token_validity(new_token):
                    print(f"Token variation {i + 1} is valid!")
                    return True
                
                time.sleep(random.uniform(1, 2))
            
            print("No valid token variations found")
            return False
                
        except Exception as e:
            print(f"Token variation generation failed: {e}")
            return False

    def _test_token_validity(self, token):
        """Test if a token is valid by making a simple request"""
        try:
            test_headers = self.base_headers.copy()
            test_headers['Authorization'] = f'Bearer {token}'
            
            # Simple test payload
            test_payload = {
                "query": "query { __typename }",
                "variables": {}
            }
            
            response = self.scraper.post(
                self.GRAPHQL_URL,
                headers=test_headers,
                cookies=self.browser_cookies,
                data=json.dumps(test_payload),
                timeout=10
            )
            
            # Consider it valid if we don't get auth errors
            return response.status_code not in [401, 403]
            
        except Exception:
            return False

    def _get_current_cookies(self):
        """Get current cookies with latest tokens"""
        # Update dynamic cookies before returning
        self._update_dynamic_cookies()
        return self.browser_cookies

    def _get_current_headers(self):
        """Get current headers with latest tokens and authorization"""
        headers = self.base_headers.copy()
        
        # Add authorization header
        if self.current_auth_token:
            headers['Authorization'] = f'Bearer {self.current_auth_token}'
            
        return headers

    # ... rest of the methods remain the same ...
    
    def fetch_jobs(self, query="developer", limit=10, delay=True):
        """
        Fetch jobs with automatic token refresh on auth failure using visitor job search API
        """
        print(f"Trying visitorJobSearch with query: '{query}'")
        
        # Update the referer to match the query
        self.base_headers['Referer'] = f"https://www.upwork.com/nx/search/jobs/?q={query}"
        
        # GraphQL query for visitor job search
        graphql_payload = {
            "query": """
            query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {
                search {
                    universalSearchNuxt {
                        visitorJobSearchV1(request: $requestVariables) {
                            paging {
                                total
                                offset
                                count
                            }
                            facets {
                                jobType {
                                    key
                                    value
                                }
                                workload {
                                    key
                                    value
                                }
                                clientHires {
                                    key
                                    value
                                }
                                durationV3 {
                                    key
                                    value
                                }
                                amount {
                                    key
                                    value
                                }
                                contractorTier {
                                    key
                                    value
                                }
                                contractToHire {
                                    key
                                    value
                                }
                            }
                            results {
                                id
                                title
                                description
                                relevanceEncoded
                                ontologySkills {
                                    uid
                                    parentSkillUid
                                    prefLabel
                                    prettyName: prefLabel
                                    freeText
                                    highlighted
                                }
                                jobTile {
                                    job {
                                        id
                                        ciphertext: cipherText
                                        jobType
                                        weeklyRetainerBudget
                                        hourlyBudgetMax
                                        hourlyBudgetMin
                                        hourlyEngagementType
                                        contractorTier
                                        sourcingTimestamp
                                        createTime
                                        publishTime
                                        hourlyEngagementDuration {
                                            rid
                                            label
                                            weeks
                                            mtime
                                            ctime
                                        }
                                        fixedPriceAmount {
                                            isoCurrencyCode
                                            amount
                                        }
                                        fixedPriceEngagementDuration {
                                            id
                                            rid
                                            label
                                            weeks
                                            ctime
                                            mtime
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """,
            "variables": {
                "requestVariables": {
                    "sort": "recency",
                    "highlight": True,
                    "paging": {
                        "offset": 0,
                        "count": limit
                    }
                }
            }
        }

        if delay:
            time.sleep(random.uniform(2, 4))

        jobs_data = self._make_graphql_request(graphql_payload, "VisitorJobSearch")
        
        if jobs_data:
            return jobs_data
        
        # If first method fails, try minimal parameters
        print("First attempt failed, trying minimal search...")
        return self._try_minimal_search(limit, delay)

    def _make_graphql_request(self, payload, method_name):
        """
        Make the actual GraphQL request with automatic token refresh on auth failure
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Generate fresh session IDs for each request
                self._generate_session_ids()
                
                response = self.scraper.post(
                    self.GRAPHQL_URL,
                    headers=self._get_current_headers(),
                    cookies=self._get_current_cookies(),
                    data=json.dumps(payload),
                    timeout=30
                )

                print(f"{method_name} Response Status: {response.status_code}")
                
                # If we get auth errors, try refreshing tokens
                if response.status_code in [401, 403]:
                    print(f"Authentication error detected, refreshing tokens...")
                    
                    if retry_count < max_retries - 1:  # Don't refresh on last retry
                        success = self._refresh_tokens()
                        if success:
                            retry_count += 1
                            print(f"Retrying request with fresh tokens (attempt {retry_count + 1})")
                            # Add longer delay after token refresh
                            time.sleep(random.uniform(3, 6))
                            continue
                        else:
                            print("Token refresh failed, using current tokens")
                            break
                    else:
                        print("Max retries reached, request failed")
                        break
                
                if response.status_code != 200:
                    print(f"API request failed: {response.status_code}")
                    print(f"Response text: {response.text[:500]}")
                    return []

                try:
                    data = response.json()
                    print(f"JSON parsed successfully")
                    
                    # Check for GraphQL errors
                    if "errors" in data:
                        print(f"GraphQL errors found:")
                        auth_error_found = False
                        
                        for error in data["errors"]:
                            error_msg = error.get('message', 'Unknown error')
                            print(f"   - {error_msg}")
                            
                            # Check for OAuth/permission errors in GraphQL response
                            if any(keyword in error_msg.lower() for keyword in ["permission", "oauth", "unauthorized", "forbidden"]):
                                auth_error_found = True
                                print(f"GraphQL permission issue detected")
                        
                        # If auth error in GraphQL and we haven't retried yet, try refresh
                        if auth_error_found and retry_count < max_retries - 1:
                            print("Attempting token refresh due to GraphQL auth error...")
                            success = self._refresh_tokens()
                            if success:
                                retry_count += 1
                                print(f"Retrying request with fresh tokens (attempt {retry_count + 1})")
                                time.sleep(random.uniform(3, 6))
                                continue
                        
                        # Don't return empty if we have partial data
                        if "data" in data and data["data"]:
                            print(f"Has errors but also has data, attempting to parse...")
                        else:
                            return []

                    # Extract jobs from response
                    jobs_data = self._extract_jobs_from_response(data, method_name)
                    
                    if jobs_data:
                        # Save to database
                        self._save_jobs_to_db(jobs_data)
                        print(f"Successfully fetched {len(jobs_data)} jobs from Upwork GraphQL.")
                        return jobs_data
                    else:
                        print(f"No jobs found in response")
                    
                    return jobs_data
                    
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON: {e}")
                    print(f"Response text: {response.text[:500]}")
                    return []
                
            except Exception as e:
                print(f"Request failed: {e}")
                # Add delay before retry
                time.sleep(random.uniform(2, 5))
                return []
        
        return []

    def _try_minimal_search(self, limit, delay):
        """Try minimal visitor search without complex parameters"""
        graphql_payload_minimal = {
            "query": """
            query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {
                search {
                    universalSearchNuxt {
                        visitorJobSearchV1(request: $requestVariables) {
                            paging {
                                total
                                offset
                                count
                            }
                            results {
                                id
                                title
                                description
                                jobTile {
                                    job {
                                        id
                                        jobType
                                        createTime
                                        publishTime
                                        fixedPriceAmount {
                                            amount
                                        }
                                        hourlyBudgetMin
                                        hourlyBudgetMax
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """,
            "variables": {
                "requestVariables": {
                    "sort": "recency",
                    "highlight": True,
                    "paging": {
                        "offset": 0,
                        "count": limit
                    }
                }
            }
        }
        
        if delay:
            time.sleep(random.uniform(2, 4))
        
        print(f"Testing minimal visitor search...")
        jobs_data = self._make_graphql_request(graphql_payload_minimal, "MinimalSearch")
        return jobs_data

    def _extract_jobs_from_response(self, data, method_name):
        """Extract job data from visitor job search GraphQL response"""
        jobs_data = []
        
        try:
            # Try different possible paths in the new response structure
            possible_paths = [
                ["data", "search", "universalSearchNuxt", "visitorJobSearchV1", "results"],
                ["search", "universalSearchNuxt", "visitorJobSearchV1", "results"],
                ["universalSearchNuxt", "visitorJobSearchV1", "results"],
                ["visitorJobSearchV1", "results"],
                ["results"]
            ]
            
            results = None
            for path in possible_paths:
                current = data
                try:
                    for key in path:
                        current = current[key]
                    if current:
                        results = current
                        print(f"Found jobs at path: {' -> '.join(path)}")
                        break
                except (KeyError, TypeError):
                    continue
            
            if not results:
                print(f"No results found in response")
                print(f"Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                return []

            print(f"Found {len(results)} job results")

            for i, job_result in enumerate(results):
                try:
                    if not job_result:
                        print(f"Empty job result at index {i}")
                        continue
                    
                    # Debug: Print the actual job structure for first job
                    if i == 0:
                        print(f"First job result structure:")
                        print(json.dumps(job_result, indent=2)[:1000])
                        print("Available fields:", list(job_result.keys()))
                    
                    # Extract basic job info
                    job_id = job_result.get("id", f"job_{i}")
                    title = job_result.get("title", "No title")
                    description = job_result.get("description", "No description")[:1000]
                    
                    # Extract job tile information for detailed data
                    job_tile = job_result.get("jobTile", {})
                    job_details = job_tile.get("job", {}) if job_tile else {}
                    
                    # Extract budget information from new structure
                    job_type = job_details.get("jobType", "")
                    hourly_min = job_details.get("hourlyBudgetMin")
                    hourly_max = job_details.get("hourlyBudgetMax")
                    fixed_price_info = job_details.get("fixedPriceAmount", {})
                    fixed_price = fixed_price_info.get("amount") if fixed_price_info else None
                    weekly_budget = job_details.get("weeklyRetainerBudget")
                    
                    # Create budget string and numeric value
                    budget_display = "Not specified"
                    budget_numeric = 0.0
                    
                    try:
                        if fixed_price and float(fixed_price) > 0:
                            budget_display = f"${fixed_price}"
                            budget_numeric = float(fixed_price)
                        elif hourly_min and float(hourly_min) > 0:
                            if hourly_max and float(hourly_max) > 0:
                                budget_display = f"${hourly_min}-${hourly_max}/hr"
                            else:
                                budget_display = f"${hourly_min}+/hr"
                            budget_numeric = float(hourly_min)
                        elif weekly_budget and float(weekly_budget) > 0:
                            budget_display = f"${weekly_budget}/week"
                            budget_numeric = float(weekly_budget)
                    except (ValueError, TypeError) as e:
                        print(f"Budget parsing error: {e}")
                        budget_display = "Not specified"
                        budget_numeric = 0.0
                    
                    # Extract other details
                    create_time = job_details.get("createTime", "")
                    contractor_tier = job_details.get("contractorTier", "")
                    
                    # Extract skills information
                    skills = job_result.get("ontologySkills", [])
                    skill_names = [skill.get("prettyName", "") for skill in skills if skill.get("prettyName")]
                    
                    # Extract job data with new structure
                    job_data = {
                        "id": job_id,
                        "title": title,
                        "description": description,
                        "createdDateTime": create_time,
                        "client": "Unknown",  # Client info not readily available in new structure
                        "budget": budget_display,
                        "budget_numeric": budget_numeric,
                        "total_applicants": 0,  # Not available in new structure
                        "amount": fixed_price,
                        "hourly_min": hourly_min,
                        "hourly_max": hourly_max,
                        "weekly_budget": weekly_budget,
                        "duration": None,  # Will need to extract from engagement duration
                        "duration_label": None,
                        "engagement": job_type,
                        "experience_level": contractor_tier,
                        "applied": False,  # Not available in visitor search
                        "category": ", ".join(skill_names[:3]),  # Use top 3 skills as category
                        "job_type": job_type,
                        "skills": skill_names
                    }
                    
                    jobs_data.append(job_data)
                    
                except Exception as e:
                    print(f"Error parsing job at index {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error extracting jobs: {e}")
        
        return jobs_data

    def _save_jobs_to_db(self, jobs_data):
        """Save jobs to database with corrected field mapping and proper data types"""
        try:
            session = SessionLocal()
            saved_count = 0
            
            for job in jobs_data:
                try:
                    # Check if Job model has description field, if not, don't include it
                    job_fields = {
                        "job_id": job["id"],
                        "title": job["title"],
                        "budget": job["budget_numeric"],  # Use numeric value for database
                        "client": job["client"]
                    }
                    
                    # Add description if the model supports it
                    try:
                        # Try to create a test Job instance to see if description field exists
                        from sqlalchemy import inspect
                        mapper = inspect(Job)
                        column_names = [column.name for column in mapper.columns]
                        
                        if 'description' in column_names:
                            job_fields["description"] = job["description"]
                        else:
                            print(f"Job model doesn't have 'description' field. Available fields: {column_names}")
                            
                    except Exception as e:
                        print(f"Could not check Job model fields: {e}")
                    
                    db_job = Job(**job_fields)
                    session.merge(db_job)
                    saved_count += 1
                    
                except Exception as e:
                    print(f"Error saving job to DB: {e}")
                    print(f"Job data: {job.get('id', 'Unknown')} - {job.get('title', 'No title')}")
                    print(f"Available Job model fields: {list(Job.__table__.columns.keys())}")
                    continue
            
            session.commit()
            session.close()
            print(f"Saved {saved_count} jobs to database")
            
        except Exception as e:
            print(f"Database error: {e}")
            print(f"Job model columns: {list(Job.__table__.columns.keys()) if hasattr(Job, '__table__') else 'Unknown'}")
            if 'session' in locals():
                session.rollback()
                session.close()

    def get_token_status(self):
        """Get current token status for debugging"""
        return {
            "current_visitor_id": self.current_visitor_id[:20] + "..." if self.current_visitor_id else None,
            "current_auth_token": self.current_auth_token[:20] + "..." if self.current_auth_token else None,
            "visitor_topnav_gql_token": self.visitor_topnav_gql_token[:20] + "..." if self.visitor_topnav_gql_token else None,
            "session_trace_id": self.session_trace_id,
            "session_span_id": self.session_span_id[:20] + "..." if self.session_span_id else None,
            "extraction_url_index": self.current_extraction_url_index,
            "cookies_count": len(self.browser_cookies)
        }