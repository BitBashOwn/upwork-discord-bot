# --- ADVANCED JOB SEARCH RUNNER ---
import asyncio
import os
def is_job_very_recent(created_datetime, max_minutes=5):
    """Check if a job was posted within the last 60 seconds"""
    from datetime import datetime, timezone
    
    if not created_datetime or created_datetime == 'Unknown':
        return False

    now = datetime.now(timezone.utc)
    dt = None
    try:
        # If it's a datetime object
        if hasattr(created_datetime, 'strftime'):
            dt = created_datetime
            if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        # If it's a timestamp (int or float)
        elif isinstance(created_datetime, (int, float)):
            dt = datetime.utcfromtimestamp(created_datetime).replace(tzinfo=timezone.utc)
        # If it's a string
        elif isinstance(created_datetime, str):
            # Try ISO format
            try:
                dt = datetime.fromisoformat(created_datetime.replace('Z', '+00:00'))
                if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
            if dt is None:
                # Try parsing as float timestamp string
                try:
                    ts = float(created_datetime)
                    dt = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
                except Exception:
                    return False
        if dt is None:
            return False
        # Calculate time difference in seconds
        diff = (now - dt).total_seconds()
        # Return True if job was posted within the last 60 seconds
        return diff <= 60
    except Exception as e:
        print(f"[Advanced Search] Error checking job recency: {e}")
        return False
async def fetch_and_build_job_message(job, search_context=""):
    """
    Fetch job details and build a complete message with all information.
    Returns the complete message string or None if auth fails.
    """
    job_id = job.get('id') or job.get('ciphertext')
    job_url = build_job_url(job_id)
    skills = job.get('skills', [])
    skill_display = " • ".join(skills[:8])
    if len(skills) > 8:
        skill_display += f" • +{len(skills) - 8} more"
    
    # Get formatted posting time for display
    posted_time = format_posted_time(job.get('createdDateTime'))
    
    # Build basic job message
    job_msg = (
        "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n"
        f"(V2)🚨 **{job['title']}** \n"
        f"{job['description'][:350] + '...' if len(job['description']) > 350 else job['description']}\n"
        f"\n"
        f"💰 **Budget:** {job.get('budget', 'N/A')}\n"
        f"⚡ **Posted**: {posted_time} \n"
        f"🕒 **Sent to Discord at:** {datetime.now().strftime('%H:%M')} UTC\n"
    )
    if skills:
        job_msg += f"🎯 **Key Skills:** `{skill_display}`\n"
    job_msg += (
        f"🌐 [Open Job]({job_url})\n"
        f"📊 **Found by keyword:** `{search_context}` \n"
    )
    
    # FETCH JOB DETAILS (with auto auth refresh)
    job_details_response = None
    if job_id:
        try:
            print(f"[Pre-fetch] Fetching details for job ID: {job_id}")
            
            # This will auto-refresh auth on 401 errors
            job_details_response = await asyncio.wait_for(
                scraper.fetch_job_details(job_id),
                timeout=45
            )
            
            if job_details_response:
                # Check if response indicates auth failure
                if isinstance(job_details_response, dict):
                    title = job_details_response.get('title', '')
                    if 'Authentication Required' in title or 'authentication error' in title.lower():
                        print(f"[Pre-fetch] ⚠️ Job details fetch failed due to auth - skipping this job")
                        return None  # Signal to skip this job
                
                print(f"[Pre-fetch] ✅ Job details fetched successfully")
            else:
                print(f"[Pre-fetch] ⚠️ No job details returned")
                
        except asyncio.TimeoutError:
            print(f"[Pre-fetch] ⏰ Job details request timed out")
        except Exception as detail_error:
            print(f"[Pre-fetch] ❌ Error fetching job details: {detail_error}")
    
    # ADD DETAILED INFORMATION TO THE MESSAGE
    if job_details_response and isinstance(job_details_response, dict):
        job_msg += "\n\n**📋 DETAILED JOB INFORMATION:**\n"
        
        # Project Details Section
        job_msg += "```"
        if job_details_response.get('job_type'):
            job_msg += f"\n💼 Job Type: {job_details_response['job_type']}"
        if job_details_response.get('engagement_duration'):
            job_msg += f"\n⏳ Duration: {job_details_response['engagement_duration']}"
        # if job_details_response.get('category'):
        #     job_msg += f"\n📂 Category: {job_details_response['category']}"
        job_msg += "\n```\n"
        
        # Client Information Section
        job_msg += "**👤 CLIENT INFORMATION:**\n```"
        if job_details_response.get('client_location'):
            job_msg += f"\n📍 Location: {job_details_response['client_location']}"
        
        # Handle client_total_spent properly
        client_total_spent = job_details_response.get('client_total_spent')
        if client_total_spent is not None and client_total_spent != "":
            try:
                spent_amount = float(client_total_spent)
                if spent_amount > 0:
                    spent_display = f"${spent_amount:,.0f}"
                else:
                    spent_display = "$0"
            except (ValueError, TypeError):
                spent_display = str(client_total_spent)
        else:
            spent_display = "Not disclosed"
        job_msg += f"\n💸 Total Spent: {spent_display}"
        
        payment_verified = job_details_response.get('payment_verified', False)
        job_msg += f"\n{'✅' if payment_verified else '❌'} Payment Verified: {'Yes' if payment_verified else 'No'}"
        job_msg += "\n```"
    
    return job_msg


