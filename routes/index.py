import traceback
from flask import Blueprint, render_template, redirect, session, url_for, flash
from utils import get_db_connection
from flask import current_app as app

bp = Blueprint('index', __name__)

# @bp.route('/')
# def home():
#     conn = None
#     try:
#         # if 'user_id' in session:  # Assuming user_id is stored in session after login
#         #     flash('You are being redirected to your profile because you are already logged in.', 'success')
#         #     return redirect(url_for('user.profile'))

#         username = session.get('username')
#         user_profile = None

#         conn = get_db_connection()
#         businesses = []

#         cur = conn.cursor(dictionary=True)

#         # Fetch businesses, with subscribed businesses coming first
#         """ This will fetch the businesses with subscribed ones at the top of the list, followed by non-subscribed ones, both ordered by their timestamp. """
#         cur.execute("""
#             SELECT * FROM businesses 
#             ORDER BY is_subscribed DESC, timestamp DESC
#         """)
        
#         businesses = cur.fetchall()

#         # Fetch user profile if username is available
#         if username:
#             cur.execute("SELECT username, profile_image FROM users WHERE username = %s", (username,))
#             user_profile = cur.fetchone()

#         cur.close()
        
#         context = {
#             "username": username,
#             "businesses": businesses,
#             "user_profile": user_profile
#         }
        
#         return render_template('index.html', **context)

#     except Exception as e:
#         traceback.print_exc()
#         flash(f"Database error: {e}", 'error')
#         print(f"{e}")
#         return f"{e}"
        
#     finally:
#         if conn:
#             conn.close()

# 
# @bp.route('/')
# def home():
#     conn = None
#     try:
#         username = session.get('username')
#         user_profile = None
#         conn = get_db_connection()
        
#         # Fetch businesses with categories and subscription status
#         cur = conn.cursor(dictionary=True)
#         cur.execute("""
#             SELECT 
#                 b.*,
#                 GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
#                 CASE 
#                     WHEN b.is_subscribed = 1 THEN 'premium'
#                     ELSE 'standard'
#                 END AS tier
#             FROM businesses b
#             LEFT JOIN business_categories bc ON b.id = bc.business_id
#             LEFT JOIN categories c ON bc.category_id = c.id
#             WHERE b.status = 'active'
#             GROUP BY b.id
#             ORDER BY b.is_subscribed DESC, b.created_at DESC
#             LIMIT 1200
#         """)
#         businesses = cur.fetchall()

#         # Fetch user profile if logged in
#         if username:
#             cur.execute("""
#                 SELECT username, profile_image 
#                 FROM users 
#                 WHERE username = %s
#             """, (username,))
#             user_profile = cur.fetchone()

#         return render_template('index.html', 
#                             username=username,
#                             businesses=businesses,
#                             user_profile=user_profile)

#     except Exception as e:
#         app.logger.error(f"Error in home route: {str(e)}")
#         flash("We're having trouble loading businesses. Please try again later.", 'error')
#         return render_template('index.html', 
#                             username=username,
#                             businesses=[],
#                             user_profile=None)
#     finally:
#         if conn:
#             conn.close()

# 
# @bp.route('/')
# def home():
#     conn = None
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)
        
#         # Get current user info if logged in
#         username = session.get('username')
#         user_profile = None
#         if username:
#             cur.execute("SELECT id, username, profile_image FROM users WHERE username = %s", (username,))
#             user_profile = cur.fetchone()
        
#         # Fetch businesses with subscription priority and proper access control
#         cur.execute("""
#             SELECT 
#                 b.id,
#                 b.business_name,
#                 b.description,
#                 b.media_type,
#                 b.media_url,
#                 b.category,
#                 b.is_subscribed,
#                 b.status,
#                 b.created_at,
#                 GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
#                 CASE 
#                     WHEN b.is_subscribed = 1 THEN b.phone_number
#                     ELSE NULL
#                 END AS phone_number,
#                 CASE 
#                     WHEN b.is_subscribed = 1 THEN b.email
#                     ELSE NULL
#                 END AS email,
#                 b.shop_no,
#                 b.block_num,
#                 b.website_url,
#                 b.facebook_link,
#                 b.instagram_link,
#                 b.twitter_link
#             FROM businesses b
#             LEFT JOIN business_categories bc ON b.id = bc.business_id
#             LEFT JOIN categories c ON bc.category_id = c.id
#             WHERE b.status = 'active'
#             GROUP BY b.id
#             ORDER BY b.is_subscribed DESC, b.created_at DESC
#             LIMIT 2000
#         """)
        
#         businesses = cur.fetchall()
        
#         # Process businesses for display
#         for business in businesses:
#             business['status_display'] = 'Premium' if business['is_subscribed'] else 'Basic'
            
