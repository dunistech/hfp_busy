import os, traceback
from flask import Blueprint, current_app as app, request, render_template, redirect, session, url_for, flash
from utils import allowed_file, get_db_connection
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('user', __name__)

# Add other user-related routes...
@bp.route('/add_business')
def add_business():
    return 'add_business page'

@bp.route('/delete_business')
def delete_business():
    return 'user.delete_business page'

@bp.route('/user')
def user():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    conn = get_db_connection()
    businesses = None
    pending_businesses = None
    subscription_plans = None

    if conn:
        try:
            cur = conn.cursor(dictionary=True)

            # Fetch approved businesses
            cur.execute("""
                SELECT id, business_name, shop_no, phone_number, description, is_subscribed, media_type, media_url, category, email
                FROM businesses
                WHERE owner_id = %s
            """, (user_id,))
            businesses = cur.fetchall()
            
            # Fetch pending business requests
            cur.execute("""
                SELECT id, business_name, shop_no, phone_number, description, created_at
                FROM business_registration_requests
                WHERE user_id = %s AND processed = FALSE
            """, (user_id,))
            pending_businesses = cur.fetchall()
            
            # Fetch subscription plans
            cur.execute("""
                SELECT id, plan_name, amount, duration
                FROM subscription_plans
            """)
            subscription_plans = cur.fetchall()
            
            cur.close()
        except Exception as e:
            flash(f"Database error: {e}", 'error')
            
        finally:
            conn.close()

    return render_template('user.html', 
                           businesses=businesses, 
                           pending_businesses=pending_businesses,
                           subscription_plans=subscription_plans)
    
@bp.route('/user_business_profile')
def user_business_profile():
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    conn = get_db_connection()
    businesses = None
    pending_businesses = None
    subscription_plans = None

    if conn:
        try:
            cur = conn.cursor()

            # Fetch approved businesses
            cur.execute("""
                SELECT id, business_name, shop_no, phone_number, description, is_subscribed, media_type, media_url, category, email
                FROM businesses
                WHERE owner_id = %s
            """, (user_id,))
            businesses = cur.fetchall()
            
            # Fetch pending business requests
            cur.execute("""
                SELECT id, business_name, shop_no, phone_number, description, created_at
                FROM business_registration_requests
                WHERE user_id = %s AND processed = FALSE
            """, (user_id,))
            pending_businesses = cur.fetchall()
            
            # Fetch subscription plans
            cur.execute("""
                SELECT id, plan_name, amount, duration
                FROM subscription_plans
            """)
            subscription_plans = cur.fetchall()
            
            cur.close()
        except Exception as e:
            flash(f"Database error: {e}", 'error')
            
        finally:
            conn.close()

    return render_template('user_business_profile.html', 
                           businesses=businesses, 
                           pending_businesses=pending_businesses,
                           subscription_plans=subscription_plans)

# @bp.route('/edit_business_media/<int:business_id>', methods=['GET', 'POST'])
# def edit_business_media(business_id):
    
#     # Allow access if either admin or user is logged in
#     if 'admin_logged_in' not in session and 'user_logged_in' not in session:
#         flash(f"If you've completed a subscription, contact admin to update your business media or adverts.", category="info")
#         return redirect(url_for('auth.login'))
    
#     user_id = session.get('user_id')
#     flash(f"{user_id}")
#     conn = get_db_connection()
#     business = None

#     if conn:
#         try:
#             cur = conn.cursor(dictionary=True)
#             cur.execute("""
#                 SELECT id, business_name, shop_no, phone_number, description, is_subscribed, media_type, media_url, category, email
#                 FROM businesses
#                 WHERE owner_id = %s AND id = %s OR id = %s
#             """, (user_id, business_id, business_id))
#             business = cur.fetchone()

#             if request.method == 'POST' and business:
#                 media_type = request.form['media_type']
#                 file = request.files['file']

