import traceback
from flask import Blueprint, request, render_template, redirect, session, url_for, flash
from utils import serializer, get_db_connection, upload_file
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('admin', __name__)

# Add other admin-related routes...
### Admin Routes ###
@bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM admin WHERE username = %s", (username,))
                
                admin = cur.fetchone()
                cur.close()
                conn.close()

                if admin and check_password_hash(admin[3], password):  # Assuming password is in the 3rd column
                    session['admin_logged_in'] = True
                    
                    # Loop through admin info and save each column in the session
                    column_names = ['admin_id', 'admin_username', 'admin_email', 'admin_profile_pic']
                    for i, column_name in enumerate(column_names):
                        session[column_name] = admin[i]
                    
                    flash('Admin has logged in successfully.', 'success')
                    return redirect(url_for('admin.admin_dashboard'))
                else:
                    flash("Invalid credentials.", 'error')
            except Exception as e:
                print(f"Database error: {e}")
                flash("Error occurred during login.", 'error')
    
    return render_template('admin_login.html')

@bp.route('/admin/update_profile', methods=['GET', 'POST'])
def update_admin_profile():
    
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))
    
    admin_id = session.get('admin_id')
    conn = get_db_connection()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_password = request.form['new_password']
        email = request.form['email']
        file = request.files.get('profile_pic')

        try:
            cur = conn.cursor()
            
            # Check current password if new password is being updated
            if new_password:
                cur.execute("SELECT password FROM admin WHERE id = %s", (admin_id,))
                current_password_hash = cur.fetchone()[0]
                
                if not check_password_hash(current_password_hash, password):
                    flash('Current password is incorrect.', 'error')
                else:
                    hashed_password = generate_password_hash(new_password)
                    cur.execute("""
                        UPDATE admin
                        SET password = %s
                        WHERE id = %s
                    """, (hashed_password, admin_id))
                    conn.commit()

            # Update username and email if provided
            if username:
                cur.execute("""
                    UPDATE admin
                    SET username = %s
                    WHERE id = %s
                """, (username, admin_id))
                conn.commit()
                
            if email:
                cur.execute("""
                    UPDATE admin
                    SET email = %s
                    WHERE id = %s
                """, (email, admin_id))
                conn.commit()
            
            # Check if the admin wants to update the profile picture
            if file and file.filename:
                profile_pic_url = upload_file(file)
                if profile_pic_url:
                    cur.execute("""
                        UPDATE admin
                        SET profile_pic = %s
                        WHERE id = %s
                    """, (profile_pic_url, admin_id))
                    conn.commit()
                    session['admin_profile_pic'] = profile_pic_url


            flash('Profile updated successfully.', 'success')
            cur.close()
        except Exception as e:
            flash(f"Database error: {e}", 'error')
 

    # Fetch current admin data
    cur = conn.cursor()
    cur.execute("SELECT * FROM admin WHERE id = %s", (admin_id,))
    admin = cur.fetchone()
    cur.close()
    conn.close()

    return render_template('admin_update_profile.html', admin=admin)

@bp.route('/admin@bp.', methods=['GET'])
def admin_profile():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))
    
    admin_id = session.get('admin_id')
    conn = get_db_connection()

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin WHERE id = %s", (admin_id,))
        admin = cur.fetchone()
        cur.close()
    except Exception as e:
        flash(f"Database error: {e}", 'error')
    finally:
        conn.close()

    if admin:
        return render_template('admin_profile.html', admin=admin)
    else:
        flash('Admin profile not found.', 'error')
        return redirect(url_for('admin.admin_login'))