async def process_single_search(search):
    """Process a single job search independently and asynchronously"""
    try:
        channel = bot.get_channel(search["channel_id"])
        if channel is None:
            print(f"[Advanced Search] Channel not found for {search['category']} - {search['keyword']} (ID: {search['channel_id']})")
            return
        
        print(f"[Advanced Search] Searching for: {search['keyword']} in category: {search['category']}")
        
        # Fetch jobs for this specific keyword
        jobs = await scraper.fetch_jobs(query=search["query"], limit=10, delay=True)
        
        if not jobs:
            print(f"[Advanced Search] No jobs found for keyword: {search['keyword']}")
            return

        # Filter for very recent jobs (posted within last 60 seconds)
        recent_jobs = []
        for job in jobs:
            if is_job_very_recent(job.get('createdDateTime'), max_minutes=5):
                recent_jobs.append(job)
        
        if not recent_jobs:
            print(f"[Advanced Search] No recent jobs (within 60 seconds) found for keyword: {search['keyword']}")
            return
        
        print(f"[Advanced Search] Found {len(recent_jobs)} recent jobs for keyword: {search['keyword']}")

        # FILTER FOR KEYWORD RELEVANCE
        keyword_lower = search['keyword'].lower()
        keyword_words = set(keyword_lower.replace('-', ' ').split())
        
        relevant_jobs = []
        for job in recent_jobs:
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            skills = [s.lower() for s in job.get('skills', [])]
            skills_text = ' '.join(skills)
            searchable_text = f"{title} {description} {skills_text}"
            
            if len(keyword_words) > 1:
                if all(word in searchable_text for word in keyword_words):
                    relevant_jobs.append(job)
                    print(f"[Filter] ✓ MATCH: '{job.get('title', 'No title')[:50]}...'")
                else:
                    print(f"[Filter] ✗ REJECT: '{job.get('title', 'No title')[:50]}...' - Missing keyword words")
            else:
                if keyword_lower in searchable_text:
                    relevant_jobs.append(job)
                    print(f"[Filter] ✓ MATCH: '{job.get('title', 'No title')[:50]}...'")
                else:
                    print(f"[Filter] ✗ REJECT: '{job.get('title', 'No title')[:50]}...' - Keyword not found")
        
        if not relevant_jobs:
            print(f"[Advanced Search] No relevant jobs found after keyword filtering for: {search['keyword']}")
            return
        
        print(f"[Advanced Search] {len(relevant_jobs)} jobs passed keyword filtering for: {search['keyword']}")

        # Filter only unique relevant jobs
        unique_jobs = []
        for job in relevant_jobs:
            job_id = job.get('id')
            if job_id and job_id not in sent_job_ids:
                unique_jobs.append(job)
                sent_job_ids.add(job_id)

        # Send up to 3 unique relevant jobs per keyword
        posted_count = 0
        for i, job in enumerate(unique_jobs[:3], 1):
            # Try to store job in database, skip if duplicate
            try:
                if hasattr(scraper, 'store_job_in_db'):
                    scraper.store_job_in_db(job)
            except Exception as db_exc:
                if 'duplicate' in str(db_exc).lower() or 'unique constraint' in str(db_exc).lower():
                    print(f"[Advanced Search] Skipping duplicate job ID: {job.get('id')}")
                    continue
                else:
                    print(f"[Advanced Search] DB error: {db_exc}")
                    continue

            # BUILD COMPLETE MESSAGE WITH ALL DETAILS
            complete_message = await fetch_and_build_job_message(job, f"{search['keyword']} in {search['category']}")
            
            # Skip if auth failed
            if complete_message is None:
                print(f"[Advanced Search] Skipping job due to auth failure")
                continue
            
            # POST COMPLETE MESSAGE TO DISCORD (single message with all info)
            try:
                await channel.send(complete_message)
                posted_count += 1
                print(f"[Post] ✅ Complete job message posted to Discord")
                await asyncio.sleep(2)  # avoid rate limits
            except Exception as post_error:
                print(f"[Post] ❌ Error posting message: {post_error}")
            
        if posted_count > 0:
            print(f"[Advanced Search] Posted {posted_count} complete job messages for keyword: {search['keyword']}")
        else:
            print(f"[Advanced Search] No jobs posted for keyword: {search['keyword']}")
            
    except Exception as e:
        error_msg = f"❌ Error searching recent jobs for **{search['keyword']}** in {search['category']}: {e}"
        try:
            channel = bot.get_channel(search["channel_id"])
            if channel:
                await channel.send(error_msg)
        except:
            pass
        print(f"[Advanced Search] Error in {search['keyword']}: {e}")
# async def post_job_with_auto_details(channel, job, msg_content, search_context=""):
#     """
#     IMPROVED: Fetch job details FIRST (with auto 401 refresh), 
#     then post job message with details included in the main message.
#     This ensures auth refresh happens BEFORE posting to Discord.
#     """
#     try:
#         # STEP 1: Fetch job details FIRST (before posting anything to Discord)
#         job_id = job.get('id') or job.get('ciphertext')
#         job_details_response = None
        
#         if job_id:
#             try:
#                 print(f"[Pre-fetch] Fetching details for job ID: {job_id} BEFORE posting to Discord")
                
#                 # This will auto-refresh auth on 401 errors
#                 job_details_response = await asyncio.wait_for(
#                     scraper.fetch_job_details(job_id),
#                     timeout=45  # Increased timeout to allow for auth refresh
#                 )
                
#                 if job_details_response:
#                     # Check if response indicates auth failure
#                     if isinstance(job_details_response, dict):
#                         title = job_details_response.get('title', '')
#                         if 'Authentication Required' in title or 'authentication error' in title.lower():
#                             print(f"[Pre-fetch] ⚠️ Job details fetch failed due to auth - skipping this job post")
#                             return  # Don't post job if auth failed
                    
#                     print(f"[Pre-fetch] ✅ Job details fetched successfully, now building enhanced message")
#                 else:
#                     print(f"[Pre-fetch] ⚠️ No job details returned, will post with basic info only")
                    
#             except asyncio.TimeoutError:
#                 print(f"[Pre-fetch] ⏰ Job details request timed out (may have included auth refresh)")
#                 # Continue with posting anyway
#             except Exception as detail_error:
#                 print(f"[Pre-fetch] ❌ Error pre-fetching job details: {detail_error}")
#                 # Continue with posting anyway
        
#         # STEP 2: Build enhanced message with job details included
#         enhanced_msg = msg_content
        
#         if job_details_response and isinstance(job_details_response, dict):
#             # Add detailed information to the main message
#             enhanced_msg += "\n\n**📋 DETAILED JOB INFORMATION:**\n"
            
#             # Project Details Section
#             enhanced_msg += "```"
#             if job_details_response.get('job_type'):
#                 enhanced_msg += f"\n💼 Job Type: {job_details_response['job_type']}"
#             if job_details_response.get('engagement_duration'):
#                 enhanced_msg += f"\n⏳ Duration: {job_details_response['engagement_duration']}"
#             if job_details_response.get('category'):
#                 enhanced_msg += f"\n📂 Category: {job_details_response['category']}"
#             enhanced_msg += "\n```\n"
            
#             # Client Information Section
#             enhanced_msg += "**👤 CLIENT INFORMATION:**\n```"
#             if job_details_response.get('client_location'):
#                 enhanced_msg += f"\n📍 Location: {job_details_response['client_location']}"
            
#             # Handle client_total_spent properly
#             client_total_spent = job_details_response.get('client_total_spent')
#             if client_total_spent is not None and client_total_spent != "":
#                 try:
#                     spent_amount = float(client_total_spent)
#                     if spent_amount > 0:
#                         spent_display = f"${spent_amount:,.0f}"
#                     else:
#                         spent_display = "$0"
#                 except (ValueError, TypeError):
#                     spent_display = str(client_total_spent)
#             else:
#                 spent_display = "Not disclosed"
#             enhanced_msg += f"\n💸 Total Spent: {spent_display}"
            
#             # if job_details_response.get('client_industry'):
#             #     enhanced_msg += f"\n🏢 Industry: {job_details_response['client_industry']}"
#             # if job_details_response.get('client_company_size'):
#             #     enhanced_msg += f"\n👥 Company Size: {job_details_response['client_company_size']}"
            