#                 if file and file.filename != '':
#                     media_url = upload_file(file)
#                     if media_url:
#                         cur.execute("""
#                             UPDATE businesses
#                             SET media_type = %s, media_url = %s
#                             WHERE id = %s AND owner_id = %s
#                         """, (media_type, media_url, business_id, user_id))
#                         conn.commit()
                        
#                         flash('Media uploaded successfully.', 'success')
#                     else:
#                         flash('Invalid file type.', 'error')
#                 else:
#                     flash('No file selected.', 'error')

#             cur.close()
#         except Exception as e:
#             flash(f"Database error: {e}", 'error')
#         finally:
#             conn.close()

#     return render_template('edit_business_media.html', business=business)

@bp.route('/edit_business_media/<int:business_id>', methods=['GET', 'POST'])
def edit_business_media(business_id):
    # Check if either admin or user is logged in
    if 'user_id' not in session and 'role' not in session:
        flash("If you've completed a subscription, contact admin to update your business media or adverts.", category="info")
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    conn = get_db_connection()
    business = None
    
    # return f"{business_id}"

    if conn:
        try:
            cur = conn.cursor(dictionary=True)

            # If user_id is None, fetch owner_id from businesses table
            if user_id is None:
                cur.execute("""
                    SELECT owner_id FROM businesses WHERE id = %s
                """, (business_id,))
                owner = cur.fetchone()
                user_id = owner['owner_id'] if owner else None

                # return f"{owner}"
                
            # Fetch business details
            cur.execute("""
                SELECT id, business_name, shop_no, phone_number, description, is_subscribed, media_type, media_url, category, email
                FROM businesses
                WHERE (owner_id = %s AND id = %s) OR id = %s
            """, (user_id, business_id, business_id))
            business = cur.fetchone()

            # Handle form submission
            if request.method == 'POST' and business:
                media_type = request.form['media_type']
                file = request.files['file']

                if file and file.filename:
                    media_url = upload_file(file)
                    if media_url:
                        cur.execute("""
                            UPDATE businesses
                            SET media_type = %s, media_url = %s
                            WHERE id = %s AND owner_id = %s
                        """, (media_type, media_url, business_id, user_id))
                        conn.commit()
                        flash('Media uploaded successfully.', 'success')
                    else:
                        flash('Invalid file type.', 'error')
                else:
                    flash('No file selected.', 'error')

            cur.close()
        except Exception as e:
            flash(f"Database error: {e}", 'error')
        finally:
            conn.close()

    return render_template('edit_business_media.html', user_id=user_id, business=business)

def upload_file(file):
    # Save the file to the server and return the URL
    # This is a placeholder implementation
    file_path = f"static/uploads/{file.filename}"
    file.save(file_path)
    return file_path

