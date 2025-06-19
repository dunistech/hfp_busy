import os, traceback
from flask import Blueprint, current_app as app, request, render_template, redirect, session, url_for, flash
from utils import allowed_file, get_db_connection
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('user', __name__)

# def upload_file(file):
#     """Handle file uploads for both user profile and business media"""
#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
#         upload_folder = app.config['UPLOAD_FOLDER']
#         os.makedirs(upload_folder, exist_ok=True)
#         file_path = os.path.join(upload_folder, filename)
#         file.save(file_path)
#         return file_path
#     return None

def upload_file(file):
    """Handle file uploads and return PROPERLY FORMATTED full web URL"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = app.config['UPLOAD_FOLDER']
        print(upload_folder)
        # Create directory if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # PROPERLY construct the full URL with correct slashes
        base_url = request.host_url.rstrip('/')  # Gets "http://localhost:5000"
        # static_path = f"/static/uploads/{filename}"  # Note leading slash
        static_path = f"/static/uploads/{filename}"  # Note leading slash
        full_url = f"{base_url}{static_path}"  # Correctly joins with slash
        
        return full_url  # "http://localhost:5000/static/uploads/02.png"
    return None

@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Complete user profile management with business integration"""
    if 'user_id' not in session:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db_connection()
    user = None
    businesses = []

    if request.method == 'POST':
        try:
            # Handle form data
            username = request.form.get('username')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            password = request.form.get('password')
            file = request.files.get('profile_image')

            # Update user profile
            update_fields = {}
            if username:
                update_fields['username'] = username
            if email:
                update_fields['email'] = email
            if phone:
                update_fields['phone'] = phone
            if address:
                update_fields['address'] = address
            if password:
                update_fields['password'] = generate_password_hash(password, method='pbkdf2:sha256')

            # Handle profile image upload
            if file and file.filename:
                file_path = upload_file(file)
                if file_path:
                    update_fields['profile_image'] = file_path
                    session['avatar'] = file_path  # Update session immediately

            # Update database if there are changes
            if update_fields:
                set_clause = ', '.join([f"{k} = %s" for k in update_fields])
                values = list(update_fields.values()) + [user_id]
                
                cur = conn.cursor()
                cur.execute(f"UPDATE users SET {set_clause} WHERE id = %s", values)
                conn.commit()
                flash('Profile updated successfully!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
        finally:
            if conn:
                conn.close()

        return redirect(url_for('user.profile'))

    # GET request - fetch user and business data
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            
            # Get user details
            cur.execute("""
                SELECT id, username, email, phone, address, profile_image, created_at
                FROM users 
                WHERE id = %s
            """, (user_id,))
            user = cur.fetchone()
            
            # Get user's businesses with status
            # cur.execute("""
            #     SELECT b.id, b.business_name, b.description, b.category, 
            #            b.phone_number, b.email, b.shop_no, b.address,
            #            b.media_type, b.media_url, b.is_subscribed,
            #            b.status, b.created_at,
            #            CASE 
            #                WHEN b.status = 'active' THEN 'Active'
            #                WHEN b.status = 'pending' THEN 'Pending Approval'
            #                WHEN b.status = 'suspended' THEN 'Suspended'
            #                ELSE b.status
            #            END as status_display
            #     FROM businesses b
            #     WHERE b.owner_id = %s
            #     ORDER BY b.status = 'active' DESC, b.created_at DESC
            # """, (user_id,))

            # MySQL version with GROUP_CONCAT
            cur.execute("""
                SELECT b.*, 
                       GROUP_CONCAT(DISTINCT c.category_name SEPARATOR '|||') AS category_names,
                       GROUP_CONCAT(DISTINCT c.id SEPARATOR '|||') AS category_ids
                FROM businesses b
                LEFT JOIN business_categories bc ON b.id = bc.business_id
                LEFT JOIN categories c ON bc.category_id = c.id
                WHERE b.owner_id = %s
                GROUP BY b.id
            """, (user_id,))

            businesses = cur.fetchall()
            
            # Convert status to display text
            for business in businesses:
                business['status_display'] = 'Active' if business['status'] == 'active' else \
                                           'Pending' if business['status'] == 'pending' else \
                                           'Suspended'
                
                # Convert category strings to lists
                if business.get('category_names'):
                    names = business['category_names'].split('|||')
                    ids = business['category_ids'].split('|||')
                    business['categories'] = [{'name': name} for name in names]
                else:
                    # Fallback to single category if exists
                    if business.get('category'):
                        business['categories'] = [{'name': business['category']}]
                    else:
                        business['categories'] = []

        except Exception as e:
            flash(f'Database error: {str(e)}', 'error')
        finally:
            if conn:
                conn.close()

    return render_template('user_profile.html', user=user, businesses=businesses)

from functools import wraps

def admin_required(f):
    """Decorator to ensure user has admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Administrator access required', 'error')
            return redirect(url_for('user.profile'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin/businesses')
@bp.route('/admin/businesses2')
# @admin_required
def admin_businesses():
    """Admin view of all businesses"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)

        # cur.execute("SELECT COUNT(*) as total FROM businesses WHERE status != 'deleted'")
        # count = cur.fetchone()
        # print(f"Total non-deleted businesses: {count['total']}")

        # Get all businesses with owner info and categories
        # cur.execute("""
        #     SELECT 
        #         b.*,
        #         u.username as owner_username,
        #         u.email as owner_email,
        #         GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
        #         COUNT(DISTINCT c.id) as category_count
        #     FROM businesses b
        #     LEFT JOIN users u ON b.owner_id = u.id
        #     LEFT JOIN business_categories bc ON b.id = bc.business_id
        #     LEFT JOIN categories c ON bc.category_id = c.id
        #     GROUP BY b.id
        #     ORDER BY b.status = 'active' DESC, b.created_at DESC
        # """)

        # This includes all businesses, not just acive
        # Get all businesses with owner info and categories
        cur.execute("""
    SELECT 
        b.*,
        u.username as owner_username,
        u.email as owner_email,
        (SELECT GROUP_CONCAT(c.category_name SEPARATOR ', ') 
         FROM business_categories bc
         JOIN categories c ON bc.category_id = c.id
         WHERE bc.business_id = b.id) AS categories,
        (SELECT COUNT(*) 
         FROM business_categories bc
         WHERE bc.business_id = b.id) AS category_count,
        CASE 
            WHEN b.status = 'active' THEN 'Active'
            WHEN b.status = 'pending' THEN 'Pending Approval'
            WHEN b.status = 'suspended' THEN 'Suspended'
            ELSE b.status
        END as status_display
    FROM businesses b
    LEFT JOIN users u ON b.owner_id = u.id
    WHERE b.status != 'deleted'
    ORDER BY 
        CASE 
            WHEN b.status = 'active' THEN 1
            WHEN b.status = 'pending' THEN 2
            WHEN b.status = 'suspended' THEN 3
            ELSE 4
        END,
        b.created_at DESC
""")
        businesses = cur.fetchall()
        
        # Process categories
        for biz in businesses:
            biz['status_display'] = 'Active' if biz['status'] == 'active' else \
                                  'Pending' if biz['status'] == 'pending' else \
                                  'Suspended'
        # print(businesses)
        return render_template('admin_businesses.html', businesses=businesses)
    except Exception as e:
        flash(f'Error loading businesses: {str(e)}', 'error')
        return redirect(url_for('user.profile'))
    finally:
        if conn:
            conn.close()

@bp.route('/admin/users')
@admin_required
def admin_users():
    """Admin view of all users"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get all users with business count
        cur.execute("""
            SELECT 
                u.*,
                COUNT(b.id) as business_count,
                CASE 
                    WHEN u.role = 'admin' THEN 'Admin'
                    WHEN u.role = 'owner' THEN 'Business Owner'
                    ELSE 'Regular User'
                END as role_display
            FROM users u
            LEFT JOIN businesses b ON u.id = b.owner_id
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        users = cur.fetchall()
        
        return render_template('admin_users.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('user.profile'))
    finally:
        if conn:
            conn.close()


@bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user account (admin only)"""
    if user_id == session['user_id']:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('user.admin_users'))

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get user info for confirmation message
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('user.admin_users'))
        
        # Check if user owns any businesses
        cur.execute("SELECT COUNT(*) as business_count FROM businesses WHERE owner_id = %s", (user_id,))
        result = cur.fetchone()
        
        if result['business_count'] > 0:
            flash('Cannot delete user - they own businesses. Reassign businesses first.', 'error')
            return redirect(url_for('user.admin_users'))
        
        # Delete user
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        flash(f'User "{user["username"]}" has been deleted', 'success')
        return redirect(url_for('user.admin_users'))
        
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('user.admin_users'))
    finally:
        if conn:
            conn.close()



@bp.route('/admin/business/<int:business_id>/update_status', methods=['POST'])
@admin_required
def admin_update_business_status(business_id):
    """Admin update business status"""
    new_status = request.form.get('status')
    
    if not new_status or new_status not in ['active', 'suspended', 'pending']:
        flash('Invalid status provided', 'error')
        return redirect(url_for('user.admin_businesses'))
    
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get business name for logging
        cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('user.admin_businesses'))
        
        # Update status
        cur.execute("""
            UPDATE businesses 
            SET status = %s
            WHERE id = %s
        """, (new_status, business_id))
        
        conn.commit()
        flash(f'Business "{business["business_name"]}" status updated to {new_status}', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('user.admin_businesses'))

@bp.route('/admin/user/<int:user_id>/update_role', methods=['POST'])
@admin_required
def admin_update_user_role(user_id):
    """Admin update user role"""
    new_role = request.form.get('role')
    
    if not new_role or new_role not in ['admin', 'owner', 'user']:
        flash('Invalid role provided', 'error')
        return redirect(url_for('user.admin_users'))
    
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get username for logging
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('user.admin_users'))
        
        # Prevent self-demotion
        if user_id == session['user_id'] and new_role != 'admin':
            flash('You cannot remove your own admin privileges', 'error')
            return redirect(url_for('user.admin_users'))
        
        # Update role
        cur.execute("""
            UPDATE users 
            SET role = %s
            WHERE id = %s
        """, (new_role, user_id))
        
        conn.commit()
        flash(f'User "{user["username"]}" role updated to {new_role}', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating role: {str(e)}', 'error')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('user.admin_users'))












































# @bp.route('/business/<int:business_id>', methods=['GET', 'POST'])
# def business_profile(business_id):
#     """Manage individual business profile"""
#     if 'user_id' not in session:
#         flash('Please log in to access this page.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     conn = get_db_connection()
#     business = None
#     subscription_plans = []

#     if conn:
#         try:
#             cur = conn.cursor(dictionary=True)
            
#             # Verify ownership and get business details
#             cur.execute("""
#                 SELECT b.*, 
#                        CASE 
#                            WHEN b.status = 'active' THEN 'Active'
#                            WHEN b.status = 'pending' THEN 'Pending Approval'
#                            WHEN b.status = 'suspended' THEN 'Suspended'
#                            ELSE b.status
#                        END as status_display
#                 FROM businesses b
#                 WHERE b.id = %s AND b.owner_id = %s
#             """, (business_id, user_id))
#             business = cur.fetchone()
#             # business = cur.fetchall()

#             if not business:
#                 flash('Business not found or you do not have permission.', 'danger')
#                 return redirect(url_for('user.profile'))

#             # Handle form submission for business updates
#             if request.method == 'POST':
#                 business_name = request.form.get('business_name')
#                 description = request.form.get('description')
#                 # category = request.form.get('category')
#                 phone_number = request.form.get('phone_number')
#                 email = request.form.get('email')
#                 shop_no = request.form.get('shop_no')
#                 bloc_num = request.form.get('block_num')
#                 address = request.form.get('address')
#                 facebook = request.form.get('facebook_link')
#                 instagram = request.form.get('instagram_link')
#                 twitter = request.form.get('twitter_link')
#                 website = request.form.get('website_url')
#                 file = request.files.get('business_media')

#                 # Update business details
#                 update_fields = {
#                     'business_name': business_name,
#                     'description': description,
#                     # 'category': category,
#                     'phone_number': phone_number,
#                     'email': email,
#                     'shop_no': shop_no,
#                     'block_num': block_num,
#                     'address': address,
#                     'facebook_link': facebook,
#                     'instagram_link': instagram,
#                     'twitter_link': twitter,
#                     'website_url': website
#                 }

#                 # Handle media upload
#                 if file and file.filename:
#                     file_path = upload_file(file)
#                     if file_path:
#                         update_fields['media_url'] = file_path
#                         update_fields['media_type'] = 'image'  # Default to image

#                 # Build and execute update query
#                 set_clause = ', '.join([f"{k} = %s" for k in update_fields])
#                 values = list(update_fields.values()) + [business_id, user_id]
                
#                 cur.execute(f"""
#                     UPDATE businesses 
#                     SET {set_clause}
#                     WHERE id = %s AND owner_id = %s
#                 """, values)
                
#                 # 
#                 selected_category_ids = request.form.getlist('categories')
#                 # First, delete existing relationships
#                 cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))

#                 # Then add the new ones
#                 for cat_id in selected_category_ids:
#                     cur.execute("""
#                         INSERT INTO business_categories (business_id, category_id)
#                         VALUES (%s, %s)
#                     """, (business_id, cat_id))
#                 # 

#                 conn.commit()
#                 flash('Business updated successfully!', 'success')
#                 return redirect(url_for('user.business_profile', business_id=business_id))

#             # Get subscription plans for the subscription section
#             # cur.execute("""
#             #     SELECT id, plan_name, amount, duration, features
#             #     FROM subscription_plans
#             #     WHERE is_active = TRUE
#             #     ORDER BY amount ASC
#             # """)
#             cur.execute("""
#                 SELECT * FROM subscription_plans WHERE 1 ORDER BY amount ASC
#             """)
#             subscription_plans = cur.fetchall()

#             # 
#             # Get all available categories
#             cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
#             all_categories = cur.fetchall()

#             # Get business's current categories
#             cur.execute("""
#                 SELECT c.id, c.category_name 
#                 FROM business_categories bc
#                 JOIN categories c ON bc.category_id = c.id
#                 WHERE bc.business_id = %s
#             """, (business_id,))
#             business_categories = cur.fetchall()

#             # Convert to list of IDs for easier template handling
#             business_category_ids = [cat['id'] for cat in business_categories]

#             context = {
#                 "business_categories": business_categories,
#                 "business_category_ids": business_category_ids,
#                 "business":business, "subscription_plans":subscription_plans,
#             }


#         except Exception as e:
#             conn.rollback()
#             traceback.print_exception(e)
#             flash(f'Error updating business: {str(e)}', 'error')
#         finally:
#             if conn:
#                 conn.close()
#     # print(business)
#     return render_template('business_profile_0.html', **context)
# 

# @bp.route('/business/<int:business_id>', methods=['GET', 'POST'])
# def business_profile(business_id):
#     """Manage individual business profile"""
#     if 'user_id' not in session:
#         flash('Please log in to access this page.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     conn = get_db_connection()
#     business = None
#     subscription_plans = []
#     all_categories = []
#     business_categories = []
#     business_category_ids = []

#     if conn:
#         try:
#             cur = conn.cursor(dictionary=True)
            
#             # Verify ownership and get business details
#             cur.execute("""
#                 SELECT b.*, 
#                        CASE 
#                            WHEN b.status = 'active' THEN 'Active'
#                            WHEN b.status = 'pending' THEN 'Pending Approval'
#                            WHEN b.status = 'suspended' THEN 'Suspended'
#                            ELSE b.status
#                        END as status_display
#                 FROM businesses b
#                 WHERE b.id = %s AND b.owner_id = %s
#             """, (business_id, user_id))
#             business = cur.fetchone()

#             if not business:
#                 flash('Business not found or you do not have permission.', 'error')
#                 return redirect(url_for('user.profile'))

#             # Get all available categories
#             cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
#             all_categories = cur.fetchall()

#             # Get business's current categories
#             cur.execute("""
#                 SELECT c.id, c.category_name 
#                 FROM business_categories bc
#                 JOIN categories c ON bc.category_id = c.id
#                 WHERE bc.business_id = %s
#             """, (business_id,))
#             business_categories = cur.fetchall()
#             business_category_ids = [cat['id'] for cat in business_categories]

#             # Handle form submission for business updates
#             if request.method == 'POST':
#                 business_name = request.form.get('business_name')
#                 description = request.form.get('description')
#                 phone_number = request.form.get('phone_number')
#                 email = request.form.get('email')
#                 shop_no = request.form.get('shop_no')
#                 block_num = request.form.get('block_num')  # Fixed typo: was bloc_num
#                 address = request.form.get('address')
#                 facebook = request.form.get('facebook_link')
#                 instagram = request.form.get('instagram_link')
#                 twitter = request.form.get('twitter_link')
#                 website = request.form.get('website_url')
#                 file = request.files.get('business_media')
#                 selected_category_ids = request.form.getlist('categories')

#                 # Update business details
#                 update_fields = {
#                     'business_name': business_name,
#                     'description': description,
#                     'phone_number': phone_number,
#                     'email': email,
#                     'shop_no': shop_no,
#                     'block_num': block_num,
#                     'address': address,
#                     'facebook_link': facebook,
#                     'instagram_link': instagram,
#                     'twitter_link': twitter,
#                     'website_url': website
#                 }

#                 # Handle media upload
#                 if file and file.filename:
#                     file_path = upload_file(file)
#                     if file_path:
#                         update_fields['media_url'] = file_path
#                         update_fields['media_type'] = 'image'  # Default to image

#                 # Build and execute update query
#                 set_clause = ', '.join([f"{k} = %s" for k in update_fields])
#                 values = list(update_fields.values()) + [business_id, user_id]
                
#                 cur.execute(f"""
#                     UPDATE businesses 
#                     SET {set_clause}
#                     WHERE id = %s AND owner_id = %s
#                 """, values)
                
#                 # Update categories relationship
#                 # First, delete existing relationships
#                 cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))

#                 # Then add the new ones
#                 for cat_id in selected_category_ids:
#                     if cat_id:  # Ensure category ID is not empty
#                         cur.execute("""
#                             INSERT INTO business_categories (business_id, category_id)
#                             VALUES (%s, %s)
#                         """, (business_id, cat_id))

#                 conn.commit()
#                 flash('Business updated successfully!', 'success')
#                 return redirect(url_for('user.business_profile', business_id=business_id))

#             # Get subscription plans
#             cur.execute("SELECT * FROM subscription_plans ORDER BY amount ASC")
#             subscription_plans = cur.fetchall()

#         except Exception as e:
#             conn.rollback()
#             traceback.print_exc()  # Better for debugging than print_exception
#             flash(f'Error updating business: {str(e)}', 'error')
#         finally:
#             if conn:
#                 conn.close()

#     context = {
#         "business": business,
#         "subscription_plans": subscription_plans,
#         "all_categories": all_categories,
#         "business_categories": business_categories,
#         "business_category_ids": business_category_ids
#     }

#     return render_template('business_profile_0.html', **context)

# UPDATED ON 6/19/2025 AROUND 4:11PM
@bp.route('/business/<int:business_id>', methods=['GET', 'POST'])
def business_profile(business_id):
    """Manage individual business profile (admin or owner access only)"""
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db_connection()
    business = None
    subscription_plans = []
    all_categories = []
    business_categories = []
    business_category_ids = []

    if conn:
        try:
            cur = conn.cursor(dictionary=True)

            # Get user role
            cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            is_admin = user and user['role'] == 'admin'

            # Get business and check access
            cur.execute("""
                SELECT b.*, 
                       CASE 
                           WHEN b.status = 'active' THEN 'Active'
                           WHEN b.status = 'pending' THEN 'Pending Approval'
                           WHEN b.status = 'suspended' THEN 'Suspended'
                           ELSE b.status
                       END as status_display
                FROM businesses b
                WHERE b.id = %s
            """, (business_id,))
            business = cur.fetchone()

            if not business:
                flash('Business not found.', 'error')
                return redirect(url_for('user.profile'))

            if not is_admin and business['owner_id'] != user_id:
                flash('You do not have permission to access this business.', 'danger')
                return redirect(url_for('user.profile'))

            # Get all available categories
            cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
            all_categories = cur.fetchall()

            # Get business's current categories
            cur.execute("""
                SELECT c.id, c.category_name 
                FROM business_categories bc
                JOIN categories c ON bc.category_id = c.id
                WHERE bc.business_id = %s
            """, (business_id,))
            business_categories = cur.fetchall()
            business_category_ids = [cat['id'] for cat in business_categories]

            # Handle form submission for business updates
            if request.method == 'POST':
                business_name = request.form.get('business_name')
                description = request.form.get('description')
                phone_number = request.form.get('phone_number')
                email = request.form.get('email')
                shop_no = request.form.get('shop_no')
                block_num = request.form.get('block_num')
                address = request.form.get('address')
                facebook = request.form.get('facebook_link')
                instagram = request.form.get('instagram_link')
                twitter = request.form.get('twitter_link')
                website = request.form.get('website_url')
                file = request.files.get('business_media')
                selected_category_ids = request.form.getlist('categories')

                update_fields = {
                    'business_name': business_name,
                    'description': description,
                    'phone_number': phone_number,
                    'email': email,
                    'shop_no': shop_no,
                    'block_num': block_num,
                    'address': address,
                    'facebook_link': facebook,
                    'instagram_link': instagram,
                    'twitter_link': twitter,
                    'website_url': website
                }

                # Handle media upload
                if file and file.filename:
                    file_path = upload_file(file)
                    if file_path:
                        update_fields['media_url'] = file_path
                        update_fields['media_type'] = 'image'

                # Build and execute update query
                set_clause = ', '.join([f"{k} = %s" for k in update_fields])
                values = list(update_fields.values()) + [business_id]

                # If not admin, enforce owner check
                if not is_admin:
                    update_sql = f"UPDATE businesses SET {set_clause} WHERE id = %s AND owner_id = %s"
                    values.append(user_id)
                else:
                    update_sql = f"UPDATE businesses SET {set_clause} WHERE id = %s"

                cur.execute(update_sql, values)

                # Update business categories
                cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))
                for cat_id in selected_category_ids:
                    if cat_id:
                        cur.execute("""
                            INSERT INTO business_categories (business_id, category_id)
                            VALUES (%s, %s)
                        """, (business_id, cat_id))

                conn.commit()
                flash('Business updated successfully!', 'success')
                return redirect(url_for('user.business_profile', business_id=business_id))

            # Load subscription plans
            cur.execute("SELECT * FROM subscription_plans ORDER BY amount ASC")
            subscription_plans = cur.fetchall()

        except Exception as e:
            conn.rollback()
            traceback.print_exc()
            flash(f'Error updating business: {str(e)}', 'error')
        finally:
            conn.close()

    context = {
        "business": business,
        "subscription_plans": subscription_plans,
        "all_categories": all_categories,
        "business_categories": business_categories,
        "business_category_ids": business_category_ids
    }

    return render_template('business_profile_0.html', **context)