#             # Format categories for display
#             if business['categories']:
#                 business['primary_category'] = business['categories'].split(', ')[0]
#                 if len(business['categories'].split(', ')) > 1:
#                     business['additional_categories'] = len(business['categories'].split(', ')) - 1
#                 else:
#                     business['additional_categories'] = 0
#             else:
#                 business['primary_category'] = 'General'
#                 business['additional_categories'] = 0
        
#         return render_template('index.html',
#                             username=username,
#                             user_profile=user_profile,
#                             businesses=businesses)
        
#     except Exception as e:
#         app.logger.error(f"Error in home route: {str(e)}")
#         flash("We're having trouble loading businesses. Please try again later.", 'error')
#         return render_template('index.html',
#                             username=username,
#                             user_profile=None,
#                             businesses=[])
#     finally:
#         if conn:
#             conn.close()


# 
# @bp.route('/')
# def home():
#     conn = None
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)
        
#         # Get all active businesses with subscription status and categories
#         cur.execute("""
#             SELECT 
#                 b.*,
#                 u.username as owner_username,
#                 GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
#                 COUNT(DISTINCT c.id) as category_count,
#                 MIN(c.category_name) as primary_category
#             FROM businesses b
#             LEFT JOIN users u ON b.owner_id = u.id
#             LEFT JOIN business_categories bc ON b.id = bc.business_id
#             LEFT JOIN categories c ON bc.category_id = c.id
#             WHERE b.status = 'active'
#             GROUP BY b.id
#             ORDER BY b.is_subscribed DESC, b.created_at DESC
#             LIMIT 12
#         """)
        
#         businesses = cur.fetchall()
        
#         # Process the businesses data
#         for biz in businesses:
#             biz['additional_categories'] = biz['category_count'] - 1 if biz['category_count'] else 0
            
#         return render_template('index.html', 
#                             businesses=businesses,
#                             username=session.get('username'),
#                             user_profile=session.get('profile_image'))

#     except Exception as e:
#         # app.logger.error(f"Error loading home page: {str(e)}")
#         flash('Error loading businesses. Please try again later.', 'error')
#         return render_template('index.html', 
#                             businesses=[],
#                             username=None,
#                             user_profile=None)
#     finally:
#         if conn:
#             conn.close()


@bp.route('/')
@bp.route('/page/<int:page>')
def home(page=1):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Pagination settings
        per_page = 12
        offset = (page - 1) * per_page
        
        # Get total count for pagination
        cur.execute("SELECT COUNT(*) as total FROM businesses WHERE status != 'deleted'")
        total = cur.fetchone()['total']
        
        # Get businesses with subscription status and categories
        cur.execute("""
            SELECT 
                b.*,
                u.username as owner_username,
                GROUP_CONCAT(DISTINCT c.category_name SEPARATOR ', ') AS categories,
                COUNT(DISTINCT c.id) as category_count,
                MIN(c.category_name) as primary_category
            FROM businesses b
            LEFT JOIN users u ON b.owner_id = u.id
            LEFT JOIN business_categories bc ON b.id = bc.business_id
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE b.status != 'deleted'
            GROUP BY b.id
            ORDER BY b.is_subscribed DESC, 
                     CASE WHEN b.status = 'active' THEN 0 ELSE 1 END,
                     b.created_at DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        
        businesses = cur.fetchall()
        
        # Process the businesses data
        for biz in businesses:
            biz['additional_categories'] = biz['category_count'] - 1 if biz['category_count'] else 0
        
        # print(businesses)
        return render_template('index.html', 
                            businesses=businesses,
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
        app.logger.error(f"Error loading home page: {str(e)}")
        flash('Error loading businesses. Please try again later.', 'error')
        return render_template('index.html', 
                            businesses=[],
                            username=None,
                            user_profile=None,
                            pagination=None)
    finally:
        if conn:
            conn.close()

# 
# @bp.route('/')
# def home():
    # conn = None
    # try:
    #     conn = get_db_connection()
    #     cur = conn.cursor(dictionary=True)
        
    #     # Get businesses with subscription status
    #     cur.execute("""
    #         SELECT b.*, 
    #                GROUP_CONCAT(c.category_name SEPARATOR ', ') AS categories,
    #                COUNT(c.id) AS category_count
    #         FROM businesses b
    #         LEFT JOIN business_categories bc ON b.id = bc.business_id
    #         LEFT JOIN categories c ON bc.category_id = c.id
    #         WHERE b.status != 'deleted'
    #         GROUP BY b.id
    #         ORDER BY b.is_subscribed DESC, b.created_at DESC
    #     """)
        
    #     businesses = cur.fetchall()
        
    #     return render_template('index.html', 
    #                         businesses=businesses,
    #                         username=session.get('username'))

    # except Exception as e:
    #     flash("Error loading businesses", 'error')
    #     return render_template('index.html', 
    #                         businesses=[],
    #                         username=None)
    # finally:
    #     if conn:
    #         conn.close()