#             payment_verified = job_details_response.get('payment_verified', False)
#             enhanced_msg += f"\n{'✅' if payment_verified else '❌'} Payment Verified: {'Yes' if payment_verified else 'No'}"
#             enhanced_msg += "\n```\n"
            
#             # Requirements Section
#             # if (job_details_response.get('min_job_success_score') or 
#             #     job_details_response.get('min_hours') or 
#             #     job_details_response.get('english_requirement', 'ANY') != 'ANY' or
#             #     job_details_response.get('portfolio_required', False) or
#             #     job_details_response.get('rising_talent', False)):
                
#             #     enhanced_msg += "**📋 REQUIREMENTS:**\n```"
#             #     if job_details_response.get('min_job_success_score'):
#             #         enhanced_msg += f"\n⭐ Min Success Score: {job_details_response['min_job_success_score']}%"
#             #     if job_details_response.get('min_hours'):
#             #         enhanced_msg += f"\n🕐 Min Platform Hours: {job_details_response['min_hours']}"
#             #     if job_details_response.get('min_hours_week'):
#             #         enhanced_msg += f"\n📅 Min Hours/Week: {job_details_response['min_hours_week']}"
#             #     if job_details_response.get('portfolio_required', False):
#             #         enhanced_msg += f"\n📁 Portfolio Required: Yes"
#             #     if job_details_response.get('rising_talent', False):
#             #         enhanced_msg += f"\n🌟 Rising Talent: Welcome"
#             #     if job_details_response.get('english_requirement', 'ANY') != 'ANY':
#             #         enhanced_msg += f"\n🗣️ English: {job_details_response['english_requirement']}"
#             #     enhanced_msg += "\n```\n"
            
#             # Tools & Skills Section
#             # tools = job_details_response.get('tools', [])
#             # if tools:
#             #     tools_display = ' • '.join(tools[:15])
#             #     if len(tools) > 15:
#             #         tools_display += f" • +{len(tools) - 15} more"
#             #     enhanced_msg += f"**🛠️ TOOLS & PLATFORMS ({len(tools)} total):**\n`{tools_display}`\n\n"
            
#             # Additional Info
#             # if job_details_response.get('deliverables'):
#             #     deliverables = job_details_response['deliverables'][:200]
#             #     if len(job_details_response['deliverables']) > 200:
#             #         deliverables += "..."
#             #     enhanced_msg += f"**📦 DELIVERABLES:**\n{deliverables}\n\n"
            
#             # Competition Stats
#             # enhanced_msg += "**📊 COMPETITION STATS:**\n```"
#             # if job_details_response.get('total_applicants'):
#             #     enhanced_msg += f"\n📝 Proposals: {job_details_response['total_applicants']}"
#             # if job_details_response.get('total_interviewed'):
#             #     enhanced_msg += f"\n💬 Interviewing: {job_details_response['total_interviewed']}"
#             # if job_details_response.get('total_hired'):
#             #     enhanced_msg += f"\n✅ Hired: {job_details_response['total_hired']}"
#             # enhanced_msg += "\n```"
        
#         # STEP 3: Post the enhanced message to Discord
#         job_message = await channel.send(enhanced_msg)
#         print(f"[Post] ✅ Enhanced job message posted to Discord with detailed information")
            
#     except Exception as e:
#         print(f"[Post] ❌ Error posting job with auto details: {e}")
#         import traceback
#         traceback.print_exc()
#         # Don't post anything if there's an error to avoid partial posts

# # Insert this updated function into your Discord bot file, replacing the existing post_job_with_auto_details function
# # The rest of your Discord bot code remains the same

# async def process_single_search(search):
#     """Process a single job search independently and asynchronously"""
#     try:
#         channel = bot.get_channel(search["channel_id"])
#         if channel is None:
#             print(f"[Advanced Search] Channel not found for {search['category']} - {search['keyword']} (ID: {search['channel_id']})")
#             return
        
#         print(f"[Advanced Search] Searching for: {search['keyword']} in category: {search['category']}")
        
#         # Fetch jobs for this specific keyword
#         jobs = await scraper.fetch_jobs(query=search["query"], limit=10, delay=True)
        
#         if not jobs:
#             print(f"[Advanced Search] No jobs found for keyword: {search['keyword']}")
#             return

#         # Filter for very recent jobs (posted within last 60 seconds)
#         recent_jobs = []
#         for job in jobs:
#             if is_job_very_recent(job.get('createdDateTime'), max_minutes=5):
#                 recent_jobs.append(job)
        
#         # If no very recent jobs, skip this search
#         if not recent_jobs:
#             print(f"[Advanced Search] No recent jobs (within 60 seconds) found for keyword: {search['keyword']}")
#             return
        
#         print(f"[Advanced Search] Found {len(recent_jobs)} recent jobs for keyword: {search['keyword']}")

#         # ===== NEW: FILTER FOR KEYWORD RELEVANCE =====
#         keyword_lower = search['keyword'].lower()
        
#         # Extract individual words from keyword for better matching
#         keyword_words = set(keyword_lower.replace('-', ' ').split())
        
#         # Filter jobs that actually match the keyword
#         relevant_jobs = []
#         for job in recent_jobs:
#             title = job.get('title', '').lower()
#             description = job.get('description', '').lower()
#             skills = [s.lower() for s in job.get('skills', [])]
#             skills_text = ' '.join(skills)
            
#             # Combine all searchable text
#             searchable_text = f"{title} {description} {skills_text}"
            
#             # Check if keyword appears in searchable text
#             # For multi-word keywords, check if all words appear
#             if len(keyword_words) > 1:
#                 # All words must appear (allows for variations like "browser" and "fingerprint")
#                 if all(word in searchable_text for word in keyword_words):
#                     relevant_jobs.append(job)
#                     print(f"[Filter] ✓ MATCH: '{job.get('title', 'No title')[:50]}...'")
#                 else:
#                     print(f"[Filter] ✗ REJECT: '{job.get('title', 'No title')[:50]}...' - Missing keyword words")
#             else:
#                 # Single word keyword - direct match
#                 if keyword_lower in searchable_text:
#                     relevant_jobs.append(job)
#                     print(f"[Filter] ✓ MATCH: '{job.get('title', 'No title')[:50]}...'")
#                 else:
#                     print(f"[Filter] ✗ REJECT: '{job.get('title', 'No title')[:50]}...' - Keyword not found")
        
#         # If no relevant jobs after filtering, skip
#         if not relevant_jobs:
#             print(f"[Advanced Search] No relevant jobs found after keyword filtering for: {search['keyword']}")
#             return
        
#         print(f"[Advanced Search] {len(relevant_jobs)} jobs passed keyword filtering for: {search['keyword']}")
#         # ===== END KEYWORD FILTERING =====

