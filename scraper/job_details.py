# scraper/job_details.py
"""
Handles job details fetching and parsing for UpworkScraper.
"""


import json
import os
import time
import random
import re

def fetch_job_details(scraper, job_id):
    print(f"Fetching detailed information for job ID: {job_id}")
    clean_job_id = str(job_id).lstrip("~")
    formatted_job_id = f"~{clean_job_id}"
    print(f"Using formatted job ID for API: {formatted_job_id}")

    # Use job_details_headers.json and job_details_cookies.json if they exist, else fallback to headers_upwork.json and upwork_cookies.json
    headers_file = os.path.join(os.path.dirname(__file__), '../job_details_headers.json')
    cookies_file = os.path.join(os.path.dirname(__file__), '../job_details_cookies.json')
    if not os.path.exists(headers_file):
        headers_file = os.path.join(os.path.dirname(__file__), '../headers_upwork.json')
    if not os.path.exists(cookies_file):
        cookies_file = os.path.join(os.path.dirname(__file__), '../upwork_cookies.json')

    # Load headers
    if not os.path.exists(headers_file):
        raise FileNotFoundError(f"Headers file not found: {headers_file}")
    with open(headers_file, "r") as f:
        headers = json.load(f)
        print("[✓] Loaded job details headers from file.")

    # Load cookies
    if not os.path.exists(cookies_file):
        print(f"[!] Cookies file not found: {cookies_file}. Using no cookies.")
        cookies = {}
    else:
        try:
            with open(cookies_file, "r") as f:
                cookies = json.load(f)
                print("[✓] Loaded job details cookies from file.")
                # Ensure all cookie values are strings
                cookies = {k: str(v) for k, v in cookies.items()}
        except (json.JSONDecodeError, Exception) as e:
            print(f"[!] Error loading cookies: {e}. Using no cookies.")
            cookies = {}

    # Build the payload (minimal public query)
    payload = get_simplified_job_details_query(formatted_job_id)

    # Make the request (use cloudscraper if available, else requests)
    try:
        import cloudscraper
        session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    except ImportError:
        import requests
        session = requests.Session()

    url = "https://www.upwork.com/api/graphql/v1?alias=gql-query-get-visitor-job-details"
    print(f"Making job details API request to: {url}")
    resp = session.post(
        url,
        headers=headers,
        cookies=cookies,
        json=payload
    )
    print(f"Job Details Response Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Job details API request failed: {resp.status_code}")
        print(f"Response text: {resp.text[:500]}")
        return {
            "id": job_id,
            "title": "Job details temporarily unavailable",
            "description": "Unable to fetch complete job details. The API may require authentication or the job may no longer be available.",
            "budget": "Not available",
            "status": "Unknown",
            "posted_on": "Unknown"
        }
    try:
        data = resp.json()
        print(f"Job details JSON parsed successfully")
        if "errors" in data:
            print(f"GraphQL errors in job details:")
            for error in data["errors"]:
                error_msg = error.get('message', 'Unknown error')
                print(f"   - {error_msg}")
            if "data" not in data or not data["data"]:
                return {
                    "id": job_id,
                    "title": "No title",
                    "description": "No description available",
                    "budget": "Not specified",
                    "currency_code": "USD",
                    "total_applicants": 0,
                    "total_hired": 0,
                    "skills": [],
                    "posted_on": "Unknown",
                    "category": ""
                }
        job_details = extract_job_details_from_response(data)
        if job_details:
            print(f"Successfully fetched detailed job information")
            return job_details
        else:
            print(f"No job details found in response")
        return job_details
    except Exception as e:
        print(f"Failed to parse job details JSON: {e}")
        print(f"Response text: {resp.text[:500]}")
        return {
            "id": job_id,
            "title": "No title",
            "description": f"No details available. Error: {e}",
            "budget": "Not specified",
            "currency_code": "USD",
            "total_applicants": 0,
            "total_hired": 0,
            "skills": [],
            "posted_on": "Unknown",
            "category": ""
        }

