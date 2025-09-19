import cloudscraper
import json
import time
import random
from datetime import datetime, timedelta
from db.database import SessionLocal
from db.models import Job

class UpworkScraper:
    # Updated GraphQL endpoint for visitor job search
    GRAPHQL_URL = "https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch"
    TOKEN_EXTRACTION_URL = "https://www.upwork.com/nx/search/jobs/"  # Page to extract tokens from

    def __init__(self):
        # cloudscraper handles Cloudflare
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )

        # Token management
        self.current_auth_token = None
        self.current_visitor_id = None
        self.current_visitor_gql_token = None

        # Initialize with existing tokens (fallback)
        self.fallback_cookies = {
            "__cf_bm": "3vqBoAx1SWYvKY1mM0UtKBxT4kGgLARR2kPPyW1SCj0-1758215029-1.0.1.1-EV4rvYNI8Ap5aTJkdk6lSIUEMN3S8vpB_aK_.gmyqG96CyGf4EsyTHsBEaIXpNTjqY5r7a7buTIBavugzr3P9S8sNBGtx6PtahQLzM7Y7P0",
            "visitor_gql_token": "oauth2v2_c283b8178b24567f7e9880f4df857ac0",
            "visitor_id": "39.45.32.89.1758018771960000",
            "_upw_ses.5831": "*",
            "_upw_id.5831": "16d6e703-b7a6-4116-b7c6-7a7801d795b9.1758018776.8.1758215136.1758202399.208f1741-e94a-4d4d-a9a0-9357fe0c30fd.2708a9ca-c12b-47e6-9ff6-e91765660eb5.9416dd98-2578-4c25-9dc5-8eff4e3d0590.1758215122331.14"
        }

        self.fallback_auth_token = "oauth2v2_52409f88c9b777a931f281db2598889"

        # Headers template
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Referer": "https://www.upwork.com/nx/search/jobs/?nbs=1&q=developer",
            "Origin": "https://www.upwork.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "x-trace-id": "98126d692669a03b-SIN",
            "x-span-id": "05334ad6-4880-4bec-9afa-30f8b6b69735",
        }

        # Initialize with fallback tokens
        self._initialize_fallback_tokens()

    def _initialize_fallback_tokens(self):
        """Initialize with fallback tokens"""
        self.current_visitor_gql_token = self.fallback_cookies.get('visitor_gql_token')
        self.current_visitor_id = self.fallback_cookies.get('visitor_id')
        self.current_auth_token = self.fallback_auth_token
        print("✅ Initialized with fallback tokens")

    def _extract_tokens_from_page(self):
        """Extract visitor tokens and auth token from Upwork page"""
        try:
            print("🔄 Extracting fresh tokens from Upwork page...")
            
            # First, get the page to extract tokens
            response = self.scraper.get(
                self.TOKEN_EXTRACTION_URL,
                headers={
                    "User-Agent": self.base_headers["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to load token extraction page: {response.status_code}")
                return False

            # Extract tokens from cookies
            extracted_cookies = {}
            for cookie in response.cookies:
                extracted_cookies[cookie.name] = cookie.value

            # Extract visitor_gql_token and visitor_id from cookies
            visitor_gql_token = extracted_cookies.get('visitor_gql_token')
            visitor_id = extracted_cookies.get('visitor_id')
            
            if not visitor_gql_token or not visitor_id:
                print("❌ Could not extract visitor tokens from cookies")
                print(f"Available cookies: {list(extracted_cookies.keys())}")
                return False

            # Try to extract auth token from page content or make a test request
            auth_token = self._extract_auth_token_from_requests(extracted_cookies, visitor_id)
            
            if auth_token:
                self.current_visitor_gql_token = visitor_gql_token
                self.current_visitor_id = visitor_id
                self.current_auth_token = auth_token
                
                print(f"✅ Successfully extracted tokens:")
                print(f"   - Visitor ID: {visitor_id}")
                print(f"   - Visitor GQL Token: {visitor_gql_token[:20]}...")
                print(f"   - Auth Token: {auth_token[:20]}...")
                
                return True
            else:
                print("❌ Could not extract auth token")
                return False

        except Exception as e:
            print(f"❌ Error extracting tokens: {e}")
            return False

    def _extract_auth_token_from_requests(self, cookies, visitor_id):
        """Enhanced auth token extraction with multiple fallback methods"""
        try:
            print("🔍 Trying to extract auth token...")
            
            # Method 1: Use visitor_gql_token as auth token (most common case)
            visitor_gql_token = cookies.get('visitor_gql_token')
            if visitor_gql_token and visitor_gql_token.startswith('oauth2v2_'):
                print("🔄 Using visitor_gql_token as auth token")
                return visitor_gql_token
            
            # Method 2: Try to make a test GraphQL request to trigger auth token generation
            print("🧪 Testing GraphQL endpoint for auth token extraction...")
            
            test_headers = self.base_headers.copy()
            test_headers.update({
                "x-visitor-id": visitor_id,
                "User-Agent": random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                ])
            })
            
            # Very simple query that shouldn't require authentication
            test_payload = {
                "query": "{ __typename }"
            }
            
            response = self.scraper.post(
                self.GRAPHQL_URL,
                headers=test_headers,
                cookies=cookies,
                data=json.dumps(test_payload),
                timeout=15
            )
            
            print(f"🧪 Test GraphQL response: {response.status_code}")
            
            # Method 3: Check response headers for auth tokens
            auth_header = response.headers.get('Authorization')
            if auth_header and 'oauth2v2_' in auth_header:
                token_match = re.search(r'oauth2v2_[a-f0-9]{32}', auth_header)
                if token_match:
                    print("🔍 Found auth token in response headers")
                    return token_match.group()
            
            # Method 4: Parse error response for token hints
            if response.status_code in [401, 403]:
                try:
                    error_data = response.json()
                    if 'errors' in error_data:
                        for error in error_data['errors']:
                            error_msg = error.get('message', '')
                            if 'oauth2v2_' in error_msg:
                                import re
                                token_match = re.search(r'oauth2v2_[a-f0-9]{32}', error_msg)
                                if token_match:
                                    print("🔍 Found auth token in error message")
                                    return token_match.group()
                except:
                    pass
            
            # Method 5: Extract from Set-Cookie headers in the response
            set_cookies = response.headers.get('Set-Cookie', '')
            if 'oauth2v2_' in set_cookies:
                token_match = re.search(r'oauth2v2_[a-f0-9]{32}', set_cookies)
                if token_match:
                    print("🔍 Found auth token in Set-Cookie header")
                    return token_match.group()
            
            # Method 6: Generate a derived token (if pattern is known)
            if visitor_gql_token:
                print("🔄 Attempting to derive auth token from visitor token")
                # This is a placeholder for actual token derivation logic
                # You would need to reverse engineer how Upwork generates auth tokens
                # For now, we'll try some common patterns
                
                # Sometimes they just change a prefix or suffix
                derived_candidates = [
                    visitor_gql_token,  # Sometimes they're identical
                    visitor_gql_token.replace('oauth2v2_', 'Bearer_oauth2v2_'),
                    # Add more patterns as you discover them
                ]
                
                for candidate in derived_candidates:
                    if candidate and candidate.startswith('oauth2v2_'):
                        return candidate
            
            print("❌ Could not extract auth token using any method")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting auth token: {e}")
            return None

    def _refresh_tokens(self):
        """Enhanced token refresh with better error handling"""
        print("🔄 Refreshing tokens due to authorization failure...")
        
        # First, try a quick cookie refresh without full page load
        quick_success = self._quick_token_refresh()
        if quick_success:
            return True
        
        # If quick refresh fails, do full token extraction
        success = self._extract_tokens_from_page()
        
        if not success:
            print("⚠️ Token extraction failed, keeping current fallback tokens")
            # If all else fails, try rotating the existing tokens
            return self._rotate_fallback_tokens()
        
        return True

    def _quick_token_refresh(self):
        """Try to refresh tokens with a lightweight request"""
        try:
            print("⚡ Attempting quick token refresh...")
            
            # Make a simple request to a lightweight endpoint
            response = self.scraper.get(
                "https://www.upwork.com/ab/account-security/api/health",
                headers={
                    "User-Agent": random.choice([
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                    ]),
                    "Accept": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200 and response.cookies:
                # Extract new tokens from cookies
                new_cookies = {cookie.name: cookie.value for cookie in response.cookies}
                
                visitor_gql_token = new_cookies.get('visitor_gql_token')
                visitor_id = new_cookies.get('visitor_id')
                
                if visitor_gql_token and visitor_id:
                    self.current_visitor_gql_token = visitor_gql_token
                    self.current_visitor_id = visitor_id
                    self.current_auth_token = visitor_gql_token  # Often the same
                    
                    print("✅ Quick token refresh successful")
                    return True
            
            return False
            
        except Exception as e:
            print(f"⚡ Quick refresh failed: {e}")
            return False

    def _rotate_fallback_tokens(self):
        """Rotate through different fallback token sets"""
        print("🔄 Rotating fallback tokens...")
        
        # You can add multiple sets of fallback tokens here
        fallback_token_sets = [
            {
                "visitor_gql_token": "oauth2v2_c283b8178b24567f7e9880f4df857ac0",
                "visitor_id": "39.45.32.89.1758018771960000",
                "auth_token": "oauth2v2_52409f88c9b777a931f281db25988889"
            },
            # Add more fallback sets if you have them
        ]
        
        for i, token_set in enumerate(fallback_token_sets):
            print(f"🔄 Trying fallback token set {i + 1}")
            self.current_visitor_gql_token = token_set["visitor_gql_token"]
            self.current_visitor_id = token_set["visitor_id"]
            self.current_auth_token = token_set["auth_token"]
            
            # You could test the tokens here with a simple request
            # For now, just return True to try them
            return True
        
        print("❌ No more fallback tokens available")
        return False

    def _get_current_cookies(self):
        """Get current cookies with latest tokens"""
        cookies = self.fallback_cookies.copy()
        
        if self.current_visitor_gql_token:
            cookies['visitor_gql_token'] = self.current_visitor_gql_token
        if self.current_visitor_id:
            cookies['visitor_id'] = self.current_visitor_id
            
        return cookies

    def _get_current_headers(self):
        """Get current headers with latest tokens"""
        headers = self.base_headers.copy()
        
        if self.current_visitor_id:
            headers['x-visitor-id'] = self.current_visitor_id
        if self.current_auth_token:
            headers['Authorization'] = f'Bearer {self.current_auth_token}'
            
        return headers

    def fetch_jobs(self, query="developer", limit=10, delay=True):
        """
        Fetch jobs with automatic token refresh on auth failure using visitor job search API
        """
        print(f"🔍 Method 1: Trying visitorJobSearch with query: '{query}'")
        
        # New GraphQL query for visitor job search
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

        # The 'q' field is not supported in VisitorJobSearchV1Request anymore
        # If Upwork adds a new way to filter by query, update here

        if delay:
            time.sleep(random.uniform(2, 4))

        jobs_data = self._make_graphql_request(graphql_payload, "Method 1")
        
        if jobs_data:
            return jobs_data
        
        # If first method fails due to auth, try refreshing tokens once more
        if not jobs_data:
            print("🔄 First attempt failed, checking if it was due to auth error...")
            # The auth check and refresh is now handled inside _make_graphql_request
            
        # Method 2: Try with minimal parameters
        print(f"🔍 Method 2: Trying minimal visitorJobSearch")
        return self._try_method_2_visitor_search(query, limit, delay)

    def _make_graphql_request(self, payload, method_name):
        """
        Make the actual GraphQL request with automatic token refresh on auth failure
        """
        max_retries = 2
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.scraper.post(
                    self.GRAPHQL_URL,
                    headers=self._get_current_headers(),
                    cookies=self._get_current_cookies(),
                    data=json.dumps(payload),
                    timeout=30
                )

                print(f"📊 {method_name} Response Status: {response.status_code}")
                
                # If we get auth errors, try refreshing tokens
                if response.status_code in [401, 403]:
                    print(f"🔑 {method_name} Authentication error detected, refreshing tokens...")
                    
                    if retry_count < max_retries - 1:  # Don't refresh on last retry
                        success = self._refresh_tokens()
                        if success:
                            retry_count += 1
                            print(f"🔄 Retrying request with fresh tokens (attempt {retry_count + 1})")
                            continue
                        else:
                            print("❌ Token refresh failed, using current tokens")
                            break
                    else:
                        print("❌ Max retries reached, request failed")
                        break
                
                if response.status_code != 200:
                    print(f"❌ {method_name} API request failed: {response.status_code}")
                    print(f"Response text: {response.text[:500]}")
                    return []

                try:
                    data = response.json()
                    print(f"✅ {method_name} JSON parsed successfully")
                    
                    # Check for GraphQL errors
                    if "errors" in data:
                        print(f"❌ {method_name} GraphQL errors found:")
                        auth_error_found = False
                        
                        for error in data["errors"]:
                            error_msg = error.get('message', 'Unknown error')
                            print(f"   - {error_msg}")
                            
                            # Check for OAuth/permission errors in GraphQL response
                            if any(keyword in error_msg.lower() for keyword in ["permission", "oauth", "unauthorized", "forbidden"]):
                                auth_error_found = True
                                print(f"🔑 GraphQL permission issue detected")
                        
                        # If auth error in GraphQL and we haven't retried yet, try refresh
                        if auth_error_found and retry_count < max_retries - 1:
                            print("🔄 Attempting token refresh due to GraphQL auth error...")
                            success = self._refresh_tokens()
                            if success:
                                retry_count += 1
                                print(f"🔄 Retrying request with fresh tokens (attempt {retry_count + 1})")
                                continue
                        
                        # Don't return empty if we have partial data
                        if "data" in data and data["data"]:
                            print(f"⚠️ {method_name} Has errors but also has data, attempting to parse...")
                        else:
                            return []

                    # Extract jobs from response
                    jobs_data = self._extract_jobs_from_response(data, method_name)
                    
                    if jobs_data:
                        # Save to database
                        self._save_jobs_to_db(jobs_data)
                        print(f"✅ {method_name} Successfully fetched {len(jobs_data)} jobs from Upwork GraphQL.")
                        return jobs_data
                    else:
                        print(f"⚠️ {method_name} No jobs found in response")
                    
                    return jobs_data
                    
                except json.JSONDecodeError as e:
                    print(f"❌ {method_name} Failed to parse JSON: {e}")
                    print(f"Response text: {response.text[:500]}")
                    return []
                
            except Exception as e:
                print(f"❌ {method_name} Request failed: {e}")
                return []
        
        return []

    def _try_method_2_visitor_search(self, query, limit, delay):
        """Method 2: Try minimal visitor search without query"""
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
        
        print(f"🧪 Testing minimal visitor search...")
        jobs_data = self._make_graphql_request(graphql_payload_minimal, "Method 2 Minimal")
        
        if jobs_data:
            return jobs_data
        
        # Method 3: Try absolute minimal query
        print(f"🔍 Method 3: Trying ultra minimal visitor search")
        return self._try_method_3_visitor_search(limit, delay)

    def _try_method_3_visitor_search(self, limit, delay):
        """Method 3: Try ultra minimal visitor search"""
        graphql_payload = {
            "query": """
            query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {
                search {
                    universalSearchNuxt {
                        visitorJobSearchV1(request: $requestVariables) {
                            results {
                                id
                                title
                            }
                        }
                    }
                }
            }
            """,
            "variables": {
                "requestVariables": {
                    "paging": {
                        "offset": 0,
                        "count": limit
                    }
                }
            }
        }

        if delay:
            time.sleep(random.uniform(2, 4))

        jobs_data = self._make_graphql_request(graphql_payload, "Method 3 Ultra Minimal")
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
                        print(f"✅ {method_name} Found jobs at path: {' -> '.join(path)}")
                        break
                except (KeyError, TypeError):
                    continue
            
            if not results:
                print(f"⚠️ {method_name} No results found in response")
                print(f"Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                return []

            print(f"📊 {method_name} Found {len(results)} job results")

            for i, job_result in enumerate(results):
                try:
                    if not job_result:
                        print(f"⚠️ {method_name} Empty job result at index {i}")
                        continue
                    
                    # Debug: Print the actual job structure for first job
                    if i == 0:
                        print(f"🔍 {method_name} First job result structure:")
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
                        print(f"⚠️ Budget parsing error: {e}")
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
                    print(f"⚠️ {method_name} Error parsing job at index {i}: {e}")
                    continue

        except Exception as e:
            print(f"❌ {method_name} Error extracting jobs: {e}")
        
        return jobs_data

    def _safe_get_nested(self, data, path):
        """Safely get nested dictionary values"""
        try:
            current = data
            for key in path:
                current = current[key]
            return current
        except (KeyError, TypeError, AttributeError):
            return None

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
                            print(f"⚠️ Job model doesn't have 'description' field. Available fields: {column_names}")
                            
                    except Exception as e:
                        print(f"⚠️ Could not check Job model fields: {e}")
                    
                    db_job = Job(**job_fields)
                    session.merge(db_job)
                    saved_count += 1
                    
                except Exception as e:
                    print(f"⚠️ Error saving job to DB: {e}")
                    print(f"Job data: {job.get('id', 'Unknown')} - {job.get('title', 'No title')}")
                    print(f"Available Job model fields: {list(Job.__table__.columns.keys())}")
                    continue
            
            session.commit()
            session.close()
            print(f"💾 Saved {saved_count} jobs to database")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            print(f"Job model columns: {list(Job.__table__.columns.keys()) if hasattr(Job, '__table__') else 'Unknown'}")
            if 'session' in locals():
                session.rollback()
                session.close()

    def get_token_status(self):
        """Get current token status for debugging"""
        return {
            "current_visitor_id": self.current_visitor_id[:20] + "..." if self.current_visitor_id else None,
            "current_auth_token": self.current_auth_token[:20] + "..." if self.current_auth_token else None,
            "current_visitor_gql_token": self.current_visitor_gql_token[:20] + "..." if self.current_visitor_gql_token else None,
        }