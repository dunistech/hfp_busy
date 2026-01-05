from flask import Blueprint, current_app, render_template
import traceback
from flask import Blueprint, current_app as app, render_template, redirect, session, url_for, flash
from services.schema import category_schema
from services.seo import build_seo
from utils.helpers import get_db_connection


# bp = Blueprint('categories', __name__)
bp = Blueprint("categories", __name__, url_prefix="/categories")

@bp.route('/')
def categories():
    return render_template('category/categories.html')

# ======================
# CATEGORY ROUTE
# ======================

# @bp.route('/category/<int:category_id>')
# @bp.route('/category/<int:category_id>/page/<int:page>')
# def businesses_by_category(category_id, page=1):
#     """Show all businesses in a specific category"""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor(dictionary=True)
        
#         # First verify category exists
#         cur.execute("SELECT id, category_name FROM categories WHERE id = %s", (category_id,))
#         category = cur.fetchone()
        
#         if not category:
#             flash('Category not found', 'error')
#             return redirect(url_for('index.home'))
        
#         # Pagination settings
#         per_page = 12
#         offset = (page - 1) * per_page
        
#         # Get total count for pagination
#         cur.execute("""
#             SELECT COUNT(DISTINCT b.id) as total 
#             FROM businesses b
#             JOIN business_categories bc ON b.id = bc.business_id
#             WHERE bc.category_id = %s AND b.status != 'deleted'
#         """, (category_id,))
#         total = cur.fetchone()['total']
        
#         # Get businesses in this category
#         cur.execute("""
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
#             JOIN business_categories bc ON b.id = bc.business_id
#             JOIN categories c ON bc.category_id = c.id
#             LEFT JOIN users u ON b.owner_id = u.id
#             WHERE bc.category_id = %s AND b.status != 'deleted'
#             GROUP BY b.id
#             ORDER BY b.is_subscribed DESC, 
#                      status_order,
#                      b.created_at DESC
#             LIMIT %s OFFSET %s
#         """, (category_id, per_page, offset))
        
#         businesses = cur.fetchall()
        
#         # Process the businesses data
#         for biz in businesses:
#             biz['additional_categories'] = biz['category_count'] - 1 if biz['category_count'] else 0
        
#         # Get all categories for sidebar
#         cur.execute("SELECT id, category_name FROM categories ORDER BY category_name")
#         all_categories = cur.fetchall()
        
#         return render_template('ccategory_businesses.html', 
#                             businesses=businesses,
#                             category=category,
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
#         app.logger.error(f"Category page error: {str(e)}")
#         flash('Error loading category. Please try again later.', 'error')
#         return redirect(url_for('index.home'))
#     finally:
#         if conn:
#             conn.close()


# SLUG VERSIONS
@bp.route("/<string:category_slug>")
@bp.route("/<string:category_slug>/page/<int:page>")
def businesses_by_category(category_slug, page=1):
    """Public businesses by category (slug-based)"""

    per_page = 12
    offset = (page - 1) * per_page

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Fetch category
        cur.execute("""
            SELECT id, category_name, slug
            FROM categories
            WHERE slug = %s
        """, (category_slug,))
        category = cur.fetchone()

        if not category:
            flash("Category not found.", "error")
            return redirect(url_for("index.home"))

        # Total count
        cur.execute("""
            SELECT COUNT(DISTINCT b.id) AS total
            FROM businesses b
            JOIN business_categories bc ON b.id = bc.business_id
            WHERE bc.category_id = %s
              AND b.status != 'deleted'
        """, (category["id"],))
        total = cur.fetchone()["total"]

        # Businesses
        cur.execute("""
            SELECT
                b.id,
                b.business_name,
                b.slug,
                b.media_url,
                b.media_type,
                b.is_subscribed,
                b.created_at,
                u.username AS owner_username,
                GROUP_CONCAT(DISTINCT c.category_name) AS categories
            FROM businesses b
            JOIN business_categories bc ON b.id = bc.business_id
            JOIN categories c ON bc.category_id = c.id
            LEFT JOIN users u ON b.owner_id = u.id
            WHERE bc.category_id = %s
              AND b.status != 'deleted'
            GROUP BY b.id
            ORDER BY b.is_subscribed DESC, b.created_at DESC
            LIMIT %s OFFSET %s
        """, (category["id"], per_page, offset))

        businesses = cur.fetchall()

        # Sidebar categories
        cur.execute("""
            SELECT category_name, slug
            FROM categories
            ORDER BY category_name
        """)
        all_categories = cur.fetchall()
        
        seo = build_seo(
            title=f'{category["category_name"]} Businesses in Ajah',
            description=f'Browse verified {category["category_name"]} businesses in Ajah and Lekki.',
            schema=category_schema(category, businesses),
        )

        return render_template(
            "category/category_businesses.html",
            category=category,
            seo=seo,
            businesses=businesses,
            all_categories=all_categories,
            pagination={
                "page": page,
                "per_page": per_page,
                "total": total,
                "has_next": offset + per_page < total,
                "has_prev": page > 1,
            },
        )

    except Exception:
        traceback.print_exc()
        current_app.logger.exception("Category page error")
        flash("Unable to load category.", "error")
        return redirect(url_for("index.home"))
    finally:
        if conn:
            conn.close()