@bp.route('/admin_dashboard')
def admin_dashboard():
    
    if 'admin_logged_in' not in session or "admin_id" not in session:
        return redirect(url_for('admin.admin_login'))

    conn = get_db_connection()
    user_requests = []
    business_requests = []
    users = []
    claim_requests = []
    pending_user_registration_request_count = 0
    pending_business_registration_requests_count = 0
    pending_approved_user_count = 0
    pending_claim_requests_count = 0  # New variable for claim requests count

    if conn:
        try:
            cur = conn.cursor(buffered=True)
            
            # Fetch pending claim requests
            cur.execute("""
                SELECT cr.id, b.business_name, u.username, cr.phone_number, cr.email, cr.category, cr.description, cr.created_at
                FROM claim_requests cr
                JOIN businesses b ON cr.business_id = b.id
                JOIN users u ON cr.user_id = u.id
                WHERE cr.reviewed = FALSE
            """)
            claim_requests = cur.fetchall()
            
            # Count pending claim requests
            cur.execute("SELECT COUNT(*) FROM claim_requests WHERE reviewed = FALSE")
            pending_claim_requests_count = cur.fetchone()[0]

            # Fetch admin profile picture URL
            admin_id = session.get('admin_id')
            cur.execute("SELECT profile_pic FROM admin WHERE id = %s", (admin_id,))
            
            # Fetch all user registration requests
            cur.execute("SELECT * FROM user_registration_requests")
            user_requests = cur.fetchall()
            
            # Fetch all business registration requests
            cur.execute("SELECT * FROM business_registration_requests")
            business_requests = cur.fetchall()
            
            # Fetch all users
            cur.execute("SELECT * FROM users")
            users = cur.fetchall()

            # Count pending user registration requests
            cur.execute("SELECT COUNT(*) FROM user_registration_requests WHERE processed = FALSE")
            pending_user_registration_request_count = cur.fetchone()[0]
            
            # Count pending business registration requests
            cur.execute("SELECT COUNT(*) FROM business_registration_requests WHERE processed = FALSE")
            pending_business_registration_requests_count = cur.fetchone()[0]
            
            # Count unapproved users
            cur.execute("SELECT COUNT(*) FROM users WHERE is_approved = FALSE")
            pending_approved_user_count = cur.fetchone()[0]
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Database error: {e}")
            flash("Error occurred during dashboard retrieval.", 'error')
        finally:
            conn.close()

    return render_template(
        'admin_dashboard.html', 
        user_requests=user_requests, 
        business_requests=business_requests,  
        users=users, 
        pending_user_registration_request_count=pending_user_registration_request_count,
        pending_business_registration_requests_count=pending_business_registration_requests_count,
        pending_approved_user_count=pending_approved_user_count,
    #    profile_pic_path=profile_pic_path,
        claim_requests=claim_requests,
        pending_claim_requests_count=pending_claim_requests_count)  # Pass count to template

# 

