from flask import Blueprint, render_template

bp = Blueprint('categories', __name__)

@bp.route('/categories')
def categories():
    return render_template('categories.html')

