from flask import url_for
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
from werkzeug.utils import secure_filename
import os 
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

from config import Config as config
allowed_extensions = config.ALLOWED_EXTENSIONS
# print(dir(config.Config))

# role/permission
from functools import wraps
from flask import abort, session

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# UPLOAD Images and Videos Function
def upload_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        return filename  
    return None

# # 
# import mysql.connector, os
# # Function to establish a direct MySQL connection
def get_db_connection():
    try:
        # Fetching connection parameters from environment variables
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),  
            database=os.getenv('DB_NAME', 'hfp_data'),  
            user=os.getenv('DB_USER', 'root'),  # Default MySQL username
            password=os.getenv('DB_PASSWORD', 'password')  # Default MySQL password
        )
        if conn.is_connected():
            print("Successfully connected to MySQL database!")
        return conn
    except mysql.connector.Error as e:
        print(f"Error: {e}")
    return None

def fetch_categories():
    conn = get_db_connection()
    categories = []
    if conn:
        try:
            cur = conn.cursor(dictionary=True)  # Fetch rows as dictionaries
            cur.execute("SELECT id, category_name FROM categories")
            result = cur.fetchall()
            # categories = {row['id']: row['category_name'] for row in result}  # Convert to dict

            categories = [{"id": row['id'], 'name': row['category_name'] } for row in result]  # List of named tuples
            
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
        finally:
            cur.close()
            conn.close()
            
    # return categories  # Return categories as dict
    return {"categories": categories}

def fetch_plans():
    conn = get_db_connection()
    plans = []
    if conn:
        try:
            cur = conn.cursor(buffered=True, dictionary=True)  # Fetch rows as dictionaries
            # cur.execute("SELECT id, category_name FROM categories")
             # Fetch subscription plans
            cur.execute("""
                SELECT id, plan_name, amount, duration
                FROM subscription_plans
            """)
            
            # subscription_plans = cur.fetchall()
            
            result = cur.fetchall()
            # categories = {row['id']: row['category_name'] for row in result}  # Convert to dict

            plans = [
                {
                "id": row['id'], 'plan_name': row['plan_name'],
                'amount': row['amount'], 'duration':row['duration']
            } 
            for row in result
            ]  # List of named tuples
            
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
        finally:
            cur.close()
            conn.close()
            
    # return categories  # Return categories as dict
    return {"subscription_plans": plans }

serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))

def generate_token(email):
    """Generate a time-sensitive verification token"""
    return serializer.dumps(email, salt='email-verification-salt')

def verify_token(token, max_age=3600):
    """Verify the token and return the email if valid"""
    try:
        email = serializer.loads(
            token,
            salt='email-verification-salt',
            max_age=max_age
        )
        return email
    except Exception as e:
        app.logger.error(f"Token verification failed: {str(e)}")
        return None

# ## Forgotton password Route and Functions ##
def generate_reset_token(user_id):
    # serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))
    return serializer.dumps(user_id, salt='password-reset-salt')

def verify_reset_token(token, expiration=3600):
    # serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))
    try:
        user_id = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return None
    return user_id

# def send_reset_email(app, email, token):
#     with app.app_context():  # Set the application context
#         mail = create_mail_instance(app)
#         reset_url = url_for('auth.reset_password', token=token, _external=True)
#         msg = Message('Password Reset Request', sender='Dunistech <Coders@gmail.com>', recipients=[email])
#         msg.body = f'To reset your password, click the following link: {reset_url}'
#         msg.html = f'<p>To reset your password, click the following link: <a href="{reset_url}">{reset_url}</a></p>'
#         mail.send(msg)

# # VERIFICATIONS EMAIL
# from flask_mail import Message
# from your_app import mail, app  # Import your Flask app and mail instance

# def send_verification_email(email, token):
#     """Send a professional verification email to the user"""
#     verification_url = url_for(
#         'auth.verify_email',
#         token=token,
#         _external=True
#     )
    
#     subject = "Please verify your email address"
    
#     # HTML email template
#     html_body = f"""
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <meta charset="UTF-8">
#         <title>Email Verification</title>
#     </head>
#     <body style="font-family: Arial, sans-serif; line-height: 1.6;">
#         <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
#             <h2 style="color: #2c3e50;">Welcome to Our Service!</h2>
#             <p>Thank you for registering. Please verify your email address to complete your account setup.</p>
            
#             <div style="text-align: center; margin: 25px 0;">
#                 <a href="{verification_url}" 
#                    style="background-color: #3498db; color: white; 
#                           padding: 12px 24px; text-decoration: none; 
#                           border-radius: 4px; font-weight: bold;">
#                     Verify Email Address
#                 </a>
#             </div>
            
