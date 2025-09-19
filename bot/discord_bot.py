import discord
from discord.ext import commands, tasks
from scraper.upwork_scraper import UpworkScraper
from config import DISCORD_TOKEN, DISCORD_CHANNEL_ID, UPWORK_EMAIL, UPWORK_PASSWORD
import asyncio
import re

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
scraper = UpworkScraper()

# Store the last search time to prevent spam
last_search_time = {}
COOLDOWN_SECONDS = 30  # Prevent searches more than once every 30 seconds per user

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"🔍 Bot will respond to keywords in channel ID: {DISCORD_CHANNEL_ID}")
    # Optional: Start periodic monitoring
    job_monitor.start()

@bot.event
async def on_message(message):
    # Don't respond to bot's own messages
    if message.author == bot.user:
        return
    
    # Only respond in the designated channel
    if message.channel.id != DISCORD_CHANNEL_ID:
        return
    
    # Don't respond to commands (let command handler deal with them)
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return
    
    # Check cooldown
    user_id = message.author.id
    current_time = asyncio.get_event_loop().time()
    
    if user_id in last_search_time:
        if current_time - last_search_time[user_id] < COOLDOWN_SECONDS:
            await message.add_reaction("⏰")  # Clock emoji to indicate cooldown
            return
    
    last_search_time[user_id] = current_time
    
    # Extract keywords from the message
    keyword = message.content.strip()
    
    # Skip very short messages or common words
    if len(keyword) < 2 or keyword.lower() in ['hi', 'hello', 'hey', 'ok', 'yes', 'no', 'thanks']:
        return
    
    # Add a loading reaction
    await message.add_reaction("🔍")
    
    try:
        # Search for jobs using the keyword
        print(f"🔍 Searching for jobs with keyword: '{keyword}'")
        jobs = scraper.fetch_jobs(query=keyword, limit=5)
        
        if jobs:
            print(f"✅ Found {len(jobs)} jobs for keyword: '{keyword}'")
            
            # Create embed for search results
            main_embed = discord.Embed(
                title=f"🎯 Job Search Results for '{keyword}'",
                description=f"Found {len(jobs)} jobs matching your search",
                color=0x00ff00
            )
            main_embed.set_footer(text=f"Requested by {message.author.display_name}")
            
            await message.channel.send(embed=main_embed)
            
            # Send individual job embeds (limit to first 3 to avoid spam)
            for i, job in enumerate(jobs[:3], 1):
                embed = discord.Embed(
                    title=f"📋 {job['title']}",
                    description=job['description'][:500] + "..." if len(job['description']) > 500 else job['description'],
                    color=0x3498db,
                    url=f"https://www.upwork.com/jobs/~{job['id']}" if job['id'] else None
                )
                
                # Add job details
                embed.add_field(
                    name="💰 Budget", 
                    value=job.get('budget', 'Not specified'), 
                    inline=True
                )
                # embed.add_field(
                #     name="🏢 Client", 
                #     value=job.get('client', 'Unknown'), 
                #     inline=True
                # )
                # embed.add_field(
                #     name="👥 Applicants", 
                #     value=str(job.get('total_applicants', 'N/A')), 
                #     inline=True
                # )
                
                if job.get('experience_level'):
                    embed.add_field(
                        name="📊 Experience Level", 
                        value=job.get('experience_level'), 
                        inline=True
                    )
                
                if job.get('job_type'):
                    embed.add_field(
                        name="💼 Job Type", 
                        value=job.get('job_type'), 
                        inline=True
                    )
                
                if job.get('duration_label'):
                    embed.add_field(
                        name="⏱️ Duration", 
                        value=job.get('duration_label'), 
                        inline=True
                    )
                
                # Add skills field with proper formatting
                skills = job.get('skills', [])
                if skills:
                    # Limit to first 5 skills to avoid overly long embeds
                    skill_display = ", ".join(skills[:5])
                    if len(skills) > 5:
                        skill_display += f" +{len(skills) - 5} more"
                    
                    embed.add_field(
                        name="🎯 Required Skills", 
                        value=f"`{skill_display}`", 
                        inline=False
                    )
                
                embed.set_footer(text=f"Job {i} of {min(len(jobs), 3)} • Posted: {job.get('createdDateTime', 'Unknown')}")
                
                msg = await message.channel.send(embed=embed)
                await msg.add_reaction("✅")  # Allow users to react to jobs they like
                await msg.add_reaction("❌")  # Allow users to react to jobs they don't like
                
                # Small delay between job posts to avoid rate limits
                await asyncio.sleep(1)
            
            # If there are more jobs, mention it
            if len(jobs) > 3:
                overflow_embed = discord.Embed(
                    description=f"... and {len(jobs) - 3} more jobs. Use `!jobs {keyword}` for the full list.",
                    color=0xf39c12
                )
                await message.channel.send(embed=overflow_embed)
            
            # Remove the loading reaction and add success
            await message.remove_reaction("🔍", bot.user)
            await message.add_reaction("✅")
            
        else:
            # No jobs found
            embed = discord.Embed(
                title="😞 No Jobs Found",
                description=f"Sorry, no jobs found for '{keyword}'. Try a different keyword or check back later!",
                color=0xe74c3c
            )
            embed.set_footer(text="Try using different keywords like 'python', 'web developer', 'data analyst', etc.")
            await message.channel.send(embed=embed)
            
            # Remove loading and add sad reaction
            await message.remove_reaction("🔍", bot.user)
            await message.add_reaction("😞")
    
    except Exception as e:
        print(f"❌ Error searching for jobs: {e}")
        
        error_embed = discord.Embed(
            title="⚠️ Search Error",
            description="Something went wrong while searching for jobs. Please try again later.",
            color=0xe74c3c
        )
        await message.channel.send(embed=error_embed)
        
        # Remove loading and add error reaction
        await message.remove_reaction("🔍", bot.user)
        await message.add_reaction("❌")
    
    # Process commands after handling the message
    await bot.process_commands(message)

