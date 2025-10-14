import traceback
from flask import Blueprint, jsonify, render_template, session, flash
from utils.helpers import get_db_connection
from flask import current_app as app

bp = Blueprint('index', __name__)

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
        return render_template(
            'index.html', 
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


# Add custom routes
@bp.route("/routes")
def site_map():
    """Endpoint to list all available routes"""
    links = []
    for rule in app.url_map.iter_rules():
        if 'GET' in rule.methods and not rule.rule.startswith('/static'):
            links.append({
                'url': rule.rule,
                'endpoint': rule.endpoint,
                'methods': list(rule.methods)
            })
    return jsonify(links)
