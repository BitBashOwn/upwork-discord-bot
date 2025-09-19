import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

POSTGRES_URL = os.getenv("POSTGRES_URL")
UPWORK_EMAIL = os.getenv("UPWORK_EMAIL")
UPWORK_PASSWORD = os.getenv("UPWORK_PASSWORD")

# 2captcha API key (add to your .env file)
CAPTCHA_API_KEY = os.getenv("TWO_CAPTCHA_API_KEY")

PROXIES = [
    "http://mvpidhan:bt1per0s2glt@64.137.96.74:6641",
    "http://mvpidhan:bt1per0s2glt@45.43.186.39:6257",
    "http://mvpidhan:bt1per0s2glt@154.203.43.247:5536",
    "http://mvpidhan:bt1per0s2glt@216.10.27.159:6837",
    "http://mvpidhan:bt1per0s2glt@136.0.207.84:6661",
    "http://mvpidhan:bt1per0s2glt@142.147.128.93:6593",
    "http://mvpidhan:bt1per0s2glt@107.172.163.27:6543"
]