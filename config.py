import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.getenv('APP_ENV_FILE', os.path.join(BASE_DIR, '.env'))

load_dotenv(ENV_FILE_PATH)

class Config:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
    DB_NAME = os.getenv('DB_NAME', 'ai_week')
    
    ALIYUN_API_KEY = os.getenv('ALIYUN_API_KEY')
    ALIYUN_MODEL = os.getenv('ALIYUN_MODEL', 'qwen-turbo')
    ALIYUN_VL_MODEL = os.getenv('ALIYUN_VL_MODEL', 'qwen-omni-turbo') # For Image OCR
    APP_ACCESS_PASSWORD = os.getenv('APP_ACCESS_PASSWORD', '213213')
    
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev_key')
