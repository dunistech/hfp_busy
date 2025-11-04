# utils/emails.py
from datetime import datetime
from flask import url_for
from flask_mail import Message

def send_verification_email(app, email, token):
    """Send a simple but professional verification email"""
    try:
        with app.app_context():
            mail = app.extensions['mail']
            verification_url = url_for('auth.verify_email', token=token, _external=True)

            current_year = datetime.now().year
            subject = "Verify Your Email Address – Dunis Technologies"

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background: #f7f9fb;
                        color: #333;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 40px auto;
                        background: #fff;
                        border-radius: 10px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                        padding: 30px;
                    }}
                    h2 {{
                        color: #004080;
                        text-align: center;
                        margin-bottom: 20px;
                    }}
                    p {{
                        line-height: 1.7;
                        font-size: 15px;
                    }}
                    .btn {{
                        display: inline-block;
                        background: #004080;
                        color: #fff !important;
                        text-decoration: none;
                        padding: 12px 24px;
                        border-radius: 6px;
                        font-weight: 600;
                        margin: 25px 0;
                    }}
                    .footer {{
                        font-size: 12px;
                        color: #888;
                        text-align: center;
                        border-top: 1px solid #eee;
                        padding-top: 15px;
                        margin-top: 30px;
                    }}
                    a {{ color: #004080; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Verify Your Email</h2>
                    <p>Hello,</p>
                    <p>Thank you for signing up with <strong>Dunis Technologies</strong>. Please verify your email address by clicking the button below:</p>
                    <div style="text-align:center;">
                        <a href="{verification_url}" class="btn">Verify Email</a>
                    </div>
                    <p>If the button doesn’t work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all;">{verification_url}</p>
                    <p>This link will expire in 24 hours.</p>
                    <div class="footer">
                        © {current_year} Dunis Technologies Limited. All rights reserved.
                    </div>
                </div>
            </body>
            </html>
            """

            msg = Message(
                subject=subject,
                recipients=[email],
                html=html_body,
                sender=app.config['MAIL_DEFAULT_SENDER']
            )

            mail.send(msg)
            app.logger.info(f"Verification email sent to {email}")
            return True
    except Exception as e:
        app.logger.error(f"Failed to send verification email: {str(e)}")
        return False


def send_reset_email(app, email, token):
    """Send a professional password reset email"""
    try:
        with app.app_context():
            mail = app.extensions['mail']
            reset_url = url_for('auth.reset_password', token=token, _external=True)

            current_year = datetime.now().year
            subject = "Password Reset Request – Dunis Technologies"

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background: #f7f9fb;
                        color: #333;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 40px auto;
                        background: #fff;
                        border-radius: 10px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                        padding: 30px;
                    }}
                    h2 {{
                        color: #d9534f;
                        text-align: center;
                        margin-bottom: 20px;
                    }}
                    p {{
                        line-height: 1.7;
                        font-size: 15px;
                    }}
                    .btn {{
                        display: inline-block;
                        background: #d9534f;
                        color: #fff !important;
                        text-decoration: none;
                        padding: 12px 24px;
                        border-radius: 6px;
                        font-weight: 600;
                        margin: 25px 0;
                    }}
                    .footer {{
                        font-size: 12px;
                        color: #888;
                        text-align: center;
                        border-top: 1px solid #eee;
                        padding-top: 15px;
                        margin-top: 30px;
                    }}
                    a {{ color: #d9534f; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Password Reset</h2>
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Click the button below to continue:</p>
                    <div style="text-align:center;">
                        <a href="{reset_url}" class="btn">Reset Password</a>
                    </div>
                    <p>If the button doesn’t work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all;">{reset_url}</p>
                    <p>If you didn’t request this, please ignore this email. This link expires in 1 hour.</p>
                    <div class="footer">
                        © {current_year} Dunis Technologies Limited. All rights reserved.
                    </div>
                </div>
            </body>
            </html>
            """

            msg = Message(
                subject=subject,
                recipients=[email],
                html=html_body,
                sender=app.config['MAIL_DEFAULT_SENDER']
            )

            mail.send(msg)
            app.logger.info(f"Password reset email sent to {email}")
            return True
    except Exception as e:
        app.logger.error(f"Failed to send reset email: {str(e)}")
        return False