# 
@bp.route('/business/<int:business_id>/public')
def public_business_profile(business_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get business details with categories
        cur.execute("""
            SELECT 
                b.*,
                u.username as owner_username,
                GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories
            FROM businesses b
            LEFT JOIN users u ON b.owner_id = u.id
            LEFT JOIN business_categories bc ON b.id = bc.business_id
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE b.id = %s AND b.status = 'active'
            GROUP BY b.id
        """, (business_id,))
        
        business = cur.fetchone()
        
        if not business:
            # flash('Business not found or not active', 'error')
            flash("Currently not runninng Ads, if you're the owner, Subscribe to a plan to make your business page accessible ", 'error')
            return redirect(url_for('index.home'))
        
        # Get similar businesses (same category)
        cur.execute("""
            SELECT b.id, b.business_name, b.media_url, b.media_type
            FROM businesses b
            JOIN business_categories bc ON b.id = bc.business_id
            WHERE bc.category_id IN (
                SELECT category_id FROM business_categories 
                WHERE business_id = %s
            )
            AND b.id != %s
            AND b.status = 'active'
            GROUP BY b.id
            LIMIT 4
        """, (business_id, business_id))
        
        similar_businesses = cur.fetchall()
        
        return render_template('public_business_profile.html',
                            business=business,
                            similar_businesses=similar_businesses,
                            is_owner=('user_id' in session and 
                                     session['user_id'] == business['owner_id']))
        
    except Exception as e:
        app.logger.error(f"Error loading business profile: {str(e)}")
        traceback.print_exception(e)
        flash('Error loading business profile', 'error')
        return redirect(url_for('index.home'))
    finally:
        if conn:
            conn.close()



# @bp.route('/add_business', methods=['GET', 'POST'])
# def add_business():
#     """Add new business with integrated status handling"""
#     if 'user_id' not in session:
#         flash('Please log in to add a business.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']

#     if request.method == 'POST':
#         conn = get_db_connection()
#         try:
#             # Get form data
#             business_name = request.form.get('business_name')
#             description = request.form.get('description')
#             # category = request.form.get_list('category')
#             phone_number = request.form.get('phone_number')
#             email = request.form.get('email')
#             shop_no = request.form.get('shop_no')
#             block_num = request.form.get('block_num')
#             address = request.form.get('address')
#             file = request.files.get('business_media')

#             # Handle media upload
#             media_url = None
#             media_type = None
#             if file and file.filename:
#                 media_url = upload_file(file)
#                 media_type = 'image'  # Default to image type

#             # Insert new business with 'pending' status
#             cur = conn.cursor()
#             cur.execute("""
#                 INSERT INTO businesses (
#                     owner_id, business_name, description,
#                     phone_number, email, shop_no, block_num, address,
#                     media_type, media_url, status
#                 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
#             """, (
#                 user_id, business_name, description,
#                 phone_number, email, shop_no, block_num, address,
#                 media_type, media_url
#             ))

#             category_ids = request.form.getlist('categories')
#             # Create category relationships
#             for category_id in category_ids:
#                 cur.execute("""
#                     INSERT INTO business_categories (business_id, category_id)
#                     VALUES (%s, %s)
#                 """, (business_id, category_id))
            
#             conn.commit()
#             flash('Business submitted for approval!', 'success')
#             return redirect(url_for('user.profile'))

#         except Exception as e:
#             conn.rollback()
#             flash(f'Error adding business: {str(e)}', 'error')
#         finally:
#             if conn:
#                 conn.close()

#     try:
#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)
#         cur.execute("SELECT id, category_name AS name FROM categories ORDER BY category_name")
#         categories = cur.fetchall()
#     finally:
#         conn.close()

#     return render_template('add_business.html', categories=categories)

@bp.route('/add_business', methods=['GET', 'POST'])
def add_business():
    """Add new business with integrated status handling"""
    if 'user_id' not in session:
        flash('Please log in to add a business.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        conn = get_db_connection()
        try:
            # Get form data
            business_name = request.form.get('business_name')
            description = request.form.get('description')
            phone_number = request.form.get('phone_number')
            email = request.form.get('email')
            shop_no = request.form.get('shop_no')
            block_num = request.form.get('block_num')
            address = request.form.get('address')

            website_url = request.form.get('website_url')
            facebook_link = request.form.get('facebook_link')
            instagram_link = request.form.get('instagram_link')
            twitter_link = request.form.get('twitter_link')

            file = request.files.get('business_media')
            category_ids = request.form.getlist('categories')

            # Handle media upload
            media_url = None
            media_type = None
            if file and file.filename:
                media_url = upload_file(file)
                media_type = 'image'  # Default to image type

            # Insert new business with 'pending' status
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO businesses (
                    owner_id, business_name, description,
                    phone_number, email, shop_no, block_num, address,
                    website_url, facebook_link, instagram_link, twitter_link, 
                    media_type, media_url, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (
                user_id, business_name, description,
                phone_number, email, shop_no, block_num, address,
                website_url, facebook_link, instagram_link, twitter_link, 
                media_type, media_url
            ))

            # Get the newly created business ID
            business_id = cur.lastrowid

            # Create category relationships
            for category_id in category_ids:
                cur.execute("""
                    INSERT INTO business_categories (business_id, category_id)
                    VALUES (%s, %s)
                """, (business_id, category_id))
            
            conn.commit()
            flash('Business submitted for approval!', 'success')
            return redirect(url_for('user.profile'))

        except Exception as e:
            conn.rollback()
            flash(f'Error adding business: {str(e)}', 'error')
            # Get categories again to render the form with errors
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, category_name AS name FROM categories ORDER BY category_name")
            categories = cur.fetchall()
            return render_template('add_business.html', categories=categories)
        finally:
            if conn:
                conn.close()

    # GET request - fetch categories
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, category_name AS name FROM categories ORDER BY category_name")
        categories = cur.fetchall()
    except Exception as e:
        flash(f'Error loading categories: {str(e)}', 'error')
        categories = []
    finally:
        if conn:
            conn.close()

    return render_template('add_business.html', categories=categories)


# @bp.route('/delete_business/<int:business_id>', methods=['POST'])
# def delete_business(business_id):
#     """Delete a business with confirmation"""
#     if 'user_id' not in session:
#         flash('Please log in to perform this action.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     conn = get_db_connection()
    
#     try:
#         cur = conn.cursor()
        
#         # Verify ownership before deletion
#         cur.execute("""
#             DELETE FROM businesses 
#             WHERE id = %s AND owner_id = %s
#             RETURNING business_name
#         """, (business_id, user_id))
        
#         result = cur.fetchone()
#         if not result:
#             flash('Business not found or you do not have permission.', 'error')
#         else:
#             conn.commit()
#             flash(f'Business "{result[0]}" has been deleted.', 'success')
            
#     except Exception as e:
#         traceback.print_exception(e)
#         conn.rollback()
#         flash(f'Error deleting business: {str(e)}', 'error')
#     finally:
#         if conn:
#             conn.close()
    
#     return redirect(url_for('user.profile'))

# @bp.route('/delete_business/<int:business_id>', methods=['POST'])
# def delete_business(business_id):
#     """Delete a business with confirmation"""
#     if 'user_id' not in session:
#         flash('Please log in to perform this action.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     conn = get_db_connection()
#     business_name = None
    
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # First get the business name to use in the success message
#         cur.execute("""
#             SELECT business_name FROM businesses 
#             WHERE id = %s AND owner_id = %s
#         """, (business_id, user_id))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found or you do not have permission.', 'error')
#             return redirect(url_for('user.profile'))
        
#         business_name = business['business_name']
        
#                 # Also delete from the business_categories join table
#         cur.execute("""
#             DELETE FROM business_categories
#             WHERE business_id = %s
#         """, (business_id,))

#         # Now delete the business
#         cur.execute("""
#             DELETE FROM businesses 
#             WHERE id = %s AND owner_id = %s
#         """, (business_id, user_id))
        
#         conn.commit()
#         flash(f'Business "{business_name}" has been deleted.', 'success')
        
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error deleting business: {str(e)}', 'error')
#     finally:
#         if conn:
#             conn.close()
    
#     return redirect(url_for('user.profile'))


@bp.route('/delete_business/<int:business_id>', methods=['POST'])
def delete_business(business_id):
    """Delete a business with confirmation"""
    if 'user_id' not in session:
        flash('Please log in to perform this action.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user_role = session.get('role', 'user')  # default to 'user' if not set
    conn = get_db_connection()
    business_name = None

    try:
        cur = conn.cursor(dictionary=True)

        # Get the business info regardless of user
        cur.execute("SELECT id, business_name, owner_id FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()

        if not business:
            flash('Business not found.', 'error')
            return redirect(url_for('user.profile'))

        # Allow if user is owner or admin
        if business['owner_id'] != user_id and user_role != 'admin':
            flash('You do not have permission to delete this business.', 'error')
            return redirect(url_for('user.profile'))

        business_name = business['business_name']

        # Delete from join table
        cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))

        # Delete business
        cur.execute("DELETE FROM businesses WHERE id = %s", (business_id,))

        conn.commit()
        flash(f'Business "{business_name}" has been deleted.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error deleting business: {str(e)}', 'error')
    finally:
        if conn:
            conn.close()

    return redirect(request.referrer)


# # Assign a business to a user.
# @bp.route('/admin/business/<int:business_id>/assign', methods=['GET', 'POST'])
# @admin_required
# def admin_assign_business(business_id):
#     """Assign business to a different owner"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         if request.method == 'POST':
#             new_owner_id = request.form.get('owner_id')
            
#             # Verify new owner exists
#             cur.execute("SELECT id, username FROM users WHERE id = %s", (new_owner_id,))
#             new_owner = cur.fetchone()
            
#             if not new_owner:
#                 flash('Invalid owner selected', 'error')
#                 return redirect(url_for('user.admin_assign_business', business_id=business_id))
            
#             # Get current business details
#             cur.execute("SELECT business_name, owner_id FROM businesses WHERE id = %s", (business_id,))
#             business = cur.fetchone()
#             print(business)
#             if not business:
#                 flash('Business not found', 'error')
#                 return redirect(url_for('user.admin_businesses'))
            
#             # Update ownership
#             cur.execute("""
#                 UPDATE businesses 
#                 SET owner_id = %s
#                 WHERE id = %s
#             """, (new_owner_id, business_id))
            
#             conn.commit()
#             flash(f'Business "{business["business_name"]}" assigned to {new_owner["username"]}', 'success')
#             return redirect(url_for('user.admin_businesses'))
        
#         # GET request - load form
#         # Get current business info
#         cur.execute("""
#             SELECT b.id, b.business_name, u.id as owner_id, u.username as owner_name
#             FROM businesses b
#             JOIN users u ON b.owner_id = u.id
#             WHERE b.id = %s
#         """, (business_id,))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found', 'error')
#             return redirect(url_for('user.admin_businesses'))
            
#         # Get all potential owners (users with owner or admin role)
#         cur.execute("""
#             SELECT id, username, email 
#             FROM users 
#             WHERE role IN ('owner', 'admin')
#             ORDER BY username
#         """)
#         owners = cur.fetchall()
        
#         return render_template('admin_assign_business.html', 
#                              business=business,
#                              owners=owners)
#     except Exception as e:
#         conn.rollback()
#         traceback.print_exception(e)
#         flash(f'Error assigning business: {str(e)}', 'error')
#         return redirect(url_for('user.admin_businesses'))
#     finally:
#         if conn:
#             conn.close()

# 
@bp.route('/admin/business/<int:business_id>/assign', methods=['GET', 'POST'])
@admin_required
def admin_assign_business(business_id):
    """Assign business to a different owner"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # First verify business exists
        cur.execute("SELECT id, business_name FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash(f'Business with ID {business_id} not found', 'error')
            return redirect(url_for('user.admin_businesses'))
        
        print(f"Found business: {business}")  # Debug print
        
        if request.method == 'POST':
            new_owner_id = request.form.get('owner_id')
            
            if not new_owner_id:
                flash('No owner selected', 'error')
                return redirect(url_for('user.admin_assign_business', business_id=business_id))
            
            # Verify new owner exists
            cur.execute("SELECT id, username FROM users WHERE id = %s", (new_owner_id,))
            new_owner = cur.fetchone()
            
            if not new_owner:
                flash('Invalid owner selected', 'error')
                return redirect(url_for('user.admin_assign_business', business_id=business_id))
            
            print(f"Assigning business {business_id} to user {new_owner_id}")  # Debug print
            
            # Update ownership
            cur.execute("""
                UPDATE businesses 
                SET owner_id = %s
                WHERE id = %s
            """, (new_owner_id, business_id))
            
            conn.commit()
            flash(f'Business "{business["business_name"]}" assigned to {new_owner["username"]}', 'success')
            return redirect(url_for('user.admin_businesses'))
        
        # GET request - load form
        # Get current owner info
        cur.execute("""
            SELECT u.id, u.username
            FROM users u
            JOIN businesses b ON b.owner_id = u.id
            WHERE b.id = %s
        """, (business_id,))
        current_owner = cur.fetchone()
        
        # Get all potential owners (users with owner or admin role)
        cur.execute("""
            SELECT id, username, email 
            FROM users 
            WHERE role IN ('owner', 'admin')
            ORDER BY username
        """)
        owners = cur.fetchall()
        
        return render_template('admin_assign_business.html', 
                            business={
                                'id': business_id,
                                'name': business['business_name'],
                                'current_owner': current_owner
                            },
                            owners=owners)
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error in admin_assign_business: {str(e)}")
        traceback.print_exc()
        flash(f'Error assigning business: {str(e)}', 'error')
        return redirect(url_for('user.admin_businesses'))
    finally:
        if conn:
            conn.close()



# @bp.route('/update_business_status/<int:business_id>', methods=['POST'])
# def update_business_status(business_id):
#     """Update business status (for admin and user actions)"""
#     if 'user_id' not in session:
#         flash('Please log in to perform this action.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     new_status = request.form.get('status')
    
#     if not new_status or new_status not in ['active', 'suspended', 'pending']:
#         flash('Invalid status provided.', 'error')
#         return redirect(request.referrer)

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor()
        
#         # Verify ownership and update status
#         cur.execute("""
#             UPDATE businesses 
#             SET status = %s
#             WHERE id = %s AND owner_id = %s
#             RETURNING business_name
#         """, (new_status, business_id, user_id))
        
#         result = cur.fetchone()
#         if not result:
#             flash('Business not found or you do not have permission.', 'error')
#         else:
#             conn.commit()
#             flash(f'Business "{result[0]}" status updated to {new_status}.', 'success')
            
#     except Exception as e:
#         traceback.print_exception(e)
#         conn.rollback()
#         flash(f'Error updating status: {str(e)}', 'error')
#     finally:
#         if conn:
#             conn.close()
    
#     return redirect(request.referrer)

# 
# @bp.route('/update_business_status/<int:business_id>', methods=['POST'])
# def update_business_status(business_id):
#     """Update business status (for admin and user actions)"""
#     if 'user_id' not in session:
#         flash('Please log in to perform this action.', 'error')
#         return redirect(url_for('auth.login'))

#     user_id = session['user_id']
#     new_status = request.form.get('status')
    
#     if not new_status or new_status not in ['active', 'suspended', 'pending']:
#         flash('Invalid status provided.', 'error')
#         return redirect(url_for('user.profile'))

#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # First get the business name
#         cur.execute("""
#             SELECT business_name FROM businesses 
#             WHERE id = %s AND owner_id = %s
#         """, (business_id, user_id))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found or you do not have permission.', 'error')
#             flash('Business not found or you do not have permission.', 'danger')
#             return redirect(url_for('user.profile'))
        
#         # Update the status
#         cur.execute("""
#             UPDATE businesses 
#             SET status = %s
#             WHERE id = %s AND owner_id = %s
#         """, (new_status, business_id, user_id))
        
#         conn.commit()
#         flash(f'Business "{business["business_name"]}" status updated to {new_status}.', 'success')
        
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error updating status: {str(e)}', 'error')
#     finally:
#         if conn:
#             conn.close()
    
#     return redirect(request.referrer)

@bp.route('/update_business_status/<int:business_id>', methods=['POST'])
def update_business_status(business_id):
    """Update business status (admin or business owner only)"""
    if 'user_id' not in session:
        flash('Please log in to perform this action.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    new_status = request.form.get('status')

    if not new_status or new_status not in ['active', 'suspended', 'pending']:
        flash('Invalid status provided.', 'error')
        return redirect(url_for('user.profile'))

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)

        # Get user role
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        is_admin = user and user['role'] == 'admin'

        # Get the business and check access permission
        cur.execute("SELECT business_name, owner_id FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()

        if not business:
            flash('Business not found.', 'error')
            return redirect(request.referrer)

        if not is_admin and business['owner_id'] != user_id:
            flash('You do not have permission to update this business.', 'danger')
            return redirect(request.referrer)

        # Update status
        cur.execute("""
            UPDATE businesses 
            SET status = %s 
            WHERE id = %s
        """, (new_status, business_id))
        conn.commit()

        flash(f'Business "{business["business_name"]}" status updated to {new_status}.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(request.referrer or url_for('user.profile'))

# BUSINESS SUBSCRIPTION STATUS UPDATES:
@bp.route('/business/<int:business_id>/subscription', methods=['POST'])
# @admin_required_v2(allowed_roles=['superadmin', 'admin' 'billing_admin'])  # Restrict to certain admins
@admin_required
def update_business_subscription(business_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)

        # Ensure the business exists
        cur.execute("SELECT * FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()
        if not business:
            flash('Business not found.', 'error')
            return redirect(request.referrer)

        action = request.form.get("action")

        # Toggle subscription
        if action == "toggle_subscription":
            is_subscribed = 'is_subscribed' in request.form
            cur.execute("""
                UPDATE businesses 
                SET is_subscribed = %s 
                WHERE id = %s
            """, (is_subscribed, business_id))
            conn.commit()
            flash('Subscription status updated.', 'success')

        # Update subscription plan
        elif action == "update_plan":
            subscription_plan_id = request.form.get('subscription_plan')
            if not subscription_plan_id or not subscription_plan_id.isdigit():
                flash('Invalid subscription plan selected.', 'error')
                return redirect(url_for('user.business_profile', business_id=business_id))

            cur.execute("""
                UPDATE subscriptions 
                SET plan_id = %s, business_id= %s
                WHERE id = %s
            """, (int(subscription_plan_id), business_id))
            conn.commit()
            flash('Subscription plan updated.', 'success')

        else:
            flash('Invalid action.', 'error')

    except Exception as e:
        conn.rollback()
        flash(f'Error updating subscription: {str(e)}', 'error')

    finally:
        conn.close()

    return redirect(request.referrer)

# 
# import os
# import traceback
# from flask import Blueprint, current_app as app, request, render_template, redirect, session, url_for, flash
# from utils import allowed_file, get_db_connection
# from werkzeug.utils import secure_filename
# from werkzeug.security import generate_password_hash, check_password_hash
# from functools import wraps

# # bp = Blueprint('user', __name__)
# admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# # ======================
# # HELPER FUNCTIONS
# # ======================

# def admin_required(f):
#     """Decorator to ensure user has admin privileges"""
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session or session.get('role') != 'admin':
#             flash('Administrator access required', 'error')
#             return redirect(url_for('auth.login'))
#         return f(*args, **kwargs)
#     return decorated_function

# def owner_or_admin_required(business_id):
#     """Decorator factory to ensure user is owner or admin"""
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             if 'user_id' not in session:
#                 flash('Please log in to access this page.', 'error')
#                 return redirect(url_for('auth.login'))
            
#             conn = get_db_connection()
#             try:
#                 cur = conn.cursor()
#                 cur.execute("""
#                     SELECT owner_id, status FROM businesses WHERE id = %s
#                 """, (business_id,))
#                 business = cur.fetchone()
                
#                 if not business:
#                     flash('Business not found', 'error')
#                     return redirect(url_for('user.profile'))
                
#                 if session['user_id'] != business[0] and session.get('role') != 'admin':
#                     flash('You do not have permission to access this resource', 'error')
#                     return redirect(url_for('user.profile'))
                
#                 return f(*args, **kwargs)
#             finally:
#                 if conn:
#                     conn.close()
#         return decorated_function
#     return decorator

# def upload_file(file):
#     """Handle file uploads and return properly formatted full web URL"""
#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
#         upload_folder = app.config['UPLOAD_FOLDER']
#         os.makedirs(upload_folder, exist_ok=True)
#         file_path = os.path.join(upload_folder, filename)
#         file.save(file_path)
#         base_url = request.host_url.rstrip('/')
#         static_path = f"/static/uploads/{filename}"
#         return f"{base_url}{static_path}"
#     return None

# # ======================
# # USER ROUTES (EXISTING)
# # ======================
# # ... [Keep all existing user routes exactly as they are] ...

# # ======================
# # ADMIN ROUTES (NEW)
# # ======================

# @admin_bp.route('/dashboard')
# @admin_required
# def dashboard():
#     """Admin dashboard with system overview"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # Get system statistics
#         cur.execute("""
#             SELECT 
#                 (SELECT COUNT(*) FROM users) as total_users,
#                 (SELECT COUNT(*) FROM businesses) as total_businesses,
#                 (SELECT COUNT(*) FROM businesses WHERE status = 'active') as active_businesses,
#                 (SELECT COUNT(*) FROM businesses WHERE status = 'pending') as pending_businesses,
#                 (SELECT COUNT(*) FROM businesses WHERE status = 'suspended') as suspended_businesses,
#                 (SELECT COUNT(*) FROM businesses WHERE is_subscribed = TRUE) as subscribed_businesses
#         """)
#         stats = cur.fetchone()
        
#         # Get recent activities
#         cur.execute("""
#             SELECT a.*, u.username as actor_name 
#             FROM admin_activities a
#             JOIN users u ON a.admin_id = u.id
#             ORDER BY a.created_at DESC
#             LIMIT 10
#         """)
#         activities = cur.fetchall()
        
#         return render_template('admin_dashboard.html', 
#                              stats=stats,
#                              activities=activities)
#     except Exception as e:
#         flash(f'Error loading dashboard: {str(e)}', 'error')
#         return redirect(url_for('admin.dashboard'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/users')
# @admin_required
# def manage_users():
#     """List all users with management options"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
#         cur.execute("""
#             SELECT u.*, 
#                    COUNT(b.id) as business_count,
#                    CASE WHEN u.role = 'admin' THEN 'Admin'
#                         WHEN u.role = 'owner' THEN 'Business Owner'
#                         ELSE 'Regular User' END as role_display
#             FROM users u
#             LEFT JOIN businesses b ON u.id = b.owner_id
#             GROUP BY u.id
#             ORDER BY u.created_at DESC
#         """)
#         users = cur.fetchall()
#         return render_template('admin_users.html', users=users)
#     except Exception as e:
#         flash(f'Error loading users: {str(e)}', 'error')
#         return redirect(url_for('admin.dashboard'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
# @admin_required
# def edit_user(user_id):
#     """Edit user details and role"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         if request.method == 'POST':
#             # Handle form submission
#             username = request.form.get('username')
#             email = request.form.get('email')
#             role = request.form.get('role')
#             is_active = request.form.get('is_active') == 'on'
            
#             cur.execute("""
#                 UPDATE users 
#                 SET username = %s, email = %s, role = %s, is_active = %s
#                 WHERE id = %s
#                 RETURNING *
#             """, (username, email, role, is_active, user_id))
#             updated_user = cur.fetchone()
#             conn.commit()
            
#             # Log admin activity
#             cur.execute("""
#                 INSERT INTO admin_activities (admin_id, action, details)
#                 VALUES (%s, 'user_update', %s)
#             """, (session['user_id'], f"Updated user {updated_user['username']} (ID: {user_id})"))
#             conn.commit()
            
#             flash('User updated successfully', 'success')
#             return redirect(url_for('admin.manage_users'))
        
#         # GET request - load user data
#         cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#         user = cur.fetchone()
        
#         if not user:
#             flash('User not found', 'error')
#             return redirect(url_for('admin.manage_users'))
            
#         return render_template('admin_edit_user.html', user=user)
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error updating user: {str(e)}', 'error')
#         return redirect(url_for('admin.manage_users'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/businesses')
# @admin_required
# def manage_businesses():
#     """List all businesses with management options"""
#     conn = get_db_connection()
#     try:
#         status_filter = request.args.get('status', 'all')
        
#         base_query = """
#             SELECT b.*, 
#                    u.username as owner_name,
#                    CASE 
#                        WHEN b.status = 'active' THEN 'Active'
#                        WHEN b.status = 'pending' THEN 'Pending Approval'
#                        WHEN b.status = 'suspended' THEN 'Suspended'
#                        ELSE b.status
#                    END as status_display
#             FROM businesses b
#             JOIN users u ON b.owner_id = u.id
#         """
        
#         params = []
#         if status_filter != 'all':
#             base_query += " WHERE b.status = %s"
#             params.append(status_filter)
            
#         base_query += " ORDER BY b.created_at DESC"
        
#         cur = conn.cursor(dictionary=True)
#         cur.execute(base_query, params)
#         businesses = cur.fetchall()
        
#         return render_template('admin_businesses.html', 
#                             businesses=businesses,
#                             current_filter=status_filter)
#     except Exception as e:
#         flash(f'Error loading businesses: {str(e)}', 'error')
#         return redirect(url_for('admin.dashboard'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/businesses/<int:business_id>', methods=['GET', 'POST'])
# @admin_required
# def edit_business(business_id):
#     """Edit business details as admin"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         if request.method == 'POST':
#             # Handle form submission
#             business_name = request.form.get('business_name')
#             description = request.form.get('description')
#             status = request.form.get('status')
#             is_verified = request.form.get('is_verified') == 'on'
#             is_subscribed = request.form.get('is_subscribed') == 'on'
            
#             cur.execute("""
#                 UPDATE businesses 
#                 SET business_name = %s, description = %s, 
#                     status = %s, is_verified = %s, is_subscribed = %s
#                 WHERE id = %s
#                 RETURNING *
#             """, (business_name, description, status, is_verified, is_subscribed, business_id))
#             updated_business = cur.fetchone()
#             conn.commit()
            
#             # Log admin activity
#             cur.execute("""
#                 INSERT INTO admin_activities (admin_id, action, details)
#                 VALUES (%s, 'business_update', %s)
#             """, (session['user_id'], f"Updated business {updated_business['business_name']} (ID: {business_id})"))
#             conn.commit()
            
#             flash('Business updated successfully', 'success')
#             return redirect(url_for('admin.manage_businesses'))
        
#         # GET request - load business data
#         cur.execute("""
#             SELECT b.*, u.username as owner_name
#             FROM businesses b
#             JOIN users u ON b.owner_id = u.id
#             WHERE b.id = %s
#         """, (business_id,))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found', 'error')
#             return redirect(url_for('admin.manage_businesses'))
            
#         return render_template('admin_edit_business.html', business=business)
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error updating business: {str(e)}', 'error')
#         return redirect(url_for('admin.manage_businesses'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/businesses/<int:business_id>/assign', methods=['GET', 'POST'])
# @admin_required
# def assign_business(business_id):
#     """Assign business to a different owner"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         if request.method == 'POST':
#             new_owner_id = request.form.get('owner_id')
            
#             # Verify new owner exists and is a business owner
#             cur.execute("SELECT id, username FROM users WHERE id = %s AND role = 'owner'", (new_owner_id,))
#             new_owner = cur.fetchone()
            
#             if not new_owner:
#                 flash('Invalid owner selected', 'error')
#                 return redirect(url_for('admin.assign_business', business_id=business_id))
            
#             # Get current business details for logging
#             cur.execute("SELECT business_name, owner_id FROM businesses WHERE id = %s", (business_id,))
#             business = cur.fetchone()
            
#             if not business:
#                 flash('Business not found', 'error')
#                 return redirect(url_for('admin.manage_businesses'))
            
#             # Update ownership
#             cur.execute("""
#                 UPDATE businesses 
#                 SET owner_id = %s
#                 WHERE id = %s
#                 RETURNING *
#             """, (new_owner_id, business_id))
#             conn.commit()
            
#             # Log admin activity
#             cur.execute("""
#                 INSERT INTO admin_activities (admin_id, action, details)
#                 VALUES (%s, 'business_reassign', %s)
#             """, (session['user_id'], 
#                  f"Reassigned business {business['business_name']} from user {business['owner_id']} to {new_owner_id}"))
#             conn.commit()
            
#             flash(f'Business successfully assigned to {new_owner["username"]}', 'success')
#             return redirect(url_for('admin.manage_businesses'))
        
#         # GET request - load form
#         cur.execute("SELECT id, username FROM users WHERE role = 'owner' ORDER BY username")
#         owners = cur.fetchall()
        
#         cur.execute("""
#             SELECT b.id, b.business_name, u.id as owner_id, u.username as owner_name
#             FROM businesses b
#             JOIN users u ON b.owner_id = u.id
#             WHERE b.id = %s
#         """, (business_id,))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found', 'error')
#             return redirect(url_for('admin.manage_businesses'))
            
#         return render_template('admin_assign_business.html', 
#                              business=business,
#                              owners=owners)
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error assigning business: {str(e)}', 'error')
#         return redirect(url_for('admin.manage_businesses'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/businesses/<int:business_id>/verify', methods=['POST'])
# @admin_required
# def verify_business(business_id):
#     """Verify a business as legitimate"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # Get business name for logging
#         cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found', 'error')
#             return redirect(url_for('admin.manage_businesses'))
        
#         # Update verification status
#         cur.execute("""
#             UPDATE businesses 
#             SET is_verified = TRUE
#             WHERE id = %s
#         """, (business_id,))
#         conn.commit()
        
#         # Log admin activity
#         cur.execute("""
#             INSERT INTO admin_activities (admin_id, action, details)
#             VALUES (%s, 'business_verify', %s)
#         """, (session['user_id'], f"Verified business {business['business_name']} (ID: {business_id})"))
#         conn.commit()
        
#         flash('Business successfully verified', 'success')
#         return redirect(url_for('admin.manage_businesses'))
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error verifying business: {str(e)}', 'error')
#         return redirect(url_for('admin.manage_businesses'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/businesses/<int:business_id>/suspend', methods=['POST'])
# @admin_required
# def suspend_business(business_id):
#     """Suspend a business account"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # Get business name for logging
#         cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found', 'error')
#             return redirect(url_for('admin.manage_businesses'))
        
#         # Update status to suspended
#         cur.execute("""
#             UPDATE businesses 
#             SET status = 'suspended'
#             WHERE id = %s
#         """, (business_id,))
#         conn.commit()
        
#         # Log admin activity
#         cur.execute("""
#             INSERT INTO admin_activities (admin_id, action, details)
#             VALUES (%s, 'business_suspend', %s)
#         """, (session['user_id'], f"Suspended business {business['business_name']} (ID: {business_id})"))
#         conn.commit()
        
#         flash('Business successfully suspended', 'success')
#         return redirect(url_for('admin.manage_businesses'))
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error suspending business: {str(e)}', 'error')
#         return redirect(url_for('admin.manage_businesses'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/businesses/<int:business_id>/activate', methods=['POST'])
# @admin_required
# def activate_business(business_id):
#     """Activate a suspended business"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # Get business name for logging
#         cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found', 'error')
#             return redirect(url_for('admin.manage_businesses'))
        
#         # Update status to active
#         cur.execute("""
#             UPDATE businesses 
#             SET status = 'active'
#             WHERE id = %s
#         """, (business_id,))
#         conn.commit()
        
#         # Log admin activity
#         cur.execute("""
#             INSERT INTO admin_activities (admin_id, action, details)
#             VALUES (%s, 'business_activate', %s)
#         """, (session['user_id'], f"Activated business {business['business_name']} (ID: {business_id})"))
#         conn.commit()
        
#         flash('Business successfully activated', 'success')
#         return redirect(url_for('admin.manage_businesses'))
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error activating business: {str(e)}', 'error')
#         return redirect(url_for('admin.manage_businesses'))
#     finally:
#         if conn:
#             conn.close()

# @admin_bp.route('/businesses/<int:business_id>/delete', methods=['POST'])
# @admin_required
# def delete_business(business_id):
#     """Permanently delete a business"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # Get business name for logging
#         cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
#         business = cur.fetchone()
        
#         if not business:
#             flash('Business not found', 'error')
#             return redirect(url_for('admin.manage_businesses'))
        
#         # Delete business categories first
#         cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))
        
#         # Then delete the business
#         cur.execute("DELETE FROM businesses WHERE id = %s", (business_id,))
#         conn.commit()
        
#         # Log admin activity
#         cur.execute("""
#             INSERT INTO admin_activities (admin_id, action, details)
#             VALUES (%s, 'business_delete', %s)
#         """, (session['user_id'], f"Deleted business {business['business_name']} (ID: {business_id})"))
#         conn.commit()
        
#         flash('Business successfully deleted', 'success')
#         return redirect(url_for('admin.manage_businesses'))
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error deleting business: {str(e)}', 'error')
#         return redirect(url_for('admin.manage_businesses'))
#     finally:
#         if conn:
#             conn.close()

# # ======================
# # BUSINESS MEDIA PROTECTION
# # ======================

# @bp.route('/business/<int:business_id>/update_media', methods=['POST'])
# # @owner_or_admin_required(business_id)
# def update_business_media(business_id):
#     """Update business media (protected route)"""
#     conn = get_db_connection()
#     try:
#         cur = conn.cursor(dictionary=True)
        
#         # Check if business is subscribed (admin bypasses this check)
#         if session.get('role') != 'admin':
#             cur.execute("SELECT is_subscribed FROM businesses WHERE id = %s", (business_id,))
#             business = cur.fetchone()
            
#             if not business or not business['is_subscribed']:
#                 flash('Only subscribed businesses can update their media', 'error')
#                 return redirect(url_for('user.business_profile', business_id=business_id))
        
#         # Handle file upload
#         file = request.files.get('business_media')
#         if file and file.filename:
#             file_path = upload_file(file)
#             if file_path:
#                 cur.execute("""
#                     UPDATE businesses 
#                     SET media_url = %s, media_type = 'image'
#                     WHERE id = %s
#                 """, (file_path, business_id))
#                 conn.commit()
#                 flash('Business media updated successfully!', 'success')
        
#         return redirect(url_for('user.business_profile', business_id=business_id))
#     except Exception as e:
#         conn.rollback()
#         flash(f'Error updating media: {str(e)}', 'error')
#         return redirect(url_for('user.business_profile', business_id=business_id))
#     finally:
#         if conn:
#             conn.close()



# 
# 
# 
# 
# 
# 
# 
# 
# 
# ======================
# SEARCH ROUTE
# ======================

# @bp.route('/search')
# def search_business():
#     """Search businesses by name, category, or shop number"""
#     search_query = request.args.get('search_query', '').strip()
#     page = request.args.get('page', 1, type=int)
#     category_filter = request.args.get('category', None)
    
#     if not search_query and not category_filter:
#         flash('Please enter a search term or select a category', 'info')
#         return redirect(url_for('index.home'))
    
#     conn = None
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)
        
#         # Pagination settings
#         per_page = 12
#         offset = (page - 1) * per_page
        
#         # Base query with joins
#         base_query = """
#             SELECT 
#                 b.*,
#                 u.username as owner_username,
#                 GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
#                 COUNT(DISTINCT c.id) as category_count,
#                 MIN(c.category_name) as primary_category,
#                 CASE 
#                     WHEN b.status = 'active' THEN 0 
#                     WHEN b.status = 'pending' THEN 1
#                     ELSE 2 
#                 END as status_order
#             FROM businesses b
#             LEFT JOIN users u ON b.owner_id = u.id
#             LEFT JOIN business_categories bc ON b.id = bc.business_id
#             LEFT JOIN categories c ON bc.category_id = c.id
#             WHERE b.status != 'deleted'
#         """
        
#         # Add search conditions
#         conditions = []
#         params = []
        
#         if search_query:
#             conditions.append("""
#                 (b.business_name LIKE %s OR 
#                 b.description LIKE %s OR 
#                 b.shop_no LIKE %s OR 
#                 c.category_name LIKE %s)
#             """)
#             search_term = f"%{search_query}%"
#             params.extend([search_term, search_term, search_term, search_term])
        
#         if category_filter:
#             conditions.append("c.id = %s")
#             params.append(category_filter)
        
#         if conditions:
#             base_query += " AND " + " AND ".join(conditions)
        
#         # Add grouping and ordering
#         base_query += """
#             GROUP BY b.id
#             ORDER BY b.is_subscribed DESC, 
#                      status_order,
#                      b.created_at DESC
#         """
        
#         # Get total count
#         count_query = f"SELECT COUNT(DISTINCT b.id) as total FROM ({base_query}) as filtered"
#         cur.execute(count_query, params)
#         total = cur.fetchone()['total']
        
#         # Add pagination
#         base_query += " LIMIT %s OFFSET %s"
#         params.extend([per_page, offset])
        
#         # Execute main query
#         cur.execute(base_query, params)
#         businesses = cur.fetchall()
        
#         # Process the businesses data
#         for biz in businesses:
#             biz['additional_categories'] = biz['category_count'] - 1 if biz['category_count'] else 0
        
#         # Get all categories for filter dropdown
#         cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
#         all_categories = cur.fetchall()
        
#         return render_template('search_results.html', 
#                             businesses=businesses,
#                             search_query=search_query,
#                             selected_category=category_filter,
#                             all_categories=all_categories,
#                             username=session.get('username'),
#                             user_profile=session.get('profile_image'),
#                             pagination={
#                                 'page': page,
#                                 'per_page': per_page,
#                                 'total': total,
#                                 'has_next': offset + per_page < total,
#                                 'has_prev': page > 1
#                             })

#     except Exception as e:
#         traceback.print_exc()
#         app.logger.error(f"Search error: {str(e)}")
#         flash('Error performing search. Please try again later.', 'error')
#         return redirect(url_for('index.home'))
#     finally:
#         if conn:
#             conn.close()

@bp.route('/search_business')
def search_business():
    """Search businesses by name, category, or shop number"""
    search_query = request.args.get('search_query', '').strip()
    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category', None)
    
    if not search_query and not category_filter:
        flash('Please enter a search term or select a category', 'info')
        return redirect(url_for('index.home'))
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Pagination settings
        per_page = 12
        offset = (page - 1) * per_page
        
        # Base query with joins
        base_query = """
            SELECT 
                b.*,
                u.username as owner_username,
                GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
                COUNT(DISTINCT c.id) as category_count,
                MIN(c.category_name) as primary_category,
                CASE 
                    WHEN b.status = 'active' THEN 0 
                    WHEN b.status = 'pending' THEN 1
                    ELSE 2 
                END as status_order
            FROM businesses b
            LEFT JOIN users u ON b.owner_id = u.id
            LEFT JOIN business_categories bc ON b.id = bc.business_id
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE b.status != 'deleted'
        """
        
        # Count query (simpler version without all the fields)
        count_query = """
            SELECT COUNT(DISTINCT b.id) as total
            FROM businesses b
            LEFT JOIN business_categories bc ON b.id = bc.business_id
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE b.status != 'deleted'
        """
        
        # Add search conditions
        conditions = []
        params = []
        
        if search_query:
            condition = """
                (b.business_name LIKE %s OR 
                b.description LIKE %s OR 
                b.shop_no LIKE %s OR 
                c.category_name LIKE %s)
            """
            conditions.append(condition)
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        if category_filter:
            conditions.append("c.id = %s")
            params.append(category_filter)
        
        if conditions:
            where_clause = " AND " + " AND ".join(conditions)
            base_query += where_clause
            count_query += where_clause
        
        # Add grouping and ordering to main query
        base_query += """
            GROUP BY b.id
            ORDER BY b.is_subscribed DESC, 
                     status_order,
                     b.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        # Execute count query
        cur.execute(count_query, params)
        total = cur.fetchone()['total']
        
        # Add pagination params
        params.extend([per_page, offset])
        
        # Execute main query
        cur.execute(base_query, params)
        businesses = cur.fetchall()
        
        # Process the businesses data
        for biz in businesses:
            biz['additional_categories'] = biz['category_count'] - 1 if biz['category_count'] else 0
        
        # Get all categories for filter dropdown
        cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
        all_categories = cur.fetchall()
        
        return render_template('search_results.html', 
                            businesses=businesses,
                            search_query=search_query,
                            selected_category=category_filter,
                            all_categories=all_categories,
                            username=session.get('username'),
                            user_profile=session.get('profile_image'),
                            pagination={
                                'page': page,
                                'per_page': per_page,
                                'total': total,
                                'has_next': offset + per_page < total,
                                'has_prev': page > 1
                            })

    except Exception as e:
        traceback.print_exc()
        app.logger.error(f"Search error: {str(e)}")
        flash('Error performing search. Please try again later.', 'error')
        return redirect(url_for('index.home'))
    finally:
        if conn:
            conn.close()

# ======================
# CATEGORY ROUTE
# ======================

@bp.route('/category/<int:category_id>')
@bp.route('/category/<int:category_id>/page/<int:page>')
def businesses_by_category(category_id, page=1):
    """Show all businesses in a specific category"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # First verify category exists
        cur.execute("SELECT id, category_name FROM categories WHERE id = %s", (category_id,))
        category = cur.fetchone()
        
        if not category:
            flash('Category not found', 'error')
            return redirect(url_for('index.home'))
        
        # Pagination settings
        per_page = 12
        offset = (page - 1) * per_page
        
        # Get total count for pagination
        cur.execute("""
            SELECT COUNT(DISTINCT b.id) as total 
            FROM businesses b
            JOIN business_categories bc ON b.id = bc.business_id
            WHERE bc.category_id = %s AND b.status != 'deleted'
        """, (category_id,))
        total = cur.fetchone()['total']
        
        # Get businesses in this category
        cur.execute("""
            SELECT 
                b.*,
                u.username as owner_username,
                GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
                COUNT(DISTINCT c.id) as category_count,
                MIN(c.category_name) as primary_category,
                CASE 
                    WHEN b.status = 'active' THEN 0 
                    WHEN b.status = 'pending' THEN 1
                    ELSE 2 
                END as status_order
            FROM businesses b
            JOIN business_categories bc ON b.id = bc.business_id
            JOIN categories c ON bc.category_id = c.id
            LEFT JOIN users u ON b.owner_id = u.id
            WHERE bc.category_id = %s AND b.status != 'deleted'
            GROUP BY b.id
            ORDER BY b.is_subscribed DESC, 
                     status_order,
                     b.created_at DESC
            LIMIT %s OFFSET %s
        """, (category_id, per_page, offset))
        
        businesses = cur.fetchall()
        
        # Process the businesses data
        for biz in businesses:
            biz['additional_categories'] = biz['category_count'] - 1 if biz['category_count'] else 0
        
        # Get all categories for sidebar
        cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
        all_categories = cur.fetchall()
        
        return render_template('category_businesses.html', 
                            businesses=businesses,
                            category=category,
                            all_categories=all_categories,
                            username=session.get('username'),
                            user_profile=session.get('profile_image'),
                            pagination={
                                'page': page,
                                'per_page': per_page,
                                'total': total,
                                'has_next': offset + per_page < total,
                                'has_prev': page > 1
                            })

    except Exception as e:
        traceback.print_exc()
        app.logger.error(f"Category page error: {str(e)}")
        flash('Error loading category. Please try again later.', 'error')
        return redirect(url_for('index.home'))
    finally:
        if conn:
            conn.close()