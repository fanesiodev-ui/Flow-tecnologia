import os
from dotenv import load_dotenv

load_dotenv()

# Storage paths (relative to backend/ directory)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "storage", "uploads")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "storage", "reports")

# File limits
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# Auto-create directories on startup
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
