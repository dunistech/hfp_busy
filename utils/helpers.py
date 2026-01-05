import os 
from flask import current_app as app, request, request, url_for, session, redirect, url_for, flash
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

from config import Config as config
allowed_extensions = config.ALLOWED_EXTENSIONS
# print(dir(config.Config))

# role/permission
from functools import wraps
from flask import abort, session

serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))


# 
# 

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


# 
# 

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
# def upload_file(file):
#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
#         file_path = os.path.join(config.UPLOAD_FOLDER, filename)
#         file.save(file_path)
#         return filename  
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
            cur.execute("SELECT id, category_name, slug FROM categories")
            result = cur.fetchall()
            # categories = {row['id']: row['category_name'] for row in result}  # Convert to dict

            categories = [{"id": row['id'], 'name': row['category_name'], 'slug': row['slug'] } for row in result]  # List of named tuples
            
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