#         # Filter only unique relevant jobs
#         unique_jobs = []
#         for job in relevant_jobs:
#             job_id = job.get('id')
#             if job_id and job_id not in sent_job_ids:
#                 unique_jobs.append(job)
#                 sent_job_ids.add(job_id)

#         # Send up to 3 unique relevant jobs per keyword
#         for i, job in enumerate(unique_jobs[:3], 1):
#             # Try to store job in database, skip if duplicate
#             try:
#                 if hasattr(scraper, 'store_job_in_db'):
#                     scraper.store_job_in_db(job)
#             except Exception as db_exc:
#                 if 'duplicate' in str(db_exc).lower() or 'unique constraint' in str(db_exc).lower():
#                     print(f"[Advanced Search] Skipping duplicate job ID: {job.get('id')}")
#                     continue
#                 else:
#                     print(f"[Advanced Search] DB error: {db_exc}")
#                     continue

#             job_url = build_job_url(job.get('id'))
#             skills = job.get('skills', [])
#             skill_display = " • ".join(skills[:8])
#             if len(skills) > 8:
#                 skill_display += f" • +{len(skills) - 8} more"
            
#             # Get formatted posting time for display
#             posted_time = format_posted_time(job.get('createdDateTime'))
            
#             job_msg = (
#                 "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n"
#                 f"(V2)🚨 **{job['title']}** \n"
#                 f"{job['description'][:350] + '...' if len(job['description']) > 350 else job['description']}\n"
#                 f"\n"
#                 f"💰 **Budget:** {job.get('budget', 'N/A')}\n"
#                 f"⚡ **Posted**: {posted_time} \n"
#                 f"🕒 **Sent to Discord at:** {datetime.now().strftime('%H:%M')} UTC\n"
#             )
#             if skills:
#                 job_msg += f"🎯 **Key Skills:** `{skill_display}`\n"
#             job_msg += (
#                 f"🌐 [Open Job]({job_url})\n"
#                 f"📊 **Found by keyword:** `{search['keyword']}` in **{search['category']}** \n"
#             )
            
#             # Post job with automatic details in thread
#             await post_job_with_auto_details(channel, job, job_msg, f"Advanced Search: {search['keyword']}")
#             await asyncio.sleep(2)  # avoid rate limits
            
#         if unique_jobs:
#             print(f"[Advanced Search] Posted {len(unique_jobs[:3])} relevant jobs for keyword: {search['keyword']}")
#         else:
#             print(f"[Advanced Search] No unique relevant jobs to post for keyword: {search['keyword']}")
            
#     except Exception as e:
#         error_msg = f"❌ Error searching recent jobs for **{search['keyword']}** in {search['category']}: {e}"
#         try:
#             channel = bot.get_channel(search["channel_id"])
#             if channel:
#                 await channel.send(error_msg)
#         except:
#             pass
#         print(f"[Advanced Search] Error in {search['keyword']}: {e}")

async def run_advanced_job_searches():
    """Run all job searches concurrently and independently"""
    await bot.wait_until_ready()
    print("[Advanced Search] Starting advanced job searches (ASYNC MODE)...")
    
    # Create a list of tasks for all searches
    search_tasks = []
    for search in ADVANCED_JOB_SEARCHES:
        # Create a task for each search
        task = asyncio.create_task(process_single_search(search))
        search_tasks.append(task)
    
    # Run all searches concurrently
    print(f"[Advanced Search] Running {len(search_tasks)} searches concurrently...")
    
    # Use gather with return_exceptions=True to prevent one failure from stopping others
    results = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    # Log any errors that occurred
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            search = ADVANCED_JOB_SEARCHES[i]
            print(f"[Advanced Search] Error in search '{search['keyword']}': {result}")
    
    print(f"[Advanced Search] Completed all {len(search_tasks)} concurrent searches")

import discord
from discord.ext import commands, tasks
from scraper.upwork_scraper import UpworkScraper
from scraper.bhw_scraper import post_new_bhw_threads
from config import DISCORD_TOKEN, DISCORD_CHANNEL_ID, UPWORK_EMAIL, UPWORK_PASSWORD,DISCORD_CHANNEL_ID2
import asyncio
import re

from datetime import datetime
import traceback

# --- ADVANCED JOB SEARCH KEYWORDS AND CHANNELS ---
# Map: (keyword_name, search_query, channel_id)
from .job_search_keywords import ADVANCED_JOB_SEARCHES

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
scraper = UpworkScraper()

# --- UNIQUE JOBS TRACKER ---
sent_job_ids = set()

# Store the last search time to prevent spam
last_search_time = {}
COOLDOWN_SECONDS = 30  # Prevent searches more than once every 30 seconds per user

def build_job_url(job_id):
    """Builds the correct Upwork job URL with modal info."""
    if not job_id:
        return None
    
    job_id = str(job_id)
    
    # FIXED: Remove any existing ~ prefix first, then add one
    clean_job_id = job_id.lstrip("~")
    
    # Don't add double ~ prefix
    return f"https://www.upwork.com/freelance-jobs/apply/~{clean_job_id}"

