class Config:
    SECRET_KEY = 'you-will-neva-guess'  # Replace with a real secret key
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USERNAME = 'your_email@gmail.com'
    MAIL_PASSWORD = 'your_password'
    MAIL_USE_SSL = True
    UPLOAD_FOLDER = "./static/uploads"
    MAX_CONTENT_LENGTH = 60 * 1024 * 1024  # 60 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'wmv'}
