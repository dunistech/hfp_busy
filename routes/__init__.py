from flask import Blueprint

bp = Blueprint('main', __name__)

from . import auth, business, admin, user  # Import routes to register them