@bp.route('/process_user_registration', methods=['POST'])
def process_user_registration():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    name = request.form['name']
    phone = request.form['phone']

    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()

            # Check if the user already exists
            cur.execute(
                "SELECT COUNT(*) FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            user_exists = cur.fetchone()[0] > 0

            if not user_exists:
                # Insert the new user into the users table
                cur.execute(
                    "INSERT INTO users (username, email, password, name, phone, is_admin, is_approved) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (username, email, password, name, phone, False, False)
                )
                
            # Mark the user registration request as processed
            cur.execute(
                "UPDATE user_registration_requests SET processed = TRUE WHERE username = %s",
                (username,)
            )

            conn.commit()
            flash('User registered successfully.', 'success')

        except Exception as e:
            print(f"Database error: {e}")
            flash('Error processing user registration.', 'error')
        finally:
            cur.close()
            conn.close()

    return redirect(url_for('admin.admin_dashboard'))


@bp.route('/approve_user', methods=['POST'])
def approve_user():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin.admin_login'))

    username = request.form['username']

    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(buffered=True)

            # Get the user's email and registration request ID from user_registration_requests
            cur.execute("SELECT id, email FROM user_registration_requests WHERE username = %s", (username,))
            registration_request = cur.fetchone()

            if registration_request:
                registration_request_id = registration_request[0]
                email = registration_request[1]

                # # Create the activation token
                token = serializer.dumps(email, salt='email-activate')
                
                # # Send activation email
                # activation_url = url_for('activate_account', token=token, _external=True)
                # msg = Message('Activate Your Account', sender='Dunistech Codersrich@gmail.com', recipients=[email])
                # msg.body = f"Please click the link to activate your account: {activation_url}"
                # mail.send(msg)

                # Update the user to set is_approved to TRUE, is_activated to FALSE, and associate registration_request_id
                cur.execute("""
                    UPDATE users 
                    SET is_approved = TRUE, is_activated = TRUE, activation_token = %s, registration_request_id = %s 
                    WHERE username = %s
                """, (token, registration_request_id, username))
                
                conn.commit()
                
                # Notify the admin that an email has been sent
                flash(f'User approved. Activation email sent to {email}.', 'success')
            else:
                flash('User registration request not found.', 'error')
                
        except Exception as e:
            traceback.print_exc()
            flash(f'Database error: {e}', 'error')
        finally:
            cur.close()
            conn.close()

    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/activate_account/<token>')
def activate_account(token):
    try:
        email = s.loads(token, salt='email-activate', max_age=3600)  # Token expires after 1 hour
    except SignatureExpired:
        flash('The activation link has expired.', 'error')
        return redirect(url_for('index.home'))
    except BadSignature:
        flash('The activation link is invalid.', 'error')
        return redirect(url_for('index.home'))

    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Update the user's activation status
            cur.execute("UPDATE users SET is_activated = TRUE WHERE email = %s", (email,))
            conn.commit()
            flash('Account activated successfully. You can now log in.', 'success')
        except Exception as e:
            print(f"Database error: {e}")
            flash('Error activating account.', 'error')
        finally:
            cur.close()
            conn.close()

    return redirect(url_for('auth.user_login'))

@bp.route('/admin/users')
def admin_users():
    if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
        return redirect(url_for('auth.user_login'))
    
    conn = get_db_connection()
    users = []
    user_requests = []
    business_requests = []
    pending_user_registration_request_count = 0
    pending_business_registration_requests_count = 0
    pending_approved_user_count = 0
    
    if conn:
        try:
            cur = conn.cursor()
            admin_id = session.get('admin_id')
             # Fetch admin profile picture URL
            cur.execute("SELECT profile_pic FROM admin WHERE id = %s", (admin_id,))
            profile_pic_path = cur.fetchone()[0]
            
            cur.execute("SELECT id, username, email, is_admin, is_approved, suspended FROM users")
            users = cur.fetchall()
            
            # Fetch all user registration requests
            cur.execute("SELECT * FROM user_registration_requests")
            user_requests = cur.fetchall()
            
            # Fetch all business registration requests
            cur.execute("SELECT * FROM business_registration_requests")
            business_requests = cur.fetchall()
            
            # Fetch all users
            cur.execute("SELECT * FROM users")
            users = cur.fetchall()

            # Count pending user registration requests
            cur.execute("SELECT COUNT(*) FROM user_registration_requests WHERE processed = FALSE")
            pending_user_registration_request_count = cur.fetchone()[0]
            
            # Count pending business registration requests
            cur.execute("SELECT COUNT(*) FROM business_registration_requests WHERE processed = FALSE")
            pending_business_registration_requests_count = cur.fetchone()[0]
            
            # Count unapproved users
            cur.execute("SELECT COUNT(*) FROM users WHERE is_approved = FALSE")
            pending_approved_user_count = cur.fetchone()[0]
            cur.close()
        except Exception as e:
            flash(f"Database error: {e}", 'error')
        finally:
            conn.close()
    
    return render_template('admin_users.html', users=users, user_requests=user_requests, 
                           business_requests=business_requests,  
                           pending_user_registration_request_count=pending_user_registration_request_count,
                           pending_business_registration_requests_count=pending_business_registration_requests_count,
                           pending_approved_user_count=pending_approved_user_count, profile_pic_path=profile_pic_path)
    

@bp.route('/admin/suspend_user/<int:user_id>')
def suspend_user(user_id):
    if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
        return redirect(url_for('auth.user_login'))
    
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET suspended = TRUE WHERE id = %s", (user_id,))
            conn.commit()
            cur.close()
            flash("User account suspended.", 'success')
        except Exception as e:
            flash(f"Database error: {e}", 'error')
        finally:
            conn.close()
    
    return redirect(url_for('admin.admin_users'))

@bp.route('/admin/unsuspend_user/<int:user_id>')
def unsuspend_user(user_id):
    if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
        return redirect(url_for('auth.user_login'))
    
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET suspended = FALSE WHERE id = %s", (user_id,))
            conn.commit()
            cur.close()
            flash("User account unsuspended.", 'success')
        except Exception as e:
            flash(f"Database error: {e}", 'error')
        finally:
            conn.close()
    
    return redirect(url_for('admin.admin_users'))

@bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
            return redirect(url_for('auth.user_login'))

        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()

                # Fetch the registration_request_id
                cur.execute("SELECT registration_request_id FROM users WHERE id = %s", (user_id,))
                registration_request_id = cur.fetchone()

                # Delete related claim requests
                cur.execute("DELETE FROM claim_requests WHERE user_id = %s", (user_id,))

                # Delete the user
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))

                # Manually delete the related registration request if the cascade didn't work
                if registration_request_id and registration_request_id[0]:
                    # print("registration_request_id --", registration_request_id, registration_request_id[0])
                    cur.execute("DELETE FROM user_registration_requests WHERE id = %s", (registration_request_id[0],))

                conn.commit()
                cur.close()
                flash('User and associated data deleted successfully.', 'success')
            except Exception as e:
                traceback.print_exc()
                flash(f"Database error: {e}", 'error')
            finally:
                conn.close()

        return redirect(url_for('admin.admin_users'))
    except Exception as e:
        return f"{e}"

