import os, traceback
from flask import Blueprint, current_app as app, request, render_template, redirect, session, url_for, flash
from utils.helpers import admin_required, get_db_connection, upload_file
from werkzeug.security import generate_password_hash

bp = Blueprint('user', __name__)

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


@bp.route('/admin/businesses')
@admin_required
def admin_businesses():
    """Admin view of all businesses"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
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

# BUSINESS STATUS UPDATES:
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

