from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = 'krishibodh-enhanced-secret-key'

    # Register Blueprints / Routes
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
