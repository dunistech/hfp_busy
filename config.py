import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-default-secret-key-here')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    
    # Database Configuration
    # SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql://user:password@localhost/db_name')

    # For mysqlclient (recommended)
    # SQLALCHEMY_DATABASE_URI = 'mysql://username:password@localhost/db_name'
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'mysql://root:techa.tech500@localhost/hfp_db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.simplylovely.ng')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'noreply@simplylovely.ng')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'AJAH BUSINESSES <noreply@simplylovely.ng>')
    
    # Correct upload folder configuration
    UPLOAD_FOLDER = os.path.join('static', 'uploads')  # Relative to application
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

    
    # Security
    SESSION_COOKIE_SECURE = FLASK_ENV == 'production'
    REMEMBER_COOKIE_SECURE = FLASK_ENV == 'production'
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'
    MAIL_SUPPRESS_SEND = False  # Actually send emails in development

class TestingConfig(Config):
    TESTING = True
    MAIL_SUPPRESS_SEND = True  # Don't send emails during tests

class ProductionConfig(Config):
    DEBUG = False
    MAIL_SUPPRESS_SEND = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}