@bot.command()
async def jobs(ctx, *, keyword=None):
    """Command to search for jobs with more results"""
    if not keyword:
        embed = discord.Embed(
            title="🔍 Job Search Command",
            description="Usage: `!jobs <keyword>`\nExample: `!jobs python developer`",
            color=0x3498db
        )
        await ctx.send(embed=embed)
        return
    
    # Add loading message
    loading_msg = await ctx.send("🔍 Searching for jobs...")
    
    try:
        
        jobs = scraper.fetch_jobs(query=keyword, limit=10)
        
        if jobs:
            # Delete loading message
            await loading_msg.delete()
            
            # Create main results embed
            main_embed = discord.Embed(
                title=f"🎯 Job Search Results for '{keyword}'",
                description=f"Found {len(jobs)} jobs (showing up to 10)",
                color=0x00ff00
            )
            main_embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=main_embed)
            
            # Send all jobs found (up to 10)
            for i, job in enumerate(jobs, 1):
                embed = discord.Embed(
                    title=f"📋 {job['title']}",
                    description=job['description'][:400] + "..." if len(job['description']) > 400 else job['description'],
                    color=0x3498db
                )
                
                embed.add_field(name="💰 Budget", value=job.get('budget', 'Not specified'), inline=True)
                # embed.add_field(name="🏢 Client", value=job.get('client', 'Unknown'), inline=True)
                # embed.add_field(name="👥 Applicants", value=str(job.get('total_applicants', 'N/A')), inline=True)
                
                if job.get('experience_level'):
                    embed.add_field(name="📊 Experience", value=job.get('experience_level'), inline=True)
                if job.get('job_type'):
                    embed.add_field(name="💼 Job Type", value=job.get('job_type'), inline=True)
                if job.get('duration_label'):
                    embed.add_field(name="⏱️ Duration", value=job.get('duration_label'), inline=True)
                
                # Add skills with better formatting for command results
                skills = job.get('skills', [])
                if skills:
                    # Show more skills in command results
                    skill_display = ", ".join(skills[:8])
                    if len(skills) > 8:
                        skill_display += f" +{len(skills) - 8} more"
                    
                    embed.add_field(
                        name="🎯 Required Skills", 
                        value=f"`{skill_display}`", 
                        inline=False
                    )
                
                embed.set_footer(text=f"Job {i} of {len(jobs)} • Posted: {job.get('createdDateTime', 'Unknown')}")
                
                msg = await ctx.send(embed=embed)
                await msg.add_reaction("✅")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
        else:
            await loading_msg.edit(content="😞 No jobs found for that keyword. Try different search terms!")
            
    except Exception as e:
        print(f"❌ Error in jobs command: {e}")
        await loading_msg.edit(content="❌ An error occurred while searching. Please try again later.")

