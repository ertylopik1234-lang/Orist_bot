import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CX = os.getenv("GOOGLE_CX", "")

GOOGLE_ALERT_RSS = os.getenv("GOOGLE_ALERT_RSS", "")
TALKWALKER_RSS = os.getenv("TALKWALKER_RSS", "")", "")
