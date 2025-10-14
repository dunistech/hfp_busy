from os import getenv
from flask import Flask, url_for
from config import config
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
mail = Mail()

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Register context processors
    from utils.helpers import fetch_categories, fetch_plans
    app.context_processor(lambda: {'logo_path': url_for('static', filename='img/dunistech.png')})
    app.context_processor(fetch_categories)
    app.context_processor(fetch_plans)
    
    # Register blueprints
    with app.app_context():
        from routes import categories, index, auth, business, admin, user
        app.register_blueprint(index.bp)
        app.register_blueprint(categories.bp)
        app.register_blueprint(auth.bp)
        app.register_blueprint(business.bp)
        app.register_blueprint(admin.bp)
        app.register_blueprint(user.bp)
        # app.register_blueprint(user.admin)
    
    return app

app = create_app(getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)