def build_job_details_embed(job_details):
    """Build a comprehensive detailed embed with horizontal layout matching Upwork job details"""
    if not job_details:
        return discord.Embed(
            title="❌ Job Details Unavailable",
            description="Unable to fetch detailed job information at this time.",
            color=0xe74c3c
        )
    
    # Create main title and description
    title = f"📋 {job_details.get('title', 'Job Details')}"
    description = job_details.get('description', 'No description available')[:40] + ("..." if len(job_details.get('description', '')) > 40 else "")
    
    # Build embed with each field as inline and a gap between fields
    embed = discord.Embed(
        title=title,
        description=description,
        color=0x2ecc71,
        url=build_job_url(job_details.get('ciphertext') or job_details.get('id'))
    )

    # Add job overview fields
    if job_details.get('budget'):
        embed.add_field(name="💰 Budget", value=job_details['budget'], inline=True)
    # if job_details.get('contractor_tier'):
    #     embed.add_field(name="📊 Contractor Tier", value=job_details['contractor_tier'], inline=True)
    if job_details.get('client_location', 'Unknown') != 'Unknown':
        embed.add_field(name="📍 Client Location", value=job_details['client_location'], inline=True)

    embed.add_field(name="", value="", inline=False)  # gap

    # Project details
    if job_details.get('job_type'):
        embed.add_field(name="💼 Job Type", value=job_details['job_type'], inline=True)
    if job_details.get('engagement_duration'):
        embed.add_field(name="⏳ Engagement Duration", value=job_details['engagement_duration'], inline=True)
    # if job_details.get('workload'):
    #     embed.add_field(name="⏱️ Workload", value=job_details['workload'], inline=True)
    # if job_details.get('deadline'):
    #     embed.add_field(name="📅 Deadline", value=job_details['deadline'], inline=True)

    embed.add_field(name="", value="", inline=False)

    # Activity on this job
    # embed.add_field(name="📝 Proposals", value=job_details.get('total_applicants', 0), inline=True)
    # embed.add_field(name="💬 Interviewing", value=job_details.get('total_interviewed', 0), inline=True)
    # embed.add_field(name="✅ Hired", value=job_details.get('total_hired', 0), inline=True)
    # embed.add_field(name="👤 Positions", value=job_details.get('positions_to_hire', 1), inline=True)

    embed.add_field(name="", value="", inline=False)

    # About the client
    # if job_details.get('client_country'):
    #     embed.add_field(name="🌍 Client Country", value=job_details['client_country'], inline=True)
    # if job_details.get('client_timezone'):
    #     embed.add_field(name="🕒 Client Timezone", value=job_details['client_timezone'], inline=True)
    
    # FIX: Properly handle client_total_spent with better formatting
    client_total_spent = job_details.get('client_total_spent')
    if client_total_spent is not None and client_total_spent != "":
        try:
            spent_amount = float(client_total_spent)
            if spent_amount > 0:
                spent_display = f"${spent_amount:,.0f}"
            else:
                spent_display = "$0"
        except (ValueError, TypeError):
            spent_display = str(client_total_spent)
    else:
        spent_display = "Not disclosed"
    
    embed.add_field(name="💸 Total Spent", value=spent_display, inline=True)
    
    # if job_details.get('client_hours'):
    #     embed.add_field(name="⏰ Client Hours", value=f"{job_details['client_hours']:,.0f}", inline=True)
    # if job_details.get('client_total_jobs'):
    #     embed.add_field(name="📋 Jobs Posted", value=job_details['client_total_jobs'], inline=True)
    # if job_details.get('client_rating'):
    #     rating = f"{job_details['client_rating']:.1f}/5"
    #     feedback_count = job_details.get('client_feedback_count')
    #     if feedback_count:
    #         rating += f" ({feedback_count} reviews)"
    #     embed.add_field(name="⭐ Client Rating", value=rating, inline=True)
    embed.add_field(name="✅ Payment Verified" if job_details.get('payment_verified', False) else "❌ Payment Verified", value="Yes" if job_details.get('payment_verified', False) else "No", inline=True)
    if job_details.get('client_industry'):
        embed.add_field(name="🏢 Industry", value=job_details['client_industry'], inline=True)
    if job_details.get('client_company_size'):
        embed.add_field(name="👥 Company Size", value=job_details['client_company_size'], inline=True)

    embed.add_field(name="", value="", inline=False)

    # Requirements
    if job_details.get('min_job_success_score'):
        embed.add_field(name="⭐ Min Success Score", value=f"{job_details['min_job_success_score']}%", inline=True)
    if job_details.get('min_hours'):
        embed.add_field(name="🕐 Min Platform Hours", value=job_details['min_hours'], inline=True)
    if job_details.get('min_hours_week'):
        embed.add_field(name="📅 Min Hours/Week", value=job_details['min_hours_week'], inline=True)
    if job_details.get('portfolio_required', False):
        embed.add_field(name="📁 Portfolio Required", value="Yes", inline=True)
    if job_details.get('rising_talent', False):
        embed.add_field(name="🌟 Rising Talent Welcome", value="Yes", inline=True)
    if job_details.get('english_requirement', 'ANY') != 'ANY':
        embed.add_field(name="🗣️ English", value=job_details['english_requirement'], inline=True)

    embed.add_field(name="", value="", inline=False)

    # Tools
    tools = job_details.get('tools', [])
    # if tools:
    #     tools_display = ' • '.join(tools[:15])
    #     if len(tools) > 15:
    #         tools_display += f" • +{len(tools) - 15} more"
    #     embed.add_field(name=f"🛠️ Tools ({len(tools)})", value=tools_display, inline=True)

    # Additional info
    additional_parts = []
    if job_details.get('deliverables'):
        deliverables = job_details['deliverables'][:100]
        if len(job_details['deliverables']) > 100:
            deliverables += "..."
        additional_parts.append(f"📦 {deliverables}")
    if job_details.get('category'):
        additional_parts.append(f"📂 {job_details['category']}")
    similar_jobs_count = job_details.get('similar_jobs_count')
    if similar_jobs_count:
        additional_parts.append(f"🔗 {similar_jobs_count} similar jobs available")
    # if additional_parts:
    #     embed.add_field(name="ℹ️ Additional Info", value='\n'.join(additional_parts), inline=True)

    # Enhanced footer with posting and status info
    footer_parts = []
    if job_details.get('posted_on'):
        footer_parts.append(f"📅 Posted: {format_posted_time(job_details['posted_on'])}")
    if job_details.get('status'):
        footer_parts.append(f"Status: {job_details['status']}")
    if job_details.get('publish_time'):
        footer_parts.append(f"Published: {format_posted_time(job_details['publish_time'])}")

    footer_text = " • ".join(footer_parts) if footer_parts else "Comprehensive Job Details"
    embed.set_footer(
        text=footer_text,
        icon_url="https://img.icons8.com/fluency/48/000000/upwork.png"
    )

    return embed

def format_posted_time(created_datetime):
    """Format the posting time as 'X mins ago', 'Y secs ago', etc."""
    import time
    from datetime import datetime, timezone
    if not created_datetime or created_datetime == 'Unknown':
        return "Unknown"

    now = datetime.now(timezone.utc)
    dt = None
    try:
        # If it's a datetime object
        if hasattr(created_datetime, 'strftime'):
            dt = created_datetime
            if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        # If it's a timestamp (int or float)
        elif isinstance(created_datetime, (int, float)):
            dt = datetime.utcfromtimestamp(created_datetime).replace(tzinfo=timezone.utc)
        # If it's a string
        elif isinstance(created_datetime, str):
            # Try ISO format
            try:
                dt = datetime.fromisoformat(created_datetime.replace('Z', '+00:00'))
                if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
            if dt is None:
                # Try parsing as float timestamp string
                try:
                    ts = float(created_datetime)
                    dt = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
                except Exception:
                    pass
        if dt is None:
            return str(created_datetime)[:10] if len(str(created_datetime)) > 10 else str(created_datetime)

        # Calculate time difference
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 0:
            seconds = 0
        if seconds < 60:
            return f"{seconds} sec{'s' if seconds != 1 else ''} ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        if days < 7:
            return f"{days} day{'s' if days != 1 else ''} ago"
        weeks = days // 7
        if weeks < 4:
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        months = days // 30
        if months < 12:
            return f"{months} month{'s' if months != 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    except Exception:
        return "Unknown"