#             <p>If the button doesn't work, copy and paste this link into your browser:</p>
#             <p style="word-break: break-all;">{verification_url}</p>
            
#             <p>If you didn't request this, please ignore this email.</p>
            
#             <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
#             <p style="font-size: 0.9em; color: #777;">
#                 © {datetime.now().year} Dunis Technologies Limited. All rights reserved.
#             </p>
#         </div>
#     </body>
#     </html>
#     """
    
#     # Plain text version for email clients that don't support HTML
#     text_body = f"""
#     Welcome to Our Service!

#     Thank you for registering. Please verify your email address by visiting this link:

#     {verification_url}

#     If you didn't request this, please ignore this email.

#     © {datetime.now().year} Your Company Name. All rights reserved.
#     """
    
#     try:
#         msg = Message(
#             subject=subject,
#             recipients=[email],
#             html=html_body,
#             body=text_body,
#             sender=app.config['MAIL_DEFAULT_SENDER']  # From your config
#         )
#         mail.send(msg)
#         app.logger.info(f"Verification email sent to {email}")
#         return True
#     except Exception as e:
#         app.logger.error(f"Failed to send verification email to {email}: {str(e)}")
#         return False

# 
import os
from datetime import datetime
from flask import url_for
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask-Mail
mail = Mail()

# Database Configuration
def get_db_config():
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'hfp_data'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }

# Email Configuration
class EmailConfig:
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@simplylovely.ng')
    MAIL_MAX_EMAILS = int(os.getenv('MAIL_MAX_EMAILS', 10))
    MAIL_ASCII_ATTACHMENTS = os.getenv('MAIL_ASCII_ATTACHMENTS', 'false').lower() == 'true'

# Initialize URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY', 'dont-think-about-it'))

def init_mail(app):
    """Initialize Flask-Mail with the application"""
    app.config.from_object(EmailConfig)
    mail.init_app(app)

def send_verification_email(app, email, token):
    """Send a professional verification email to the user"""
    with app.app_context():
        verification_url = url_for(
            'auth.verify_email',
            token=token,
            _external=True
        )
        
        subject = "Please verify your email address"
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Email Verification</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{
                    background-color: #3498db; color: white;
                    padding: 12px 24px; text-decoration: none;
                    border-radius: 4px; font-weight: bold;
                    display: inline-block;
                }}
                .footer {{ font-size: 0.9em; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 style="color: #2c3e50;">Welcome to Our Service!</h2>
                <p>Thank you for registering. Please verify your email address to complete your account setup.</p>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{verification_url}" class="button">
                        Verify Email Address
                    </a>
                </div>
                
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="word-break: break-all;">{verification_url}</p>
                
                <p>If you didn't request this, please ignore this email.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p class="footer">
                    © {datetime.now().year} Dunis Technologies Limited. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Welcome to Our Business Promotional Service!

        Thank you for registering. Please verify your email address by visiting this link:

        {verification_url}

        If you didn't request this, please ignore this email.

        © {datetime.now().year} Dunis Technologies Limited. All rights reserved.
        """
        
        try:
            msg = Message(
                subject=subject,
                recipients=[email],
                html=html_body,
                body=text_body,
                sender=("Dunis Technologies", EmailConfig.MAIL_DEFAULT_SENDER)
            )
            mail.send(msg)
            app.logger.info(f"Verification email sent to {email}")
            return True
        except Exception as e:
            app.logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False

def send_reset_email(app, email, token):
    """Send password reset email"""
    with app.app_context():
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        subject = "Password Reset Request"
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Password Reset</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{
                    background-color: #3498db; color: white;
                    padding: 12px 24px; text-decoration: none;
                    border-radius: 4px; font-weight: bold;
                    display: inline-block;
                }}
                .footer {{ font-size: 0.9em; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 style="color: #2c3e50;">Password Reset Request</h2>
                <p>We received a request to reset your password. Click the button below to proceed:</p>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{reset_url}" class="button">
                        Reset Password
                    </a>
                </div>
                
                <p>If you didn't request this password reset, please ignore this email.</p>
                <p>This link will expire in 1 hour.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p class="footer">
                    © {datetime.now().year} Dunis Technologies Limited. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            msg = Message(
                subject=subject,
                recipients=[email],
                html=html_body,
                sender=("Dunis Technologies", EmailConfig.MAIL_DEFAULT_SENDER)
            )
            mail.send(msg)
            app.logger.info(f"Password reset email sent to {email}")
            return True
        except Exception as e:
            app.logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False