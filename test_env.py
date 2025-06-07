# test_env.py
from dotenv import load_dotenv
import os

load_dotenv()

print("MAIL_USERNAME:", os.getenv("MAIL_USERNAME"))
print("MAIL_PASSWORD:", os.getenv("MAIL_PASSWORD"))