# ADD DEBUG FUNCTION
def debug_job_ids(jobs_data):
    """Debug function to check job IDs"""
    print("\n=== JOB ID DEBUG ===")
    for i, job in enumerate(jobs_data[:3]):  # Check first 3 jobs
        job_id = job.get('id')
        print(f"Job {i+1}:")
        print(f"  ID: {job_id}")
        print(f"  Title: {job.get('title', 'No title')[:50]}...")
        print(f"  ID starts with ~: {str(job_id).startswith('~') if job_id else False}")
        print(f"  ID length: {len(str(job_id)) if job_id else 0}")
        
        # Test URL generation
        test_url = build_job_url(job_id)
        print(f"  Generated URL: {test_url}")
        print()
    print("===================\n")

@bot.event
async def on_ready():
    print(f"Bot is ready. Username: {bot.user}")
    bot.loop.create_task(run_scrapers_concurrently())

# @bot.event
# async def on_message(message):
#     # Don't respond to bot's own messages
#     if message.author == bot.user:
#         return
    
#     # Only respond in the designated channel
#     if message.channel.id != DISCORD_CHANNEL_ID:
#         return
    
#     # Don't respond to commands (let command handler deal with them)
#     if message.content.startswith(bot.command_prefix):
#         await bot.process_commands(message)
#         return
    
#     # Check cooldown
#     user_id = message.author.id
#     current_time = asyncio.get_event_loop().time()
    
#     if user_id in last_search_time:
#         if current_time - last_search_time[user_id] < COOLDOWN_SECONDS:
#             await message.add_reaction("⏰")  # Clock emoji to indicate cooldown
#             return
    
#     last_search_time[user_id] = current_time
    
#     # Extract keywords from the message
#     keyword = message.content.strip()
    
#     # Skip very short messages or common words
#     if len(keyword) < 2 or keyword.lower() in ['hi', 'hello', 'hey', 'ok', 'yes', 'no', 'thanks']:
#         return
    
#     # Add a loading reaction
#     await message.add_reaction("🔍")
    
#     try:
#         # Search for jobs using the keyword
#         print(f"🔍 Searching for jobs with keyword: '{keyword}'")
#         jobs = await scraper.fetch_jobs(query=keyword, limit=5)
        
#         if jobs:
#             print(f"✅ Found {len(jobs)} jobs for keyword: '{keyword}'")
            
#             # ADD: Debug job IDs
#             debug_job_ids(jobs)
            
#             # Create embed for search results with horizontal layout
#             main_embed = discord.Embed(
#                 title=f"🎯 Search Results: '{keyword}'",
#                 description=f"Found **{len(jobs)}** matching jobs",
#                 color=0x00ff00
#             )
#             main_embed.add_field(name="👤 Requested by", value=message.author.display_name, inline=True)
#             main_embed.add_field(name="📊 Results", value=f"Showing top {min(len(jobs), 3)}", inline=True)
#             main_embed.add_field(name="🕒 Search Time", value=datetime.now().strftime("%H:%M"), inline=True)
#             await message.channel.send(embed=main_embed)

#             # Send individual job embeds with improved horizontal layout (limit to first 3)
#             for i, job in enumerate(jobs[:3], 1):
#                 embed = discord.Embed(
#                     title=f"📋 {job['title']}",
#                     description=job['description'][:400] + "..." if len(job['description']) > 400 else job['description'],
#                     color=0x1abc9c,
#                     url=build_job_url(job.get('id'))
#                 )
                
#                 # ROW 1: Budget, Experience, Type (3 columns)
#                 embed.add_field(name="💰 Budget", value=job.get('budget', 'N/A'), inline=True)
#                 embed.add_field(name="📊 Experience", value=job.get('experience_level', 'Any'), inline=True)
#                 embed.add_field(name="💼 Type", value=job.get('job_type', 'N/A'), inline=True)
                
#                 # ROW 2: Duration, Posted, Apply (3 columns)
#                 embed.add_field(name="⏱️ Duration", value=job.get('duration_label', 'N/A'), inline=True)
#                 embed.add_field(name="🕒 Posted", value=format_posted_time(job.get('createdDateTime')), inline=True)
#                 embed.add_field(name="🌐 Quick Apply", value="[Open Job]("+build_job_url(job.get('id'))+")", inline=True)
                
#                 # Skills row (full width but compact)
#                 skills = job.get('skills', [])
#                 if skills:
#                     skill_display = " • ".join(skills[:10])
#                     if len(skills) > 10:
#                         skill_display += f" • +{len(skills) - 10} more"
#                     embed.add_field(
#                         name="🎯 Required Skills",
#                         value=f"`{skill_display}`",
#                         inline=False
#                     )
                
#                 embed.set_footer(
#                     text=f"Result {i} of {min(len(jobs), 3)} • Detailed info will be posted in thread automatically",
#                     icon_url="https://img.icons8.com/fluency/48/000000/upwork.png"
#                 )
                
#                 # Post job with automatic details in thread
#                 await post_job_with_auto_details(message.channel, job, embed=embed, search_context=f"User search: {keyword}")
#                 await asyncio.sleep(1)
            
#             # If there are more jobs, show summary
#             if len(jobs) > 3:
#                 overflow_embed = discord.Embed(
#                     title="📋 More Results Available",
#                     description=f"Found **{len(jobs) - 3}** additional jobs",
#                     color=0xf39c12
#                 )
#                 overflow_embed.add_field(name="💡 Tip", value=f"Use `!jobs {keyword}` to see all results", inline=True)
#                 overflow_embed.add_field(name="🔍 Refine", value="Try more specific keywords", inline=True)
#                 await message.channel.send(embed=overflow_embed)
            
#             # Remove the loading reaction and add success
#             await message.remove_reaction("🔍", bot.user)
#             await message.add_reaction("✅")
            
#         else:
#             # No jobs found with enhanced layout
#             embed = discord.Embed(
#                 title="😞 No Jobs Found",
#                 description=f"No jobs matching **'{keyword}'** found right now",
#                 color=0xe74c3c
#             )
#             embed.add_field(name="💡 Try These", value="• python\n• web developer\n• data analyst", inline=True)
#             embed.add_field(name="🔄 Or Try", value="• graphic design\n• content writing\n• social media", inline=True)
#             embed.add_field(name="⏰ Check Back", value="New jobs posted hourly!", inline=True)
#             await message.channel.send(embed=embed)
            
#             # Remove loading and add sad reaction
#             await message.remove_reaction("🔍", bot.user)
#             await message.add_reaction("😞")
    
#     except Exception as e:
#         print(f"❌ Error searching for jobs: {e}")
        
#         error_embed = discord.Embed(
#             title="⚠️ Search Error",
#             description="Something went wrong while searching for jobs.",
#             color=0xe74c3c
#         )
#         error_embed.add_field(name="🔧 Status", value="Temporary issue", inline=True)
#         error_embed.add_field(name="⏰ Retry", value="Try again in a moment", inline=True)
#         error_embed.add_field(name="💬 Help", value="Use `!help_jobs` for tips", inline=True)
#         await message.channel.send(embed=error_embed)
        
