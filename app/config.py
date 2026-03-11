import os


class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/aigateway')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    HF_API_KEY = os.getenv('HF_API_KEY', '')
    TIMEOUT_SECONDS = int(os.getenv('TIMEOUT_SECONDS', '10'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '1'))
    CIRCUIT_BREAKER_THRESHOLD = int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '3'))
    CIRCUIT_BREAKER_RESET_TIMEOUT = int(os.getenv('CIRCUIT_BREAKER_RESET_TIMEOUT', '60'))
    API_KEY = os.getenv('API_KEY', '')
