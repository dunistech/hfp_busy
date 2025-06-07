import traceback
from flask import (current_app as app, Blueprint, jsonify, request, render_template, redirect, url_for, flash, session)
from werkzeug.security import generate_password_hash, check_password_hash
from utils import (generate_token, verify_token, send_verification_email, get_db_connection, send_reset_email, verify_reset_token)

from markupsafe import Markup
import re
from datetime import datetime, timedelta
import secrets
import string

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect if already logged in
    
    if 'user_id' in session:
        return redirect(get_redirect_url_based_on_role(session.get('role')))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # print(generate_password_hash(password))
        try:
            conn = get_db_connection()
            with conn.cursor(dictionary=True) as cur:
                # Check in unified users table
                cur.execute("""SELECT * FROM users WHERE username = %s OR email = %s """, (username, username))
                user = cur.fetchone()

                if not user:
                    flash("Invalid credentials. User not found.", 'danger')
                    return redirect(url_for('auth.login'))
                
                # Handle unverified accounts
                if not user['is_verified']:
                    flash(Markup(
                        f"Account not verified. <a href='{url_for('auth.resend_verification', username=user['username'])}'>"
                        "Resend verification email</a>"
                    ), 'warning')
                    return redirect(url_for('auth.login'))
                
                # Verify password
                if not check_password_hash(user['password'], password):
                    flash(f"Invalid credentials. Please check your password. {username, password}", 'danger')
                    return redirect(url_for('auth.login'))
                
                # Successful login
                setup_user_session(user)
                flash("Login successful!", 'success')
                return redirect(get_redirect_url_based_on_role(user['role']))
                
        except Exception as e:
            traceback.print_exception(e)
            app.logger.error(f"Login error: {str(e)}")
            flash(f"{e}, An error occurred during login. Please try again.", 'danger')
        
        finally:
            if conn:
                conn.close()
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    
    # Flash a success message
    flash('You have been successfully logged out.', 'success')
    
    # Redirect to home page
    return redirect(request.referrer)

def setup_user_session(user):
    """Set up session variables for logged in user"""
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['email'] = user['email']
    session['role'] = user['role']
    session['is_verified'] = user['is_verified']
    session['avatar'] = user.get('avatar_url', '')
    session['last_login'] = datetime.now().isoformat()

def get_redirect_url_based_on_role(role):
    """Determine redirect URL based on user role"""
    role_redirects = {
        'admin': 'user.profile',
        'manager': 'admin.dashboard',
        'user': 'user.profile'
    }

    return url_for(role_redirects.get(role, 'main.index'))

@bp.route('/resend-verification/<string:username>')
def resend_verification(username):
    try:
        conn = get_db_connection()
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            
            if not user:
                flash("User not found.", 'danger')
            elif user['is_verified']:
                flash("Account is already verified.", 'info')
            else:
                # Generate new token and send email
                token = generate_token(user['email'])
                # send_verification_email(app, user.email, token)
                sent = send_verification_email(app, user['email'], token)
                if sent:
                    flash(f"Verification email resent to {user['email']} sent: {sent}. Please check your inbox.", 'success')
                else:
                    flash(f"Could not send Verification mail to {user['email']}. sent: {sent}", 'warning')
                
    except Exception as e:
        app.logger.error(f"Resend verification error: {str(e)}")
        traceback.print_exception(e)
        flash(f"Failed to resend verification email.", 'danger')
        
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('auth.login'))

@bp.route('/verify-email/<token>')
def verify_email(token):
    conn = None
    try:
        # First verify the token itself
        email = verify_token(token)
        if not email:
            flash('Invalid or expired verification link', 'danger')
            return redirect(url_for('auth.login'))

        conn = get_db_connection()
        with conn.cursor(dictionary=True) as cur:
            # Find user with this email
            cur.execute("""
                SELECT id, is_verified 
                FROM users 
                WHERE email = %s
            """, (email,))
            user = cur.fetchone()

            if not user:
                flash('No account found with this email', 'danger')
                return redirect(url_for('auth.register'))

            if user['is_verified']:
                flash('Account is already verified', 'info')
                return redirect(url_for('auth.login'))

            # Mark as verified
            cur.execute("""
                UPDATE users 
                SET is_verified = TRUE, 
                    verification_token = NULL,
                    token_expires_at = NULL,
                    updated_at = NOW()
                WHERE email = %s
            """, (email,))
            conn.commit()

            flash('Email verification successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Email verification error: {str(e)}")
        flash('An error occurred during verification', 'danger')
    
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('auth.login'))