@bp.route('/view_profile')
def view_profile():
    if 'user_id' not in session:  # Ensure user is logged in
        flash('Please log in to view your profile.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT username, email, profile_image FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            cur.close()
        except Exception as e:
            print(f"Database error: {e}")
            flash('Error fetching user details.', 'error')
            user = None
        finally:
            conn.close()

    if user:
        return render_template('view_profile.html', user=user)
    else:
        flash('User not found.', 'error')
        return redirect(url_for('index.home'))

# @bp.route('/profile', methods=['GET', 'POST'])
# def update_profile():
    
#     if 'user_id' not in session:  # Assuming user_id is stored in session after login
#         flash('Please log in to access your profile.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     conn = get_db_connection()

#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         file = request.files['profile_image']
#         hashed_password = generate_password_hash(password, method='pbkdf2:sha256') if password else None

#         if conn:
#             try:
#                 cur = conn.cursor()

#                 # Update the username and password if provided
#                 if username:
#                     cur.execute("UPDATE users SET username = %s WHERE id = %s", (username, user_id))
#                 if hashed_password:
#                     cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))

#                 # Handle profile image upload if a file is provided
#                 if file and allowed_file(file.filename):
                    
#                     filename = secure_filename(file.filename)
#                     file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                     file.save(file_path)
#                     print("session-before", session['avatar'] )
#                     # Update the profile_image column in the database
#                     cur.execute("UPDATE users SET profile_image = %s WHERE id = %s", (file_path, user_id))
#                     session['avatar'] = file_path # re-assigning the image to the new image that was uploaded by the user, so that the user dont need to logout and login before the profile image will show on the navbar
#                     print("session-after", session['avatar'] )
                    
#                     # ===================================== 
#                     # cur.execute("""
#                     #     SELECT id, business_name, shop_no, phone_number, description, is_subscribed, media_type, media_url, category, email
#                     #     FROM businesses
#                     #     WHERE owner_id = %s AND id = %s
#                     # """, (user_id, business_id))
#                     # business = cur.fetchone()

#                     # Ensure user_id is passed as a tuple
#                     # cur.execute("""SELECT id FROM businesses WHERE owner_id = %s """, (user_id,))  # Note the comma
#                     # business = cur.fetchone()

#                     # cur.execute("SELECT owner_id FROM businesses WHERE id = %s", (business_id,))
#                     # user_id = cur.fetchone()[0]
#                     cur.execute("SELECT id FROM businesses WHERE owner_id = %s", (user_id,))
#                     business = cur.fetchone()
#                     print(business)
#                     print(user_id)
#                     if business and business is not None:
#                         # flash('No business found for this owner.', 'error')
#                         business_id = business[0]
                        
#                         media_type = "image"
#                         # media_type = request.form['media_type'] or "image"
                        
#                         cur.execute("""
#                                     UPDATE businesses
#                                     SET media_type = %s, media_url = %s
#                                     WHERE id = %s AND owner_id = %s
#                                 """, (media_type, file_path, business_id, user_id))  # This is correct
#                         conn.commit()
#                         flash('Media uploaded successfully also for business.', 'success')
                    
#                     # file = request.files['file']

#                     # if file and file.filename != '':
#                     #     media_url = upload_file(file)
#                     #     if media_url:
#                     #         cur.execute("""
#                     #             UPDATE businesses
#                     #             SET media_type = %s, media_url = %s
#                     #             WHERE id = %s AND owner_id = %s
#                     #         """, (media_type, file_path, business[0], user_id))  # This is correct
#                     #         conn.commit()
#                     #         flash('Media uploaded successfully.', 'success')
#                     #     else:
#                     #         flash('Invalid file type.', 'error')
#                     # else:
#                     #     flash('No file selected.', 'error')

#                     # ===================================== 
                    
#                 conn.commit()
#                 flash('Profile updated successfully!', 'success')
#             except Exception as e:
#                 print(f"Database error: {e}")
#                 flash('Error updating profile.', 'error')
#             finally:
#                 cur.close()
#                 conn.close()

#         return redirect(url_for('user.update_profile'))

#     # GET request: fetch the user's current details to display in the form
#     if conn:
#         try:
#             cur = conn.cursor()
#             cur.execute("SELECT username, email, profile_image FROM users WHERE id = %s", (user_id,))
#             user = cur.fetchone()
#             cur.close()
#         except Exception as e:
#             print(f"Database error: {e}")
#             flash('Error fetching user details.', 'error')
#         finally:
#             conn.close()

#     return render_template('profile.html', user=user)

# @bp.route('/profile', methods=['GET', 'POST'])
# def update_profile():
#     if 'user_id' not in session:
#         flash('Please log in to access your profile.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     conn = get_db_connection()

#     if request.method == 'POST':
#         return handle_post_request(conn, user_id)

#     return handle_get_request(conn, user_id)

# def handle_post_request(conn, user_id):
#     username = request.form.get('username')
#     password = request.form.get('password')
#     file = request.files.get('profile_image')
#     hashed_password = generate_password_hash(password, method='pbkdf2:sha256') if password else None

#     if conn:
#         try:
#             cur = conn.cursor()
#             update_user_profile(cur, user_id, username, hashed_password)

#             if file and allowed_file(file.filename):
#                 file_path = save_profile_image(file)
#                 session['avatar'] = file_path
#                 update_business_media(cur, user_id, file_path)

#             conn.commit()
#             flash('Profile updated successfully!', 'success')
#         except Exception as e:
#             traceback.print_exc()
#             print(f"Database error: {e}")
#             flash('Error updating profile.', 'error')
#         finally:
#             cur.close()
#             conn.close()

#     return redirect(url_for('user.update_profile'))


# def handle_get_request(conn, user_id):
#     user = None
#     if conn:
#         try:
#             cur = conn.cursor(dictionary=True)
#             cur.execute("SELECT username, email, profile_image FROM users WHERE id = %s", (user_id,))
#             user = cur.fetchone()
#         except Exception as e:
#             print(f"Database error: {e}")
#             flash('Error fetching user details.', 'error')
#         finally:
#             cur.close()
#             conn.close()

#     return render_template('profile.html', user=user)


# def update_user_profile(cur, user_id, username, hashed_password):
#     if username:
#         cur.execute("UPDATE users SET username = %s WHERE id = %s", (username, user_id))
#     if hashed_password:
#         cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))


# def save_profile_image(file):
#     filename = secure_filename(file.filename)
#     file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#     file.save(file_path)
#     return file_path


# def update_business_media(cur, user_id, file_path):
#     cur.execute("SELECT id FROM businesses WHERE owner_id = %s", (user_id,))
#     business = cur.fetchone()

#     if business:
#         business_id = business[0]
#         media_type = "image"
#         cur.execute("""
#             UPDATE businesses
#             SET media_type = %s, media_url = %s
#             WHERE id = %s AND owner_id = %s
#         """, (media_type, file_path, business_id, user_id))
#         flash('Media uploaded successfully for business.', 'success')

@bp.route('/profile', methods=['GET', 'POST'])
def update_profile():
    if 'user_id' not in session:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        return handle_post_request(conn, user_id)

    return handle_get_request(conn, user_id)


def handle_post_request(conn, user_id):
    username = request.form.get('username')
    password = request.form.get('password')
    image = request.files.get('image')
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256') if password else None

    if conn:
        try:
            cur = conn.cursor()
            update_user_profile(cur, user_id, username, hashed_password)

            if file and allowed_file(file.filename):
                file_path = save_profile_image(image)
                session['avatar'] = file_path
                update_user_profile_image(cur, user_id, file_path)
                # update_business_media(cur, user_id, file_path)

            conn.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            print(f"Database error: {e}")
            flash('Error updating profile.', 'error')
        finally:
            cur.close()
            conn.close()

    return redirect(url_for('user.update_profile'))


def handle_get_request(conn, user_id):
    user = None
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT username, email, profile_image FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
        except Exception as e:
            print(f"Database error: {e}")
            flash('Error fetching user details.', 'error')
        finally:
            cur.close()
            conn.close()

    return render_template('profile.html', user=user)


def update_user_profile(cur, user_id, username, hashed_password):
    if username:
        cur.execute("UPDATE users SET username = %s WHERE id = %s", (username, user_id))
    if hashed_password:
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))


def save_profile_image(file):
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return file_path


def update_user_profile_image(cur, user_id, file_path):
    cur.execute("UPDATE users SET profile_image = %s WHERE id = %s", (file_path, user_id))


def update_business_media(cur, user_id, file_path):
    cur.execute("SELECT id FROM businesses WHERE owner_id = %s", (user_id,))
    business = cur.fetchone()

    if business:
        business_id = business[0]
        media_type = "image"
        cur.execute("""
            UPDATE businesses
            SET media_type = %s, media_url = %s
            WHERE id = %s AND owner_id = %s
        """, (media_type, file_path, business_id, user_id))
        flash('Media uploaded successfully for business.', 'success')