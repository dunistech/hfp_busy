from flask import Flask, url_for
from config import Config
from utils import fetch_categories
from routes import categories, index, auth, business, admin, user
from utils import fetch_plans

app = Flask(__name__)
app.config.from_object(Config)

app.context_processor(lambda: {'logo_path': url_for('static', filename='img/dunistech.png')})
# categories = fetch_categories()
app.context_processor(fetch_categories)
app.context_processor(fetch_plans)

# Register Blueprints
app.register_blueprint(index.bp)
app.register_blueprint(categories.bp)
app.register_blueprint(auth.bp)
app.register_blueprint(business.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(user.bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
