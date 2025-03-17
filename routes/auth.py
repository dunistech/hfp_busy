import traceback
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils import generate_reset_token, get_db_connection, send_reset_email, verify_reset_token

bp = Blueprint('auth', __name__)

# Add other authentication routes...
### Routes for User and Business Registration ###
@bp.route('/register_user', methods=['GET', 'POST'])
def register_user():
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        phone = request.form['phone']
        
        """ ======= Business Related Info ============ """
        category = request.form['category']
        shop_no = request.form['shop_no']
        block_num = request.form['block_num']
        description = request.form['description']
        website_url = request.form['website_url']
        social_handles = request.form['social_handles']
        # user_id = session.get('user_id')
        
        # 
        # Handle form submission and save data
        # phone = request.form.get('phone')
        # email = request.form.get('email')
        # website_url = request.form.get('website_url')
        # social_handles = request.form.get('social_handles')
        # description = request.form.get('description')
        # name = request.form.get('name')
        # shop_no = request.form.get('shop_no')
        # block_num = request.form.get('block_num')
        # category = request.form.get('category')
        # username = request.form.get('username')
        # password = request.form.get('password')
        # 
        
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(buffered=True)
                
                # Check if username or email already exists in user_registration_requests or users
                cur.execute("SELECT * FROM user_registration_requests WHERE username = %s OR email = %s", (username, email))
                existing_user_request = cur.fetchone()
                
                cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
                existing_user = cur.fetchone()

                if existing_user_request or existing_user:
                    flash("Username or email already exists. Please try again with different credentials.", 'error')
                    return redirect(url_for('auth.register_user'))

                else:                    # Insert the registration request into user_registration_requests table
                    cur.execute("""
                        INSERT INTO user_registration_requests (username, password, email, name, phone)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (username, generate_password_hash(password, method='pbkdf2:sha256'), email, name, phone))
                    
                    # conn.commit()
                    # flash("Registration request submitted successfully. Your account will be created after admin approval.", 'success')
                    # Insert the new user into the users table
                    cur.execute(
                        "INSERT INTO users (username, email, password, name, phone, is_admin, is_approved) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (username, email, generate_password_hash(password, method='pbkdf2:sha256'), name, phone, False, False)
                    )
                    
                    conn.commit()
                    flash("Registration request submitted successfully. Your account will be created after admin approval.", 'success')
                    
                # Get A User & Insert A new business registration request into the database also with user details
                # Check if username or email already exists in user_registration_requests or users
                # cur.execute("SELECT * FROM user_registration_requests WHERE username = %s OR email = %s", (username, email))
                # existing_user_request = cur.fetchone()
                
                cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
                existing_user = cur.fetchone()

                if existing_user:
                    user_id = existing_user[0]
                    cur.execute("""
                        INSERT INTO business_registration_requests 
                        (business_name, shop_no, phone_number, block_num, category, description, user_id, email, website_url, social_handles)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, shop_no, phone, block_num, category, description, user_id, email, website_url, social_handles) )
                    conn.commit()
                    flash("Business Registration request submitted successfully. You will be able to login after admin approval.", 'success')
                    return redirect(url_for('index.home'))
                
                else:
                    
                    return jsonify({"error":"Could not save into business_registration_requests"})
                
                return redirect(url_for('index.home'))
            
            except Exception as e:
                traceback.print_exc()
                print(f"Database error: {e}")
                flash("Error occurred during registration.", 'error')
            finally:
                conn.close()
        else:
            flash("Could not connect to the database.", 'error')
            
    # return render_template('register_user.html')
    # If GET request, render the form with empty fields
    return render_template('register_user.html', 
                           phone='', email='', website_url='', 
                           social_handles='', description='', 
                           name='', shop_no='', block_num='', 
                           category='', username='', password='')  # Assume get_categories() fetches categories

@bp.route('/register_business', methods=['GET', 'POST'])
def register_business():
    
    # if 'user_logged_in' not in session:
    #     return redirect(url_for('auth.user_login'))

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
            flash(f"Database error: {e}", 'error')
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('user_business_profile'))

    return render_template('register_business.html')

@bp.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        
        if conn:
            try:
                cur = conn.cursor()
                
                # Check if user exists in users table
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cur.fetchone()
                
                if user:
                    # User exists in users table
                    stored_password_hash = user[3]  # Assuming password is in the 4th column
                    is_approved = user[5]  # Assuming is_approved is in the 6th column
                    is_suspended = user[7]  # Assuming suspended is in the 8th column
                    
                    # Check if the user's account is suspended
                    if is_suspended:
                        flash("Your account is suspended. Please contact the admin.", 'error')
                    
                    # Check if the user's account is not approved (i.e., not activated)
                    elif not is_approved:
                        flash("Your account is not activated yet. Please check your email for the activation link.", 'error')
                    
                    # Check if the provided password matches the stored password hash
                    elif check_password_hash(stored_password_hash, password):
                        session['user_logged_in'] = True
                        session['user_id'] = user[0]  # Store user_id in the session
                        session['username'] = user[1]
                        session['avatar'] = user[6]
                        
                        # for x in user:
                        #     print(x)
                            
                        flash("Login successful.", 'success')
                        return redirect(url_for('user.update_profile'))
                    else:
                        flash("Invalid credentials. Please check your password.", 'error')
                
                else:
                    # User not found in users table, check registration requests
                    cur.execute("SELECT * FROM user_registration_requests WHERE username = %s", (username,))
                    registration_request = cur.fetchone()
                    
                    if registration_request:
                        flash("Your account is not approved yet. Please wait for admin approval.", 'error')
                    else:
                        flash("Invalid credentials. User does not exist.", 'error')
                
                cur.close()
                conn.close()
            except Exception as e:
                flash(f"Error occurred during login: {e}", 'error')
    return render_template('user_login.html')


@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            token = generate_reset_token(user[0])
            send_reset_email(email, token)
            flash('An email with a password reset link has been sent to your email address.', 'info')
            return redirect(url_for('auth.user_login'))
        else:
            flash('Email address not found.', 'error')
        

    return render_template('forgot_password.html')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = verify_reset_token(token)
    if not user_id:
        flash('The reset link is invalid or has expired.', 'error')
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
        return redirect(url_for('auth.user_login'))

    return render_template('reset_password.html')

@bp.route('/logout')
def logout():
    # print("Session before logout:", session)  # Debug: Print session variables
    session.clear()
   
    flash('No one is logged in.', 'warning')
    return redirect(url_for('index.home'))
