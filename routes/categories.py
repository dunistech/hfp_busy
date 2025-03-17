from flask import Blueprint, render_template, redirect, url_for, flash
from utils import get_db_connection

bp = Blueprint('categories', __name__)

@bp.route('/categories')
def categories():
    return render_template('categories.html')

@bp.route('/category/<int:category_id>')
def category_view(category_id):
    conn = get_db_connection()
    businesses = []
    category_name = None

    try:
        cur = conn.cursor()

        # Fetch the category name
        cur.execute("SELECT category_name FROM categories WHERE id = %s", (category_id,))
        category_row = cur.fetchone()
        
        if category_row:
            category_name = category_row[0]
        else:
            flash("Category not found.", 'error')
            return redirect(url_for('index.home'))  # Redirect or handle as needed

        # Fetch businesses in this category
        cur.execute(
            """
                SELECT b.*
                FROM businesses b
                INNER JOIN business_categories bc ON b.id = bc.business_id
                WHERE bc.category_id = %s AND b.is_subscribed = 0 OR b.is_subscribed = 1
            """, 
            (category_id,))
        
        businesses = cur.fetchall()

        cur.close()
    except Exception as e:
        flash(f"Database error: {e}", 'error')
        businesses = []  # Ensure businesses is an empty list on error.
    finally:
        conn.close()

    return render_template('category_view.html', category_name=category_name, businesses=businesses)
