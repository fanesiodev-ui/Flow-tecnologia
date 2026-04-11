import os
from dotenv import load_dotenv

load_dotenv()

# Diretório temporário para uploads (processados e descartados em seguida)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "storage", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Limite de tamanho de arquivo
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024