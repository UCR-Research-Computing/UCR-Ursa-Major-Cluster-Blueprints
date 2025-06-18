from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from flask_marshmallow import Marshmallow # Import Marshmallow

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)
ma = Marshmallow(app) # Initialize Marshmallow

# Import models to ensure they are registered with SQLAlchemy
# This needs to come after db initialization.
from models import models

# Register Blueprints
from routes.researchers import researcher_bp
app.register_blueprint(researcher_bp, url_prefix='/api/researchers')

from routes.labs import lab_bp
app.register_blueprint(lab_bp, url_prefix='/api/labs')

from routes.projects import project_bp
app.register_blueprint(project_bp, url_prefix='/api/projects')

from routes.compute_resources import compute_resource_bp
app.register_blueprint(compute_resource_bp, url_prefix='/api/compute-resources')

from routes.grants import grant_bp
app.register_blueprint(grant_bp, url_prefix='/api/grants')

from routes.data import data_bp
app.register_blueprint(data_bp, url_prefix='/api/data')

from routes.ai import ai_bp
app.register_blueprint(ai_bp, url_prefix='/api/ai')

# Swagger UI Configuration
from flask_swagger_ui import get_swaggerui_blueprint
SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI (without trailing slash)
API_URL = '/static/swagger.json'  # URL for your Swagger JSON spec (relative to static folder)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "UCR Research Computing Dashboard API",
        'layout': "BaseLayout", # Other options: "StandaloneLayout"
        'docExpansion': "list", # Options: "none", "list", "full"
        'persistAuthorization': True,
    }
)
app.register_blueprint(swaggerui_blueprint) # Register with app, url_prefix is SWAGGER_URL by default

# Error Handler for Marshmallow ValidationErrors
from marshmallow.exceptions import ValidationError
@app.errorhandler(ValidationError)
def handle_marshmallow_validation(err):
    return jsonify(err.messages), 400

if __name__ == '__main__':
    app.run()