@bp.route('/verify-email2/<token>')
def verify_email2(token):
    try:
        conn = get_db_connection()
        with conn.cursor(dictionary=True) as cur:
            # Find user with this token
            cur.execute("""
                SELECT id, email, token_expires_at 
                FROM users 
                WHERE verification_token = %s 
                AND is_verified = FALSE
            """, (token,))
            user = cur.fetchone()

            if not user:
                flash('Invalid or expired verification link', 'danger')
                return redirect(url_for('auth.login'))

            # Check if token is expired
            if datetime.now() > user['token_expires_at']:
                flash('Verification link has expired', 'danger')
                return redirect(url_for('auth.login'))

            # Mark as verified
            cur.execute("""
                UPDATE users 
                SET is_verified = TRUE, 
                    verification_token = NULL,
                    token_expires_at = NULL,
                    updated_at = NOW()
                WHERE id = %s
            """, (user['id'],))
            conn.commit()

            flash('Email verification successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Email verification error: {str(e)}")
        flash('An error occurred during verification', 'danger')
    
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('auth.login'))


# sign-up
@bp.route('/register', methods=['GET', 'POST'])  # Changed to match your template
def register():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        phone = request.form.get('phone')
        password = request.form.get('password')

        # Validation checks
        errors = validate_registration(username, email, password, phone)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('auth.register'))

        try:
            conn = get_db_connection()
            with conn.cursor(dictionary=True) as cur:
                # Check if username or email already exists
                cur.execute(""" SELECT id FROM users WHERE username = %s OR email = %s OR phone = %s
                    LIMIT 1
                """, (username, email, phone))
                
                if cur.fetchone():
                    flash('Username or email already exists', 'danger')
                    return redirect(url_for('auth.register'))

                # Create verification token
                verification_token = generate_token(email)
                token_expires = datetime.now() + timedelta(hours=24)

                # Insert new user
                cur.execute("""
                    INSERT INTO users (
                        username, 
                        email, 
                        phone,
                        password, 
                        verification_token,
                        token_expires_at,
                        role,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    username,
                    email,
                    phone,
                    generate_password_hash(password),
                    verification_token,
                    token_expires,
                    'user'  # Default role
                ))
                user_id = cur.lastrowid
                conn.commit()

                # Send verification email
                send_verification_email(app, email, verification_token)
                
                
                flash('Registration successful! Please check your email to verify your account.', 'success')
                return redirect(url_for('auth.login'))

        except Exception as e:
            conn.rollback()
            app.logger.error(f"Registration error: {str(e)}")
            flash(f'{e} An error occurred during registration. Please try again.', 'danger')
        
        finally:
            if conn:
                conn.close()

    return render_template('auth/register.html')

def validate_registration(username, email, password, phone):
    """Validate registration form data"""
    errors = []
    
    # Username validation
    if not username or len(username) < 3:
        errors.append('Username must be at least 3 characters long')
    elif not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append('Username can only contain letters, numbers and underscores')
    
    # Email validation
    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        errors.append('Please enter a valid email address')
    
    if not phone or len(phone) < 10:
        errors.append('Please enter a valid phone number')
    
    # Password validation
    if not password or len(password) < 4:
        errors.append('Password must be at least 8 characters long')

    return errors

### Routes for User and Business Registration ###
# @bp.route('/register_user', methods=['GET', 'POST'])
# def register_user():
    
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         email = request.form['email']
#         name = request.form['name']
#         phone = request.form['phone']
        
#         """ ======= Business Related Info ============ """
#         category = request.form['category']
#         shop_no = request.form['shop_no']
#         block_num = request.form['block_num']
#         description = request.form['description']
#         website_url = request.form['website_url']
#         social_handles = request.form['social_handles']
#         # user_id = session.get('user_id')
        
#         # 
#         # Handle form submission and save data
#         # phone = request.form.get('phone')
#         # email = request.form.get('email')
#         # website_url = request.form.get('website_url')
#         # social_handles = request.form.get('social_handles')
#         # description = request.form.get('description')
#         # name = request.form.get('name')
#         # shop_no = request.form.get('shop_no')
#         # block_num = request.form.get('block_num')
#         # category = request.form.get('category')
#         # username = request.form.get('username')
#         # password = request.form.get('password')
#         # 
        
#         conn = get_db_connection()
#         if conn:
#             try:
#                 cur = conn.cursor(buffered=True)
                
#                 # Check if username or email already exists in user_registration_requests or users
#                 cur.execute("SELECT * FROM user_registration_requests WHERE username = %s OR email = %s", (username, email))
#                 existing_user_request = cur.fetchone()
                
#                 cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
#                 existing_user = cur.fetchone()

#                 if existing_user_request or existing_user:
#                     flash("Username or email already exists. Please try again with different credentials.", 'danger')
#                     return redirect(url_for('auth.register'))

#                 else:                    # Insert the registration request into user_registration_requests table
#                     cur.execute("""
#                         INSERT INTO user_registration_requests (username, password, email, name, phone)
#                         VALUES (%s, %s, %s, %s, %s);
#                     """, (username, generate_password_hash(password, method='pbkdf2:sha256'), email, name, phone))
                    
#                     # conn.commit()
#                     # flash("Registration request submitted successfully. Your account will be created after admin approval.", 'success')
#                     # Insert the new user into the users table
#                     cur.execute(
#                         "INSERT INTO users (username, email, password, name, phone, is_admin, is_approved) VALUES (%s, %s, %s, %s, %s, %s, %s)",
#                         (username, email, generate_password_hash(password, method='pbkdf2:sha256'), name, phone, False, False)
#                     )
                    
#                     conn.commit()
#                     flash("Registration request submitted successfully. Your account will be created after admin approval.", 'success')
                    
#                 # Get A User & Insert A new business registration request into the database also with user details
#                 # Check if username or email already exists in user_registration_requests or users
#                 # cur.execute("SELECT * FROM user_registration_requests WHERE username = %s OR email = %s", (username, email))
#                 # existing_user_request = cur.fetchone()
                
#                 cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
#                 existing_user = cur.fetchone()

#                 if existing_user:
#                     user_id = existing_user[0]
#                     cur.execute("""
#                         INSERT INTO business_registration_requests 
#                         (business_name, shop_no, phone_number, block_num, category, description, user_id, email, website_url, social_handles)
#                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#                     """, (name, shop_no, phone, block_num, category, description, user_id, email, website_url, social_handles) )
#                     conn.commit()
#                     flash("Business Registration request submitted successfully. You will be able to login after admin approval.", 'success')
#                     return redirect(url_for('index.home'))
                
#                 else:
                    
#                     return jsonify({"error":"Could not save into business_registration_requests"})
                
#                 return redirect(url_for('index.home'))
            
#             except Exception as e:
#                 traceback.print_exc()
#                 print(f"Database error: {e}")
#                 flash("Error occurred during registration.", 'danger')
#             finally:
#                 conn.close()
#         else:
#             flash("Could not connect to the database.", 'danger')
            
#     # return render_template('register_user.html')
#     # If GET request, render the form with empty fields
#     return render_template(
#         'register_user.html', 
#         phone='', email='', website_url='', 
#         social_handles='', description='', 
#         name='', shop_no='', block_num='', 
#         category='', username='', password='')  # Assume get_categories() fetches categories

@bp.route('/register_business', methods=['GET', 'POST'])
def register_business():
    
    # if 'user_id' not in session:
    #     return redirect(url_for('auth.login'))

    if request.method == 'POST':
        
        """  NEW """
        website_url = request.form['website_url']
        social_handles = request.form['social_handles']
        """  """
        business_name = request.form['business_name']
        shop_no = request.form['shop_no']
        phone_number = request.form['phone_number']
        block_num = request.form['block_num']
        category = request.form['category']
        description = request.form['description']
        email = request.form['email']  # Get email address
        user_id = session.get('user_id')
        
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Insert the new business registration request into the database
            cur.execute("""
                INSERT INTO business_registration_requests 
                (business_name, shop_no, phone_number, block_num, category, description, user_id, email, website_url, social_handles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (business_name, shop_no, phone_number, block_num, category, description, user_id, email, website_url, social_handles) )

            conn.commit()
            
            flash("Business registration request submitted successfully!", 'success')
            
        except Exception as e:
            flash(f"Database error: {e}", 'danger')
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('user.user_business_profile'))

    return render_template('register_business.html')

# @bp.route('/user_login', methods=['GET', 'POST'])
# def user_login():
#     print(session['user_logged_in'])
#     if 'user_id' in session:
#         return redirect(url_for('user.update_profile')) 
        
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         conn = get_db_connection()
        
#         if conn:
#             try:
#                 cur = conn.cursor(dictionary=True)
                
#                 # Check if user exists in users table
#                 cur.execute("SELECT * FROM users WHERE username = %s", (username,))
#                 user = cur.fetchone()
                
#                 if user:
#                     # User exists in users table
#                     stored_password_hash = user['password']  
#                     is_activated = user['is_activated'] 

#                     # Check if the user's account is suspended
#                     if not is_activated:
#                         flash("Your account is not activated. Check your email for activation link.", 'danger')

#                     # Check if the provided password matches the stored password hash
#                     elif check_password_hash(stored_password_hash, password):
#                         session['user_logged_in'] = True
#                         session['user_id'] = user['user_id']  # Store user_id in the session
#                         session['username'] = user['username']
#                         session['avatar'] = user['avater'] 
                            
#                         flash("Login successful.", 'success')
#                         return redirect(url_for('user.update_profile'))
#                     else:
#                         flash("Invalid credentials. Please check your password.", 'danger')
#                 else:
#                     flash("Invalid credentials. User does not exist.", 'danger')
                
#                 cur.close()
#                 conn.close()

#             except Exception as e:
#                 traceback.print_exception(e)
#     return render_template('user_login.html')

# @bp.route('/forgot_password', methods=['GET', 'POST'])
# def forgot_password():
#     if request.method == 'POST':
#         email = request.form['email']
#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)
#         cur.execute('SELECT id FROM users WHERE email = %s', (email,))
#         user = cur.fetchone()
#         cur.close()
#         conn.close()

#         if user:
#             token = generate_token(user['id'])
#             send_reset_email(email, token)
#             flash('An email with a password reset link has been sent to your email address.', 'info')
#             return redirect(url_for('auth.login'))
#         else:
#             flash('Email address not found.', 'danger')

#     return render_template('forgot_password.html')
@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT id FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            token = generate_token(user['email'])
            # print(f"Generated token: {token}")  # Debugging line
            # send_reset_email(email, token)  # Ensure this function is defined correctly
            send_reset_email(app, email, token)
            flash('An email with a password reset link has been sent to your email address.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Email address not found.', 'danger')

    return render_template('forgot_password.html')


# from flask import request, jsonify

# @bp.route('/forgot_password', methods=['POST'])
# def forgot_password():
#     email = request.form.get('email')
#     user = get_user_by_email(email)  # Replace with your method to get user by email
#     if user:
#         user_id = user.id  # Assuming user object has an id attribute
#         token = generate_token(user_id)  # Generate the reset token
#         send_reset_email(app, email, token)  # Pass the token to the email function
#         return jsonify({"message": "A password reset email has been sent."}), 200
#     return jsonify({"message": "User not found."}), 404

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = verify_reset_token(token)
    if not user_id:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, user_id))
        conn.commit()
        cur.close()
        conn.close()

        flash('Your password has been updated!', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')

