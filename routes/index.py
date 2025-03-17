import traceback
from flask import Blueprint, render_template, redirect, session, url_for, flash
from utils import get_db_connection

bp = Blueprint('index', __name__)

@bp.route('/')
def home():
    conn = None
    try:
        if 'user_id' in session:  # Assuming user_id is stored in session after login
            flash('You are being redirected to your profile because you are already logged in.', 'success')
            return redirect(url_for('user.update_profile'))

        username = session.get('username')
        user_profile = None

        conn = get_db_connection()
        businesses = []

        cur = conn.cursor(dictionary=True)

        # Fetch businesses, with subscribed businesses coming first
        """ This will fetch the businesses with subscribed ones at the top of the list, followed by non-subscribed ones, both ordered by their timestamp. """
        cur.execute("""
            SELECT * FROM businesses 
            ORDER BY is_subscribed DESC, timestamp DESC
        """)
        
        businesses = cur.fetchall()

        # Fetch user profile if username is available
        if username:
            cur.execute("SELECT username, profile_image FROM users WHERE username = %s", (username,))
            user_profile = cur.fetchone()

        cur.close()
        
        context = {
            "username": username,
            "businesses": businesses,
            "user_profile": user_profile
        }
        
        return render_template('index.html', **context)

    except Exception as e:
        traceback.print_exc()
        flash(f"Database error: {e}", 'error')
        print(f"{e}")
        return f"{e}"
        
    finally:
        if conn:
            conn.close()