@bot.command()
async def skills(ctx, *, keyword=None):
    """Command to search for jobs and show detailed skills breakdown"""
    if not keyword:
        embed = discord.Embed(
            title="🎯 Skills Search Command",
            description="Usage: `!skills <keyword>`\nExample: `!skills react developer`\n\nThis command shows detailed skills for each job.",
            color=0x3498db
        )
        await ctx.send(embed=embed)
        return
    
    # Add loading message
    loading_msg = await ctx.send("🔍 Searching for jobs and analyzing skills...")
    
    try:
        jobs = scraper.fetch_jobs(query=keyword, limit=5)
        
        if jobs:
            # Delete loading message
            await loading_msg.delete()
            
            # Create skills summary
            all_skills = {}
            for job in jobs:
                for skill in job.get('skills', []):
                    if skill and skill.strip():
                        all_skills[skill] = all_skills.get(skill, 0) + 1
            
            # Sort skills by frequency
            sorted_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)
            
            # Create skills summary embed
            skills_embed = discord.Embed(
                title=f"🎯 Skills Analysis for '{keyword}'",
                description=f"Found {len(jobs)} jobs with {len(all_skills)} unique skills",
                color=0x9b59b6
            )
            
            # Show top 10 most requested skills
            if sorted_skills:
                top_skills = sorted_skills[:10]
                skills_text = "\n".join([f"**{skill}** - {count} job{'s' if count > 1 else ''}" 
                                       for skill, count in top_skills])
                skills_embed.add_field(
                    name="🔥 Most Requested Skills",
                    value=skills_text,
                    inline=False
                )
            
            skills_embed.set_footer(text=f"Analyzed {len(jobs)} jobs • Requested by {ctx.author.display_name}")
            await ctx.send(embed=skills_embed)
            
            # Send individual job embeds with full skills
            for i, job in enumerate(jobs, 1):
                embed = discord.Embed(
                    title=f"📋 {job['title']}",
                    description=job['description'][:300] + "..." if len(job['description']) > 300 else job['description'],
                    color=0x8e44ad
                )
                
                embed.add_field(name="💰 Budget", value=job.get('budget', 'Not specified'), inline=True)
                if job.get('experience_level'):
                    embed.add_field(name="📊 Experience", value=job.get('experience_level'), inline=True)
                if job.get('job_type'):
                    embed.add_field(name="💼 Type", value=job.get('job_type'), inline=True)
                
                # Show ALL skills for this command
                skills = job.get('skills', [])
                if skills:
                    # Group skills into chunks to avoid Discord field limits
                    skill_chunks = []
                    current_chunk = []
                    current_length = 0
                    
                    for skill in skills:
                        skill_with_separator = f"`{skill}`, "
                        if current_length + len(skill_with_separator) > 1000:  # Discord field limit
                            skill_chunks.append("".join(current_chunk).rstrip(", "))
                            current_chunk = [skill_with_separator]
                            current_length = len(skill_with_separator)
                        else:
                            current_chunk.append(skill_with_separator)
                            current_length += len(skill_with_separator)
                    
                    if current_chunk:
                        skill_chunks.append("".join(current_chunk).rstrip(", "))
                    
                    # Add skill chunks as separate fields
                    for chunk_i, chunk in enumerate(skill_chunks):
                        field_name = "🎯 Required Skills" if chunk_i == 0 else f"🎯 Skills (cont. {chunk_i + 1})"
                        embed.add_field(
                            name=field_name,
                            value=chunk,
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="🎯 Required Skills",
                        value="No specific skills listed",
                        inline=False
                    )
                
                embed.set_footer(text=f"Job {i} of {len(jobs)} • {len(skills)} skills total")
                
                msg = await ctx.send(embed=embed)
                await msg.add_reaction("🎯")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
        else:
            await loading_msg.edit(content="😞 No jobs found for that keyword. Try different search terms!")
            
    except Exception as e:
        print(f"❌ Error in skills command: {e}")
        await loading_msg.edit(content="❌ An error occurred while searching. Please try again later.")