#         # Remove loading and add error reaction
#         await message.remove_reaction("🔍", bot.user)
#         await message.add_reaction("❌")
    
#     # Process commands after handling the message
#     await bot.process_commands(message)

# @bot.command()
# async def jobs(ctx, *, keyword=None):
#     """Command to search for jobs with enhanced horizontal layout"""
#     if not keyword:
#         msg = (
#             "🔍 **Job Search Command**\n"
#             "Search for Upwork jobs with detailed results\n\n"
#             "📝 **Usage:** `!jobs <keyword>`\n"
#             "💡 **Example:** `!jobs python developer`\n"
#             "📊 **Results:** Shows up to 10 jobs with auto-generated detail threads"
#         )
#         await ctx.send(msg)
#         return

#     # Add loading message
#     loading_msg = await ctx.send("🔍 Searching for jobs...")

#     try:
#         jobs = await scraper.fetch_jobs(query=keyword, limit=10)
#         # Filter jobs by keyword in title, description, or skills
#         keyword_lower = keyword.lower()
#         filtered_jobs = []
#         for job in jobs:
#             title = job.get('title', '').lower()
#             description = job.get('description', '').lower()
#             skills = [s.lower() for s in job.get('skills', [])]
#             if (
#                 keyword_lower in title
#                 or keyword_lower in description
#                 or any(keyword_lower in skill for skill in skills)
#             ):
#                 filtered_jobs.append(job)

#         if filtered_jobs:
#             # Delete loading message
#             await loading_msg.delete()

#             # Create main results message
#             main_msg = (
#                 f"🎯 **Search Results: '{keyword}'**\n"
#                 f"Found **{len(filtered_jobs)}** relevant jobs\n"
#                 f"👤 **Requested by:** {ctx.author.display_name}\n"
#                 f"📊 **Showing:** {min(len(filtered_jobs), 10)} jobs\n"
#                 f"🕒 **Search Time:** {datetime.now().strftime('%H:%M UTC')}\n"
#                 f"📋 **Note:** Detailed info will be automatically posted in threads for each job\n"
#             )
#             await ctx.send(main_msg)

#             # Send all filtered jobs found (up to 10) with auto details
#             for i, job in enumerate(filtered_jobs, 1):
#                 job_url = build_job_url(job.get('id'))
#                 skills = job.get('skills', [])
#                 skill_display = ""
#                 if skills:
#                     skill_display = " • ".join(skills[:12])
#                     if len(skills) > 12:
#                         skill_display += f" • +{len(skills) - 12} more"

#                 job_msg = (
#                     "----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n"
#                     f"📋 **{job['title']}**\n"
#                     f"{job['description'][:350] + '...' if len(job['description']) > 350 else job['description']}\n\n"
#                     f"💰 **Budget:** {job.get('budget', 'N/A')}\n"
#                     f"📊 **Level:** {job.get('experience_level', 'Any')}\n"
#                     f"💼 **Type:** {job.get('job_type', 'N/A')}\n"
#                     f"⏱️ **Duration:** {job.get('duration_label', 'N/A')}\n"
#                     f"🕒 **Posted:** {format_posted_time(job.get('createdDateTime'))}\n"
#                     f"🎯 **Result:** #{i} of {len(filtered_jobs)}\n"
#                 )
#                 if skill_display:
#                     job_msg += f"🎯 **Required Skills:** `{skill_display}`\n"
#                 job_msg += (
#                     f"🌐 [Open Job]({job_url})\n"
#                     f"Job {i} of {len(filtered_jobs)} • Detailed info will be posted in thread below.\n"
#                     "---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\n"
#                 )
                
#                 # Post job with automatic details in thread
#                 await post_job_with_auto_details(ctx.channel, job, job_msg, f"Command search: {keyword}")
#                 await asyncio.sleep(0.5)
#         else:
#             await loading_msg.edit(content="😞 No jobs found for that keyword. Try different search terms!")

#     except Exception as e:
#         print(f"❌ Error in jobs command: {e}")
#         await loading_msg.edit(content="❌ An error occurred while searching. Please try again later.")

# @bot.command()
# async def skills(ctx, *, keyword=None):
#     """Command to search for jobs with enhanced skills analysis and horizontal layout"""
#     if not keyword:
#         embed = discord.Embed(
#             title="🎯 Skills Analysis Command",
#             description="Analyze skills required for specific job types",
#             color=0x3498db
#         )
#         embed.add_field(name="📝 Usage", value="`!skills <keyword>`", inline=True)
#         embed.add_field(name="💡 Example", value="`!skills react developer`", inline=True)
#         embed.add_field(name="📊 Analysis", value="Shows skills breakdown with auto-generated detail threads", inline=True)
#         await ctx.send(embed=embed)
#         return
    
#     # Add loading message
#     loading_msg = await ctx.send("🔍 Searching jobs and analyzing skills...")
    
#     try:
#         jobs = await scraper.fetch_jobs(query=keyword, limit=5)
        
#         if jobs:
#             # Delete loading message
#             await loading_msg.delete()
            
#             # Create skills summary
#             all_skills = {}
#             for job in jobs:
#                 for skill in job.get('skills', []):
#                     if skill and skill.strip():
#                         all_skills[skill] = all_skills.get(skill, 0) + 1
            
#             # Sort skills by frequency
#             sorted_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)
            
#             # Create enhanced skills summary embed
#             skills_embed = discord.Embed(
#                 title=f"🎯 Skills Analysis: '{keyword}'",
#                 description=f"Analyzed **{len(jobs)}** jobs with **{len(all_skills)}** unique skills",
#                 color=0x9b59b6
#             )
            
#             # Stats row (3 columns)
#             skills_embed.add_field(name="📊 Jobs Analyzed", value=str(len(jobs)), inline=True)
#             skills_embed.add_field(name="🎯 Unique Skills", value=str(len(all_skills)), inline=True)
#             skills_embed.add_field(name="🔥 Top Skills", value=str(min(10, len(sorted_skills))), inline=True)
            
#             # Show top 12 most requested skills in compact format
#             if sorted_skills:
#                 top_skills = sorted_skills[:12]
#                 skills_text = " • ".join([f"**{skill}** ({count})" for skill, count in top_skills])
#                 skills_embed.add_field(
#                     name="🔥 Most In-Demand Skills",
#                     value=skills_text,
#                     inline=False
#                 )
            
#             skills_embed.set_footer(text=f"Analysis complete • Requested by {ctx.author.display_name}")
#             await ctx.send(embed=skills_embed)
            
#             # Send individual job embeds with enhanced skills focus and auto details
#             for i, job in enumerate(jobs, 1):
#                 embed = discord.Embed(
#                     title=f"📋 {job['title']}",
#                     description=job['description'][:300] + "..." if len(job['description']) > 300 else job['description'],
#                     color=0x8e44ad,
#                     url=build_job_url(job.get('id'))
#                 )
                