def get_simplified_job_details_query(job_id):
    return {
        "alias": "gql-query-get-visitor-job-details",
        "query": """query JobPubDetailsQuery($id: ID!) {\n                jobPubDetails(id: $id) {\n                    opening {\n                        status\n                        postedOn\n                        publishTime\n                        workload\n                        contractorTier\n                        description\n                        info {\n                            ciphertext\n                            id\n                            type\n                            title\n                            createdOn\n                            premium\n                        }\n                        sandsData {\n                            ontologySkills {\n                                id\n                                prefLabel\n                            }\n                            additionalSkills {\n                                id\n                                prefLabel\n                            }\n                        }\n                        category {\n                            name\n                        }\n                        categoryGroup {\n                            name\n                        }\n                        budget {\n                            amount\n                            currencyCode\n                        }\n                        engagementDuration {\n                            label\n                            weeks\n                        }\n                        extendedBudgetInfo {\n                            hourlyBudgetMin\n                            hourlyBudgetMax\n                            hourlyBudgetType\n                        }\n                        clientActivity {\n                            totalApplicants\n                            totalHired\n                            totalInvitedToInterview\n                            numberOfPositionsToHire\n                        }\n                        tools {\n                            name\n                        }\n                    }\n                    buyer {\n                        location {\n                            city\n                            country\n                            countryTimezone\n                        }\n                        stats {\n                            totalAssignments\n                            feedbackCount\n                            score\n                            totalJobsWithHires\n                            totalCharges {\n                                amount\n                                currencyCode\n                            }\n                            hoursCount\n                        }\n                        jobs {\n                            openCount\n                        }\n                    }\n                    qualifications {\n                        minJobSuccessScore\n                        minOdeskHours\n                        prefEnglishSkill\n                        risingTalent\n                        shouldHavePortfolio\n                    }\n                    buyerExtra {\n                        isPaymentMethodVerified\n                    }\n                }\n            }""",
        "variables": {
            "id": job_id
        }
    }

