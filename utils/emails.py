# from datetime import datetime
# from flask import url_for
# from flask_mail import Message
# from app import mail  # Import the shared mail instance

# def send_verification_email(app, email, token):
#     """Send a professional verification email to the user"""
#     with app.app_context():
#         verification_url = url_for(
#             'auth.verify_email',
#             token=token,
#             _external=True
#         )
        
#         subject = "Please verify your email address"
        
#         html_body = f"""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <meta charset="UTF-8">
#             <title>Email Verification</title>
#             <style>
#                 body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
#                 .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
#                 .button {{
#                     background-color: #3498db; color: white;
#                     padding: 12px 24px; text-decoration: none;
#                     border-radius: 4px; font-weight: bold;
#                     display: inline-block;
#                 }}
#                 .footer {{ font-size: 0.9em; color: #777; }}
#             </style>
#         </head>
#         <body>
#             <div class="container">
#                 <h2 style="color: #2c3e50;">Welcome to Our Service!</h2>
#                 <p>Thank you for registering. Please verify your email address to complete your account setup.</p>
                
#                 <div style="text-align: center; margin: 25px 0;">
#                     <a href="{verification_url}" class="button">
#                         Verify Email Address
#                     </a>
#                 </div>
                
#                 <p>If the button doesn't work, copy and paste this link into your browser:</p>
#                 <p style="word-break: break-all;">{verification_url}</p>
                
#                 <p>If you didn't request this, please ignore this email.</p>
                
#                 <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
#                 <p class="footer">
#                     © {datetime.now().year} Dunis Technologies Limited. All rights reserved.
#                 </p>
#             </div>
#         </body>
#         </html>
#         """
        
#         text_body = f"""
#         Welcome to Our Business Promotional Service!

#         Thank you for registering. Please verify your email address by visiting this link:

#         {verification_url}

#         If you didn't request this, please ignore this email.

#         © {datetime.now().year} Dunis Technologies Limited. All rights reserved.
#         """
        
#         try:
#             msg = Message(
#                 subject=subject,
#                 recipients=[email],
#                 html=html_body,
#                 body=text_body,
#                 sender=app.config['MAIL_DEFAULT_SENDER']
#             )
#             mail.send(msg)
#             app.logger.info(f"Verification email sent to {email}")
#             return True
#         except Exception as e:
#             app.logger.error(f"Failed to send verification email to {email}: {str(e)}")
#             return False

# def send_reset_email(app, email, token):
#     """Send password reset email"""
#     with app.app_context():
#         reset_url = url_for('auth.reset_password', token=token, _external=True)
        
#         subject = "Password Reset Request"
        
#         html_body = f"""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <meta charset="UTF-8">
#             <title>Password Reset</title>
#             <style>
#                 body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
#                 .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
#                 .button {{
#                     background-color: #3498db; color: white;
#                     padding: 12px 24px; text-decoration: none;
#                     border-radius: 4px; font-weight: bold;
#                     display: inline-block;
#                 }}
#                 .footer {{ font-size: 0.9em; color: #777; }}
#             </style>
#         </head>
#         <body>
#             <div class="container">
#                 <h2 style="color: #2c3e50;">Password Reset Request</h2>
#                 <p>We received a request to reset your password. Click the button below to proceed:</p>
                
#                 <div style="text-align: center; margin: 25px 0;">
#                     <a href="{reset_url}" class="button">
#                         Reset Password
#                     </a>
#                 </div>
                
#                 <p>If you didn't request this password reset, please ignore this email.</p>
#                 <p>This link will expire in 1 hour.</p>
                
#                 <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
#                 <p class="footer">
#                     © {datetime.now().year} Dunis Technologies Limited. All rights reserved.
#                 </p>
#             </div>
#         </body>
#         </html>
#         """
        
#         try:
#             msg = Message(
#                 subject=subject,
#                 recipients=[email],
#                 html=html_body,
#                 sender=app.config['MAIL_DEFAULT_SENDER']
#             )
#             mail.send(msg)
#             app.logger.info(f"Password reset email sent to {email}")
#             return True
#         except Exception as e:
#             app.logger.error(f"Failed to send password reset email to {email}: {str(e)}")
#             return False

# v2
# utils/emails.py
from flask import url_for
from flask_mail import Message

def send_verification_email(app, email, token):
    """Send verification email using app context"""
    try:
        with app.app_context():
            mail = app.extensions['mail']  # Get mail from app extensions
            verification_url = url_for('auth.verify_email', token=token, _external=True)
            
            msg = Message(
                subject='Verify Your Email',
                recipients=[email],
                html=f"""
                <p>Click the link below to verify your email:</p>
                <a href="{verification_url}">{verification_url}</a>
                <p>This link will expire in 24 hours.</p>
                """
            )
            mail.send(msg)
            return True
    except Exception as e:
        app.logger.error(f"Failed to send verification email: {str(e)}")
        return False

def send_reset_email(app, email, token):
    """Send password reset email"""
    try:
        with app.app_context():
            mail = app.extensions['mail']
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            msg = Message(
                subject='Password Reset Request',
                recipients=[email],
                html=f"""
                <p>Click the link below to reset your password:</p>
                <a href="{reset_url}">{reset_url}</a>
                <p>If you didn't request this, please ignore this email.</p>
                """
            )
            mail.send(msg)
            return True
    except Exception as e:
        app.logger.error(f"Failed to send reset email: {str(e)}")
        return False

