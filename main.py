from db.database import init_db
from bot.discord_bot import bot
from db.database import init_db

# Ensure all tables are created before starting the bot
init_db()

if __name__ == "__main__":
    init_db()
    # Discord bot runs scraper in background
