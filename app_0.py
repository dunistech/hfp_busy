from flask import Flask, url_for
from config import Config
from utils import fetch_categories
from routes import categories, index, auth, business, admin, user
from utils import fetch_plans

app = Flask(__name__)
app.config.from_object(Config)

# print('MAIL_USERNAME', app.config['MAIL_USERNAME'])

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

from flask import jsonify
@app.route("/routes")
def site_map():
    links = []
    # for rule in app.url_map.iter_rules():
    for rule in app.url_map._rules:
        """ Filter out rules we can't navigate to in a browser, and rules that require parameters """
        links.append({'url': rule.rule, 'view': rule.endpoint})
    return jsonify(links), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
