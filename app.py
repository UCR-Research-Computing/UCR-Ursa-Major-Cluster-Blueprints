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

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)

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


if __name__ == '__main__':
    app.run()
