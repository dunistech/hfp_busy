import os
import traceback
from flask import Blueprint, current_app as app, request, render_template, redirect, session, url_for, flash
from utils import allowed_file, get_db_connection
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# bp = Blueprint('user', __name__)
bp = Blueprint('admin', __name__, url_prefix='/admin')

# ======================
# HELPER FUNCTIONS
# ======================

def admin_required(f):
    """Decorator to ensure user has admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Administrator access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def owner_or_admin_required(business_id):
    """Decorator factory to ensure user is owner or admin"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))
            
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT owner_id, status FROM businesses WHERE id = %s
                """, (business_id,))
                business = cur.fetchone()
                
                if not business:
                    flash('Business not found', 'error')
                    return redirect(url_for('user.profile'))
                
                if session['user_id'] != business[0] and session.get('role') != 'admin':
                    flash('You do not have permission to access this resource', 'error')
                    return redirect(url_for('user.profile'))
                
                return f(*args, **kwargs)
            finally:
                if conn:
                    conn.close()
        return decorated_function
    return decorator

def upload_file(file):
    """Handle file uploads and return properly formatted full web URL"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        base_url = request.host_url.rstrip('/')
        static_path = f"/static/uploads/{filename}"
        return f"{base_url}{static_path}"
    return None

# ======================
# USER ROUTES (EXISTING)
# ======================
# ... [Keep all existing user routes exactly as they are] ...

# ======================
# ADMIN ROUTES (NEW)
# ======================

@bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with system overview"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get system statistics
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM businesses) as total_businesses,
                (SELECT COUNT(*) FROM businesses WHERE status = 'active') as active_businesses,
                (SELECT COUNT(*) FROM businesses WHERE status = 'pending') as pending_businesses,
                (SELECT COUNT(*) FROM businesses WHERE status = 'suspended') as suspended_businesses,
                (SELECT COUNT(*) FROM businesses WHERE is_subscribed = TRUE) as subscribed_businesses
        """)
        stats = cur.fetchone()
        
        # Get recent activities
        cur.execute("""
            SELECT a.*, u.username as actor_name 
            FROM admin_activities a
            JOIN users u ON a.admin_id = u.id
            ORDER BY a.created_at DESC
            LIMIT 10
        """)
        activities = cur.fetchall()
        
        return render_template('admin_dashboard.html', 
                             stats=stats,
                             activities=activities)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))
    finally:
        if conn:
            conn.close()

@bp.route('/users')
@admin_required
def manage_users():
    """List all users with management options"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT u.*, 
                   COUNT(b.id) as business_count,
                   CASE WHEN u.role = 'admin' THEN 'Admin'
                        WHEN u.role = 'owner' THEN 'Business Owner'
                        ELSE 'Regular User' END as role_display
            FROM users u
            LEFT JOIN businesses b ON u.id = b.owner_id
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        users = cur.fetchall()
        return render_template('admin_users.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))
    finally:
        if conn:
            conn.close()

@bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user details and role"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Handle form submission
            username = request.form.get('username')
            email = request.form.get('email')
            role = request.form.get('role')
            is_active = request.form.get('is_active') == 'on'
            
            cur.execute("""
                UPDATE users 
                SET username = %s, email = %s, role = %s, is_active = %s
                WHERE id = %s
                RETURNING *
            """, (username, email, role, is_active, user_id))
            updated_user = cur.fetchone()
            conn.commit()
            
            # Log admin activity
            cur.execute("""
                INSERT INTO admin_activities (admin_id, action, details)
                VALUES (%s, 'user_update', %s)
            """, (session['user_id'], f"Updated user {updated_user['username']} (ID: {user_id})"))
            conn.commit()
            
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        
        # GET request - load user data
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.manage_users'))
            
        return render_template('admin_edit_user.html', user=user)
    except Exception as e:
        conn.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
        return redirect(url_for('admin.manage_users'))
    finally:
        if conn:
            conn.close()

@bp.route('/businesses')
@admin_required
def manage_businesses():
    """List all businesses with management options"""
    conn = get_db_connection()
    try:
        status_filter = request.args.get('status', 'all')
        
        base_query = """
            SELECT b.*, 
                   u.username as owner_name,
                   CASE 
                       WHEN b.status = 'active' THEN 'Active'
                       WHEN b.status = 'pending' THEN 'Pending Approval'
                       WHEN b.status = 'suspended' THEN 'Suspended'
                       ELSE b.status
                   END as status_display
            FROM businesses b
            JOIN users u ON b.owner_id = u.id
        """
        
        params = []
        if status_filter != 'all':
            base_query += " WHERE b.status = %s"
            params.append(status_filter)
            
        base_query += " ORDER BY b.created_at DESC"
        
        cur = conn.cursor(dictionary=True)
        cur.execute(base_query, params)
        businesses = cur.fetchall()
        
        return render_template('admin_businesses.html', 
                            businesses=businesses,
                            current_filter=status_filter)
    except Exception as e:
        flash(f'Error loading businesses: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))
    finally:
        if conn:
            conn.close()

@bp.route('/businesses/<int:business_id>', methods=['GET', 'POST'])
@admin_required
def edit_business(business_id):
    """Edit business details as admin"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Handle form submission
            business_name = request.form.get('business_name')
            description = request.form.get('description')
            status = request.form.get('status')
            is_verified = request.form.get('is_verified') == 'on'
            is_subscribed = request.form.get('is_subscribed') == 'on'
            
            cur.execute("""
                UPDATE businesses 
                SET business_name = %s, description = %s, 
                    status = %s, is_verified = %s, is_subscribed = %s
                WHERE id = %s
                RETURNING *
            """, (business_name, description, status, is_verified, is_subscribed, business_id))
            updated_business = cur.fetchone()
            conn.commit()
            
            # Log admin activity
            cur.execute("""
                INSERT INTO admin_activities (admin_id, action, details)
                VALUES (%s, 'business_update', %s)
            """, (session['user_id'], f"Updated business {updated_business['business_name']} (ID: {business_id})"))
            conn.commit()
            
            flash('Business updated successfully', 'success')
            return redirect(url_for('admin.manage_businesses'))
        
        # GET request - load business data
        cur.execute("""
            SELECT b.*, u.username as owner_name
            FROM businesses b
            JOIN users u ON b.owner_id = u.id
            WHERE b.id = %s
        """, (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('admin.manage_businesses'))
            
        return render_template('admin_edit_business.html', business=business)
    except Exception as e:
        conn.rollback()
        flash(f'Error updating business: {str(e)}', 'error')
        return redirect(url_for('admin.manage_businesses'))
    finally:
        if conn:
            conn.close()

@bp.route('/businesses/<int:business_id>/assign', methods=['GET', 'POST'])
@admin_required
def assign_business(business_id):
    """Assign business to a different owner"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            new_owner_id = request.form.get('owner_id')
            
            # Verify new owner exists and is a business owner
            cur.execute("SELECT id, username FROM users WHERE id = %s AND role = 'owner'", (new_owner_id,))
            new_owner = cur.fetchone()
            
            if not new_owner:
                flash('Invalid owner selected', 'error')
                return redirect(url_for('admin.assign_business', business_id=business_id))
            
            # Get current business details for logging
            cur.execute("SELECT business_name, owner_id FROM businesses WHERE id = %s", (business_id,))
            business = cur.fetchone()
            
            if not business:
                flash('Business not found', 'error')
                return redirect(url_for('admin.manage_businesses'))
            
            # Update ownership
            cur.execute("""
                UPDATE businesses 
                SET owner_id = %s
                WHERE id = %s
                RETURNING *
            """, (new_owner_id, business_id))
            conn.commit()
            
            # Log admin activity
            cur.execute("""
                INSERT INTO admin_activities (admin_id, action, details)
                VALUES (%s, 'business_reassign', %s)
            """, (session['user_id'], 
                 f"Reassigned business {business['business_name']} from user {business['owner_id']} to {new_owner_id}"))
            conn.commit()
            
            flash(f'Business successfully assigned to {new_owner["username"]}', 'success')
            return redirect(url_for('admin.manage_businesses'))
        
        # GET request - load form
        cur.execute("SELECT id, username FROM users WHERE role = 'owner' ORDER BY username")
        owners = cur.fetchall()
        
        cur.execute("""
            SELECT b.id, b.business_name, u.id as owner_id, u.username as owner_name
            FROM businesses b
            JOIN users u ON b.owner_id = u.id
            WHERE b.id = %s
        """, (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('admin.manage_businesses'))
            
        return render_template('admin_assign_business.html', 
                             business=business,
                             owners=owners)
    except Exception as e:
        conn.rollback()
        flash(f'Error assigning business: {str(e)}', 'error')
        return redirect(url_for('admin.manage_businesses'))
    finally:
        if conn:
            conn.close()

@bp.route('/businesses/<int:business_id>/verify', methods=['POST'])
@admin_required
def verify_business(business_id):
    """Verify a business as legitimate"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get business name for logging
        cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('admin.manage_businesses'))
        
        # Update verification status
        cur.execute("""
            UPDATE businesses 
            SET is_verified = TRUE
            WHERE id = %s
        """, (business_id,))
        conn.commit()
        
        # Log admin activity
        cur.execute("""
            INSERT INTO admin_activities (admin_id, action, details)
            VALUES (%s, 'business_verify', %s)
        """, (session['user_id'], f"Verified business {business['business_name']} (ID: {business_id})"))
        conn.commit()
        
        flash('Business successfully verified', 'success')
        return redirect(url_for('admin.manage_businesses'))
    except Exception as e:
        conn.rollback()
        flash(f'Error verifying business: {str(e)}', 'error')
        return redirect(url_for('admin.manage_businesses'))
    finally:
        if conn:
            conn.close()

@bp.route('/businesses/<int:business_id>/suspend', methods=['POST'])
@admin_required
def suspend_business(business_id):
    """Suspend a business account"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get business name for logging
        cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('admin.manage_businesses'))
        
        # Update status to suspended
        cur.execute("""
            UPDATE businesses 
            SET status = 'suspended'
            WHERE id = %s
        """, (business_id,))
        conn.commit()
        
        # Log admin activity
        cur.execute("""
            INSERT INTO admin_activities (admin_id, action, details)
            VALUES (%s, 'business_suspend', %s)
        """, (session['user_id'], f"Suspended business {business['business_name']} (ID: {business_id})"))
        conn.commit()
        
        flash('Business successfully suspended', 'success')
        return redirect(url_for('admin.manage_businesses'))
    except Exception as e:
        conn.rollback()
        flash(f'Error suspending business: {str(e)}', 'error')
        return redirect(url_for('admin.manage_businesses'))
    finally:
        if conn:
            conn.close()

@bp.route('/businesses/<int:business_id>/activate', methods=['POST'])
@admin_required
def activate_business(business_id):
    """Activate a suspended business"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get business name for logging
        cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('admin.manage_businesses'))
        
        # Update status to active
        cur.execute("""
            UPDATE businesses 
            SET status = 'active'
            WHERE id = %s
        """, (business_id,))
        conn.commit()
        
        # Log admin activity
        cur.execute("""
            INSERT INTO admin_activities (admin_id, action, details)
            VALUES (%s, 'business_activate', %s)
        """, (session['user_id'], f"Activated business {business['business_name']} (ID: {business_id})"))
        conn.commit()
        
        flash('Business successfully activated', 'success')
        return redirect(url_for('admin.manage_businesses'))
    except Exception as e:
        conn.rollback()
        flash(f'Error activating business: {str(e)}', 'error')
        return redirect(url_for('admin.manage_businesses'))
    finally:
        if conn:
            conn.close()

@bp.route('/businesses/<int:business_id>/delete', methods=['POST'])
@admin_required
def delete_business(business_id):
    """Permanently delete a business"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Get business name for logging
        cur.execute("SELECT business_name FROM businesses WHERE id = %s", (business_id,))
        business = cur.fetchone()
        
        if not business:
            flash('Business not found', 'error')
            return redirect(url_for('admin.manage_businesses'))
        
        # Delete business categories first
        cur.execute("DELETE FROM business_categories WHERE business_id = %s", (business_id,))
        
        # Then delete the business
        cur.execute("DELETE FROM businesses WHERE id = %s", (business_id,))
        conn.commit()
        
        # Log admin activity
        cur.execute("""
            INSERT INTO admin_activities (admin_id, action, details)
            VALUES (%s, 'business_delete', %s)
        """, (session['user_id'], f"Deleted business {business['business_name']} (ID: {business_id})"))
        conn.commit()
        
        flash('Business successfully deleted', 'success')
        return redirect(url_for('admin.manage_businesses'))
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting business: {str(e)}', 'error')
        return redirect(url_for('admin.manage_businesses'))
    finally:
        if conn:
            conn.close()

# ======================
# BUSINESS MEDIA PROTECTION
# ======================

@bp.route('/business/<int:business_id>/update_media', methods=['POST'])
# @owner_or_admin_required(business_id)
def update_business_media(business_id):
    """Update business media (protected route)"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        
        # Check if business is subscribed (admin bypasses this check)
        if session.get('role') != 'admin':
            cur.execute("SELECT is_subscribed FROM businesses WHERE id = %s", (business_id,))
            business = cur.fetchone()
            
            if not business or not business['is_subscribed']:
                flash('Only subscribed businesses can update their media', 'error')
                return redirect(url_for('user.business_profile', business_id=business_id))
        
        # Handle file upload
        file = request.files.get('business_media')
        if file and file.filename:
            file_path = upload_file(file)
            if file_path:
                cur.execute("""
                    UPDATE businesses 
                    SET media_url = %s, media_type = 'image'
                    WHERE id = %s
                """, (file_path, business_id))
                conn.commit()
                flash('Business media updated successfully!', 'success')
        
        return redirect(url_for('user.business_profile', business_id=business_id))
    except Exception as e:
        conn.rollback()
        flash(f'Error updating media: {str(e)}', 'error')
        return redirect(url_for('user.business_profile', business_id=business_id))
    finally:
        if conn:
            conn.close()