#                 # ROW 1: Budget, Experience, Type (3 columns)
#                 embed.add_field(name="💰 Budget", value=job.get('budget', 'N/A'), inline=True)
#                 embed.add_field(name="📊 Level", value=job.get('experience_level', 'Any'), inline=True)
#                 embed.add_field(name="💼 Type", value=job.get('job_type', 'N/A'), inline=True)
                
#                 # Skills analysis (full width, prominent)
#                 skills = job.get('skills', [])
#                 skills_count = len(skills)
#                 if skills:
#                     skill_display = " • ".join(skills[:10])
#                     if len(skills) > 10:
#                         skill_display += f" • +{len(skills) - 10} more"
#                     embed.add_field(
#                         name=f"🎯 Required Skills ({skills_count} total)",
#                         value=f"`{skill_display}`",
#                         inline=False
#                     )
#                 else:
#                     embed.add_field(
#                         name="🎯 Skills",
#                         value="No specific skills listed",
#                         inline=False
#                     )
                
#                 # ROW 2: Duration, Posted, Skills Count (3 columns)
#                 embed.add_field(name="⏱️ Duration", value=job.get('duration_label', 'N/A'), inline=True)
#                 embed.add_field(name="🕒 Posted", value=format_posted_time(job.get('createdDateTime')), inline=True)
#                 embed.add_field(name="📊 Skills Count", value=f"{skills_count} skills", inline=True)
                
#                 embed.set_footer(
#                     text=f"Skills Analysis {i}/{len(jobs)} • Detailed info will be posted in thread below",
#                     icon_url="https://img.icons8.com/fluency/48/000000/clock.png"
#                 )
                
#                 # Post job with automatic details in thread
#                 await post_job_with_auto_details(ctx.channel, job, embed=embed, search_context=f"Skills analysis: {keyword}")
#                 await asyncio.sleep(0.5)
#         else:
#             await loading_msg.edit(content="😞 No jobs found for skills analysis. Try different search terms!")
            
#     except Exception as e:
#         print(f"❌ Error in skills command: {e}")
#         await loading_msg.edit(content="❌ An error occurred while analyzing skills. Please try again later.")

@bot.command()
async def help_jobs(ctx):
    """Show help for job searching with enhanced horizontal layout"""
    embed = discord.Embed(
        title="🤖 Enhanced Job Bot Help",
        description="Find Upwork jobs with advanced search, auto-generated detailed threads!",
        color=0x3498db
    )
    
    # Features row (3 columns)
    embed.add_field(name="💬 Auto Search", value="Type keywords for instant results", inline=True)
    embed.add_field(name="🔍 Manual Search", value="`!jobs <keyword>` for detailed results", inline=True)
    embed.add_field(name="🎯 Skills Analysis", value="`!skills <keyword>` for skill breakdown", inline=True)
    
    # Commands row (3 columns)
    embed.add_field(name="📝 Basic Search", value="`!jobs python developer`", inline=True)
    embed.add_field(name="🔬 Skills Focus", value="`!skills react developer`", inline=True)
    embed.add_field(name="❓ Get Help", value="`!help_jobs` (this command)", inline=True)
    
    # Auto-thread features (full width)
    embed.add_field(
        name="🧵 Automatic Thread Creation",
        value="**Every job automatically gets a detailed thread** with comprehensive information including client details, requirements, full skill lists, and more. No buttons needed!",
        inline=False
    )
    
    # Settings row (3 columns)
    embed.add_field(name="⏰ Auto-Search Cooldown", value=f"{COOLDOWN_SECONDS} seconds", inline=True)
    embed.add_field(name="📊 Results Per Search", value="Up to 10 jobs", inline=True)
    embed.add_field(name="🔄 Updates", value="Real-time job alerts", inline=True)
    
    # Examples (full width)
    embed.add_field(
        name="💡 Search Examples",
        value="`python` • `web developer` • `data analysis` • `graphic design` • `content writing` • `social media` • `wordpress` • `react developer`",
        inline=False
    )
    
    # New features highlight
    embed.add_field(
        name="🆕 Enhanced Features",
        value="**Auto Thread Details** - Comprehensive job info automatically posted • **No Buttons Required** - Everything happens automatically • **Skills Categorization** - Technical vs soft skills • **Client Verification** - Payment status & history • **Competition Analysis** - Applicant statistics",
        inline=False
    )
    
    embed.set_footer(text="Enhanced with automatic detailed threads for every job!")
    await ctx.send(embed=embed)

async def bhw_monitor_async():
    channel = bot.get_channel(DISCORD_CHANNEL_ID2)
    if channel is None:
        print(f"❌ Could not find channel with ID {DISCORD_CHANNEL_ID2}")
        return
    try:
        # Run post_new_bhw_threads in executor to avoid blocking
        loop = asyncio.get_event_loop()
        approved_threads = await loop.run_in_executor(None, lambda: post_new_bhw_threads(channel))
        if approved_threads:
            import discord
            from db.database import SessionLocal
            from db.models import BHWThread
            session = SessionLocal()
            try:
                for thread in approved_threads:
                    try:
                        embed = discord.Embed(
                            title=thread.title or 'No Title',
                            description=thread.full_description[:1500] if thread.full_description else 'No description',
                            url=thread.link,
                            color=0x00ff00
                        )
                        # Enhanced horizontal layout for BHW threads
                        embed.add_field(name="👤 Author", value=thread.author or 'Unknown', inline=True)
                        embed.add_field(name="💬 Replies", value=str(thread.replies_count or 0), inline=True)
                        embed.add_field(name="👀 Views", value=str(thread.views_count or 0), inline=True)
                        embed.add_field(name="📅 Posted", value=str(thread.posted), inline=True)
                        embed.add_field(name="🏷️ Category", value="BHW Thread", inline=True)
                        embed.add_field(name="⚡ Status", value="New", inline=True)
                        
                        embed.set_footer(text=f"BHW Auto-Monitor • Posted: {thread.posted}")
                        await channel.send(embed=embed)
                        # Mark as posted
                        db_thread = session.query(BHWThread).filter_by(link=thread.link).first()
                        if db_thread:
                            db_thread.posted_to_discord = True
                            session.commit()
                    except Exception as e:
                        print(f"[BHW] Error posting thread to Discord: {e}")
                print(f"✅ Posted {len(approved_threads)} new BHW threads to channel 2.")
            finally:
                session.close()
        else:
            print("ℹ️ No new BHW threads found for channel 2.")
    except Exception as e:
        print(f"❌ Error posting BHW threads: {e}")

async def run_scrapers_concurrently():
    await bot.wait_until_ready()
    while True:
        # Run both monitors truly concurrently
        await asyncio.gather(
            run_advanced_job_searches(),
            bhw_monitor_async()
        )
        await asyncio.sleep(5)  # Update every 5 seconds as requested