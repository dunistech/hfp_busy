from os import getenv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = 'you-will-neva-guess-pls-try-edet-james-'  # Replace with a real secret key
    # MAIL_SERVER = 'smtp.gmail.com'
    # MAIL_PORT = 465
    # MAIL_SERVER = "https://simplylovely.ng"
    # MAIL_USERNAME = "simpdinr"
    # MAIL_PASSWORD = "PZziNGCDSThq"
    # # MAIL_USERNAME = getenv('MAIL_USERNAME')
    # # MAIL_PASSWORD = getenv('MAIL_PASSWORD')
    # MAIL_USE_SSL = True
    
    # 
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    # MAIL_SERVER = getenv('MAIL_SERVER')
    # MAIL_USERNAME = getenv('MAIL_USERNAME')
    # MAIL_PASSWORD = getenv('MAIL_PASSWORD')
    
    MAIL_SERVER = "premium57.web-hosting.com"
    MAIL_USERNAME = "hi@simplylovely.ng"
    MAIL_PASSWORD = "hi@simplylovely.ng"
    
    UPLOAD_FOLDER = "./static/uploads"
    MAX_CONTENT_LENGTH = 60 * 1024 * 1024  # 60 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'wmv'}
    print('mail user', MAIL_USERNAME, MAIL_PASSWORD )