def fallback_job_details(scraper, job_id):
    print("Trying fallback job details method...")
    clean_job_id = str(job_id).lstrip("~")
    id_formats = [
        f"~{clean_job_id}",
        clean_job_id,
        f"~0{clean_job_id}",
    ]
    for id_format in id_formats:
        print(f"Trying ID format: {id_format}")
        detailed_query = get_simplified_job_details_query(id_format)
        try:
            response = scraper.scraper.post(
                "https://www.upwork.com/api/graphql/v1",
                headers=scraper._get_current_headers(),
                cookies=scraper._get_current_cookies(),
                json=detailed_query,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                if "data" in data and data["data"]:
                    print("Fallback method successful!")
                    return parse_fallback_response(data["data"])
        except Exception as e:
            print(f"Fallback attempt failed: {e}")
            continue
    return {
        "id": job_id,
        "title": "Job details temporarily unavailable",
        "description": "Unable to fetch complete job details. The API may require authentication or the job may no longer be available.",
        "budget": "Not available",
        "status": "Unknown",
        "posted_on": "Unknown"
    }

def parse_fallback_response(data):
    jobs = data.get("visitorJobSearch", {}).get("jobs", [])
    if not jobs:
        return {
            "id": "",
            "title": "No title",
            "description": "No description available",
            "budget": "Not specified",
            "currency_code": "USD",
            "total_applicants": 0,
            "total_hired": 0,
            "skills": [],
            "posted_on": "Unknown",
            "category": ""
        }
    job = jobs[0]
    return {
        "id": job.get("id", ""),
        "title": job.get("title", "No title"),
        "description": job.get("description", "No description available"),
        "budget": job.get("budget", {}).get("amount", "Not specified"),
        "currency_code": job.get("budget", {}).get("currencyCode", "USD"),
        "total_applicants": job.get("clientActivity", {}).get("totalApplicants", 0),
        "total_hired": job.get("clientActivity", {}).get("totalHired", 0),
        "skills": [s.get("name", "") for s in job.get("skills", [])],
        "posted_on": job.get("createdOn", "Unknown"),
        "category": job.get("category", {}).get("name", "")
    }

def make_job_details_request(scraper, payload, job_id, headers=None, cookies=None):
    """
    Make a job details request using fresh headers and cookies. If headers/cookies are not provided, generate them.
    """
    scraper.last_gql_errors = None
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Always use fresh session IDs and headers/cookies if not provided
            if headers is None:
                scraper._generate_session_ids()
                headers = scraper._get_current_headers()
            if cookies is None:
                cookies = scraper._get_current_cookies()
            headers = headers.copy()
            headers['Referer'] = f"https://www.upwork.com/nx/search/jobs/details/{job_id}?nbs=1&q=developer&pageTitle=Job%20Details&_modalInfo=%5B%7B%22navType%22%3A%22slider%22,%22title%22%3A%22Job%20Details%22,%22modalId%22%3A%221758699386529%22%7D%5D"
            print(f"Making job details API request to: {scraper.JOB_DETAILS_URL}")
            print(f"Payload: {json.dumps(payload, indent=2)[:500]}...")
            response = scraper.scraper.post(
                scraper.JOB_DETAILS_URL,
                headers=headers,
                cookies=cookies,
                json=payload,
            )
            print(f"Job Details Response Status: {response.status_code}")
            if response.status_code in [401, 403]:
                print(f"Authentication error detected, refreshing tokens...")
                if retry_count < max_retries - 1:
                    success = scraper._refresh_tokens()
                    if success:
                        retry_count += 1
                        print(f"Retrying job details request (attempt {retry_count + 1})")
                        time.sleep(random.uniform(3, 6))
                        # Always use fresh headers/cookies after refresh
                        headers = scraper._get_current_headers()
                        cookies = scraper._get_current_cookies()
                        continue
                    else:
                        print("Token refresh failed")
                        break
                else:
                    print("Max retries reached for job details")
                    break
            if response.status_code != 200:
                print(f"Job details API request failed: {response.status_code}")
                print(f"Response text: {response.text[:500]}")
                return None
            try:
                data = response.json()
                print(f"Job details JSON parsed successfully")
                if "errors" in data:
                    print(f"GraphQL errors in job details:")
                    for error in data["errors"]:
                        scraper.last_gql_errors = data["errors"]
                        error_msg = error.get('message', 'Unknown error')
                        print(f"   - {error_msg}")
                    if "data" not in data or not data["data"]:
                        return None
                job_details = extract_job_details_from_response(data)
                if job_details:
                    print(f"Successfully fetched detailed job information")
                    return job_details
                else:
                    print(f"No job details found in response")
                return job_details
            except json.JSONDecodeError as e:
                print(f"Failed to parse job details JSON: {e}")
                print(f"Response text: {response.text[:500]}")
                return None
        except Exception as e:
            print(f"Job details request failed: {e}")
            time.sleep(random.uniform(2, 5))
            return None
    return None

def extract_job_details_from_response(data):
    from datetime import datetime
    try:
        job_pub_details = data.get("data", {}).get("jobPubDetails", {})
        if not job_pub_details:
            print("No usable jobPubDetails found in response. Raw data:")
            print(json.dumps(data, indent=2)[:2000])
            return {
                "id": data.get("data", {}).get("id") or data.get("id", ""),
                "title": data.get("data", {}).get("title") or data.get("title", "No title"),
                "description": "No details available. (Some fields require authentication.)"
            }
        
        opening = job_pub_details.get("opening", {})
        buyer = job_pub_details.get("buyer", {})
        qualifications = job_pub_details.get("qualifications", {})
        buyer_extra = job_pub_details.get("buyerExtra", {})
        similar_jobs = job_pub_details.get("similarJobs", [])
        info = opening.get("info", {})
        extended_budget = opening.get("extendedBudgetInfo", {})
        client_activity = opening.get("clientActivity", {})
        category = opening.get("category", {})
        category_group = opening.get("categoryGroup", {})
        budget_info = opening.get("budget", {})
        engagement_duration = opening.get("engagementDuration", {})
        sands_data = opening.get("sandsData", {})
        buyer_location = buyer.get("location", {})
        buyer_stats = buyer.get("stats", {})
        buyer_company = buyer.get("company", {})
        buyer_jobs = buyer.get("jobs", {})
        
        # FIX: Improved handling of total_charges
        total_charges = buyer_stats.get("totalCharges", {})
        print(f"DEBUG: buyer_stats = {buyer_stats}")
        print(f"DEBUG: total_charges = {total_charges}")
        
        client_total_spent_value = None
        if total_charges and isinstance(total_charges, dict):
            client_total_spent_value = total_charges.get("amount")
            print(f"DEBUG: client_total_spent_value from totalCharges.amount = {client_total_spent_value}")
        
        # Alternative: Sometimes the total spending might be in a different field
        if client_total_spent_value is None:
            # Try alternative field paths
            alternative_paths = [
                buyer_stats.get("totalSpent"),
                buyer_stats.get("totalPayments"),
                buyer.get("totalSpent"),
                buyer.get("totalCharges", {}).get("amount") if isinstance(buyer.get("totalCharges"), dict) else None
            ]
            for alt_value in alternative_paths:
                if alt_value is not None:
                    client_total_spent_value = alt_value
                    print(f"DEBUG: Found alternative client_total_spent_value = {alt_value}")
                    break
        
        skills = []
        # Safely handle None for additionalSkills and ontologySkills
        additional_skills = sands_data.get("additionalSkills") or []
        for skill in additional_skills:
            if skill and skill.get("prefLabel"):
                skills.append(skill["prefLabel"])
        ontology_skills = sands_data.get("ontologySkills") or []
        for skill in ontology_skills:
            if skill and skill.get("prefLabel"):
                skills.append(skill["prefLabel"])
        
        budget_display = "Not specified"
        hourly_min = extended_budget.get("hourlyBudgetMin")
        hourly_max = extended_budget.get("hourlyBudgetMax")
        budget_amount = budget_info.get("amount")
        try:
            if budget_amount and float(budget_amount) > 0:
                budget_display = f"${budget_amount:,.0f}"
            elif hourly_min and float(hourly_min) > 0:
                if hourly_max and float(hourly_max) > 0:
                    budget_display = f"${hourly_min}-${hourly_max}/hr"
                else:
                    budget_display = f"${hourly_min}+/hr"
        except Exception:
            pass
        
        client_location_str = "Not specified"
        if buyer_location.get("city") and buyer_location.get("country"):
            client_location_str = f"{buyer_location['city']}, {buyer_location['country']}"
        elif buyer_location.get("country"):
            client_location_str = buyer_location['country']
        
        posted_on = opening.get("postedOn", "")
        if posted_on:
            try:
                posted_date = datetime.fromisoformat(posted_on.replace('Z', '+00:00'))
                posted_time = posted_date.strftime("%Y-%m-%d %H:%M UTC")
            except:
                posted_time = posted_on
        else:
            posted_time = "Unknown"
        
        job_details = {
            "id": info.get("id"),
            "ciphertext": info.get("ciphertext"),
            "title": info.get("title"),
            "description": opening.get("description"),
            "status": opening.get("status"),
            "posted_on": posted_time,
            "publish_time": opening.get("publishTime"),
            "workload": opening.get("workload"),
            "contractor_tier": opening.get("contractorTier"),
            "job_type": info.get("type"),
            "budget": budget_display,
            "budget_amount": budget_amount,
            "hourly_budget_min": hourly_min,
            "hourly_budget_max": hourly_max,
            "budget_type": extended_budget.get("hourlyBudgetType"),
            "currency_code": budget_info.get("currencyCode"),
            "engagement_duration": engagement_duration.get("label"),
            "engagement_weeks": engagement_duration.get("weeks"),
            "deliverables": opening.get("deliverables"),
            "deadline": opening.get("deadline"),
            "category": category.get("name"),
            "category_group": category_group.get("name"),
            "skills": skills,
            "total_applicants": client_activity.get("totalApplicants"),
            "total_hired": client_activity.get("totalHired"),
            "total_interviewed": client_activity.get("totalInvitedToInterview"),
            "positions_to_hire": client_activity.get("numberOfPositionsToHire"),
            "client_location": client_location_str,
            "client_country": buyer_location.get("country"),
            "client_timezone": buyer_location.get("countryTimezone"),
            "client_total_assignments": buyer_stats.get("totalAssignments"),
            "client_active_assignments": buyer_stats.get("activeAssignmentsCount"),
            "client_hours": buyer_stats.get("hoursCount"),
            "client_feedback_count": buyer_stats.get("feedbackCount"),
            "client_rating": buyer_stats.get("score"),
            "client_total_jobs": buyer_stats.get("totalJobsWithHires"),
            "client_total_spent": client_total_spent_value,  # FIX: Use the properly extracted value
            "client_open_jobs": buyer_jobs.get("openCount"),
            "client_industry": buyer_company.get("profile", {}).get("industry") if buyer_company.get("profile") else None,
            "client_company_size": buyer_company.get("profile", {}).get("size") if buyer_company.get("profile") else None,
            "payment_verified": buyer_extra.get("isPaymentMethodVerified"),
            "min_job_success_score": qualifications.get("minJobSuccessScore"),
            "min_hours": qualifications.get("minOdeskHours"),
            "min_hours_week": qualifications.get("minHoursWeek"),
            "english_requirement": qualifications.get("prefEnglishSkill"),
            "rising_talent": qualifications.get("risingTalent"),
            "portfolio_required": qualifications.get("shouldHavePortfolio"),
            "tools": [tool.get("name", "") for tool in opening.get("tools", [])],
            "similar_jobs_count": len(similar_jobs) if similar_jobs else None,
            "annotations": opening.get("annotations"),
            "segmentation_data": opening.get("segmentationData"),
            "qualifications": qualifications,
            "similar_jobs": similar_jobs[:5] if similar_jobs else []
        }
        
        print(f"DEBUG: Final client_total_spent in job_details = {job_details['client_total_spent']}")
        return job_details
        
    except Exception as e:
        print(f"Error extracting job details: {e}")
        print("Raw data for debugging:")
        print(json.dumps(data, indent=2)[:2000])
        return {
            "id": data.get("data", {}).get("id") or data.get("id", ""),
            "title": data.get("data", {}).get("title") or data.get("title", "No title"),
            "description": f"No details available. Error: {e} (Some fields require authentication.)"
        }