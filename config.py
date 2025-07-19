import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
CACHE_DIR = ".cache"
DB_PATH = os.path.join(CACHE_DIR, "cache.db")

# API configuration
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# Analysis configuration
MIN_PLAY_DURATION = int(os.getenv("MIN_PLAY_DURATION", 20000))  # in ms
TIMEZONE = os.getenv("TIMEZONE")
RECREATE_SONGDATA_FILES = os.getenv("RECREATE_SONGDATA_FILES", False)

# Output configuration
TOP_ARTISTS_COUNT = 500
TOP_SONGS_COUNT = 25
CHART_DATA_SIZE = 25
