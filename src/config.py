import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
INTRO_VIDEO_PATH = os.getenv("INTRO_VIDEO_PATH", "")
INTRO_VIDEO_CAPTION = os.getenv("INTRO_VIDEO_CAPTION", "")