@bot.command()
async def help_jobs(ctx):
    """Show help for job searching"""
    embed = discord.Embed(
        title="🤖 Job Bot Help",
        description="This bot helps you find Upwork jobs!",
        color=0x3498db
    )
    
    embed.add_field(
        name="💬 Auto Search",
        value="Just type any keyword in this channel and I'll search for jobs automatically!",
        inline=False
    )
    
    embed.add_field(
        name="🔍 Manual Search",
        value="`!jobs <keyword>` - Search for jobs with detailed results\n`!skills <keyword>` - Focus on skills analysis",
        inline=False
    )
    
    embed.add_field(
        name="⏰ Cooldown",
        value=f"Auto searches have a {COOLDOWN_SECONDS} second cooldown per user to prevent spam",
        inline=False
    )
    
    embed.add_field(
        name="💡 Examples",
        value="Try typing: `python`, `web developer`, `data analysis`, `graphic design`\nOr use: `!skills react developer` for skills focus",
        inline=False
    )
    
    await ctx.send(embed=embed)

@tasks.loop(seconds=5) # Optional: Check for new jobs every 30 minutes
async def job_monitor():
    """Optional periodic job monitoring"""
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        print(f"❌ Could not find channel with ID {DISCORD_CHANNEL_ID}")
        return
    
    try:
        # You can customize this to monitor specific keywords
        popular_keywords = ["python developer", "web developer", "data analyst"]
        
        for keyword in popular_keywords:
            jobs = scraper.fetch_jobs(query=keyword, limit=1)  # Just get the most recent
            
            if jobs:
                job = jobs[0]
                embed = discord.Embed(
                    title=f"🔔 New Job Alert",
                    description=job['description'][:300] + "..." if len(job['description']) > 300 else job['description'],
                    color=0xff9500
                )
                
                embed.add_field(name="💰 Budget", value=job.get('budget', 'Not specified'), inline=True)
                # embed.add_field(name="🏢 Client", value=job.get('client', 'Unknown'), inline=True)
                # embed.add_field(name="👥 Applicants", value=str(job.get('total_applicants', 'N/A')), inline=True)

                # Add skills to monitoring alerts
                skills = job.get('skills', [])
                if skills:
                    skill_display = ", ".join(skills[:5])
                    if len(skills) > 5:
                        skill_display += f" +{len(skills) - 5} more"
                    embed.add_field(
                        name="🎯 Skills", 
                        value=f"`{skill_display}`", 
                        inline=False
                    )
                
                embed.set_footer(text=f"Auto-monitoring")
                
                msg = await channel.send(embed=embed)
                await msg.add_reaction("🔔")
            
            # Delay between keyword searches
            await asyncio.sleep(5)
            
    except Exception as e:
        print(f"❌ Error in job monitor: {e}")

# Uncomment to enable periodic monitoring
@job_monitor.before_loop
async def before_job_monitor():
    await bot.wait_until_ready()

bot.run(DISCORD_TOKEN)