@bp.route('/admin/user/<int:user_id>/businesses')
def view_user_businesses(user_id):
    
    if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
        return redirect(url_for('auth.user_login'))
    
    conn = get_db_connection()
    businesses = []
    user_name = None

    if conn:
        try:
            cur = conn.cursor()
            admin_id = session.get('admin_id')
             # Fetch admin profile picture URL
            cur.execute("SELECT profile_pic FROM admin WHERE id = %s", (admin_id,))
            profile_pic_path = cur.fetchone()[0]
            
            # Query to fetch businesses along with the owner's username
            cur.execute("""
                SELECT b.id, b.business_name, b.shop_no, b.phone_number, b.description, b.is_subscribed, b.email, u.username
                FROM businesses b
                JOIN users u ON b.owner_id = u.id
                WHERE b.owner_id = %s
            """, (user_id,))
            
            businesses = cur.fetchall()
            
            # Extract the username from one of the fetched businesses (assuming all have the same owner)
            if businesses:
                user_name = businesses[0][7]  # Assuming the username is at index 7 in the result
            
            cur.close()
        except Exception as e:
            flash(f"Database error: {e}", 'error')
        finally:
            conn.close()

    return render_template('admin_user_businesses.html', businesses=businesses, user_id=user_id, user_name=user_name, profile_pic_path=profile_pic_path)


@bp.route('/admin/business/<int:business_id>/update', methods=['GET', 'POST'])
def update_business(business_id):
    if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
        return redirect(url_for('auth.user_login'))
    
    conn = get_db_connection()
    user_id = None

    if request.method == 'POST':
        business_name = request.form['business_name']
        shop_no = request.form['shop_no']
        phone_number = request.form['phone_number']
        description = request.form['description']
        email = request.form['email']
        category = request.form['category']
        is_subscribed = request.form.get('is_subscribed') == 'on'

        try:
            cur = conn.cursor()
            # Get the user_id before updating the business
            cur.execute("SELECT owner_id FROM businesses WHERE id = %s", (business_id,))
            user_id = cur.fetchone()[0]

            # Update the business details
            cur.execute("""
                UPDATE businesses
                SET business_name = %s, shop_no = %s, phone_number = %s, description = %s, email = %s, is_subscribed = %s, category = %s
                WHERE id = %s
            """, (business_name, shop_no, phone_number, description, email, is_subscribed, category, business_id))
            conn.commit()
            flash('Business updated successfully.', 'success')
            cur.close()
        except Exception as e:
            flash(f"Database error: {e}", 'error')
        finally:
            conn.close()

        # Redirect to the user's business view route, passing the user_id
        # return redirect(url_for(request.referrer))
        return redirect(url_for('business.businesses'))
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM businesses WHERE id = %s", (business_id,))
    business = cur.fetchone()
    user_id = business[1]  # Assuming owner_id is the second column in the businesses table
    cur.close()
    conn.close()

    if business:
        return render_template('admin_update_business.html', business=business)
    else:
        flash('Business not found.', 'error')
        return redirect(url_for('admin.view_user_businesses', user_id=user_id))


@bp.route('/admin/business/<int:business_id>/delete', methods=['POST', 'GET'])
def delete_business(business_id):
    if 'admin_logged_in' not in session or not session.get('admin_logged_in'):
        return redirect(url_for('auth.user_login'))
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Delete related claim requests
        cur.execute("DELETE FROM claim_requests WHERE business_id = %s", (business_id,))

        
        # Delete business data from related tables first
        cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))
        
        # Optionally, delete the business registration request
        cur.execute("DELETE FROM business_registration_requests WHERE business_name = (SELECT business_name FROM businesses WHERE id = %s)", (business_id,))
        
        # Finally, delete the business
        cur.execute("DELETE FROM businesses WHERE id = %s", (business_id,))
        
        conn.commit()
        flash('Business and related registration request deleted successfully.', 'success')
    except Exception as e:
        flash(f"Database error: {e}", 'error')
        print(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('business.businesses'))

## Delete from Users and user_registration_requests Table ##
@bp.route("/delete/<int:id_number>")
def delete(id_number):
    # we use this syntax <int:id_number> to get an interger or number, NOTE: the int is required,
    #but the id_number can be name anything
    
    connection = get_db_connection()
    mycusor = connection.cursor()
    mycusor.execute('DELETE FROM user_form WHERE id = %s', (id_number,))
    
    connection.commit()
    mycusor.close()
    connection.close()
    
    return redirect(url_for('fetch'))
## Delete from Users and user_registration_requests Table 