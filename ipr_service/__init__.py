"""
### A service to embed and detect Intellectual Property Rights (IPRs) to (geospatial) datasets.

*IPR service* offers various methods to embed IPR to tabular, vector and raster assets.
"""
from .lib.vector_ipr import Ipr
from .lib.raster_ipr import Watermark
import os, sys
from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
import tempfile
from ipr_service.database import db
from ._version import __version__
from .api.doc_components import add_components
from .loggers import logger

# OpenAPI documentation
logger.debug('Initializing OpenAPI specification.')
spec = APISpec(
    title="IPR API",
    version=__version__,
    info=dict(
        description=__doc__,
        contact={"email": "pmitropoulos@getmap.gr"}
    ),
    externalDocs={"description": "GitHub", "url": "https://github.com/OpertusMundi/ipr-service"},
    openapi_version="3.0.2",
    plugins=[FlaskPlugin()],
)
logger.debug('Adding OpenAPI specification components.')
add_components(spec)

# Check environment variables
if os.getenv('DATABASE_URI') is None:
    logger.fatal('Environment variable not set [variable="DATABASE_URI"]')
    sys.exit(1)
if os.getenv('SECRET_KEY') is None:
    logger.fatal('Environment variable not set [variable="SECRET_KEY"]')
    sys.exit(1)
if os.getenv('OUTPUT_DIR') is None:
    logger.fatal('Environment variable not set [variable="OUTPUT_DIR"]')
    sys.exit(1)
if os.getenv('INPUT_DIR') is None:
    logger.fatal('Environment variable not set [variable="INPUT_DIR"]')
    sys.exit(1)
if os.getenv('WORKING_DIR') is None:
    working_dir = os.path.join(tempfile.gettempdir(), os.getenv('FLASK_APP'))
    os.environ['WORKING_DIR'] = working_dir
    logger.info('Set environment variable [WORKING_DIR="%s"]', working_dir)
if os.getenv('CORS') is None:
    os.environ['CORS'] = '*'
    logger.info('Set environment variable [CORS="*"]')

# Create directories
for path in [os.environ['WORKING_DIR'], os.environ['OUTPUT_DIR']]:
    try:
        os.makedirs(path)
    except OSError:
        pass
    else:
        logger.info("Created directory: %s.", path)


def create_app():
    """Create flask app."""
    from flask import Flask, make_response, g, request
    from flask_cors import CORS
    from ipr_service.database.model import Queue
    from ipr_service.api import vector, raster, misc, jobs

    logger.debug('Initializing app.')
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ['SECRET_KEY'],
        SQLALCHEMY_DATABASE_URI=os.environ['DATABASE_URI'],
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
        EXECUTOR_TYPE="thread",
        EXECUTOR_MAX_WORKERS="1"
    )
    db.init_app(app)

    #Enable CORS
    if os.getenv('CORS') is not None:
        if os.getenv('CORS')[0:1] == '[':
            origins = json.loads(os.getenv('CORS'))
        else:
            origins = os.getenv('CORS')
        cors = CORS(app, origins=origins)

    # Register Blueprints
    vector.executor.init_app(app)
    raster.executor.init_app(app)
    logger.debug('Registering blueprints.')
    # Add blueprints
    app.register_blueprint(vector.bp)
    app.register_blueprint(raster.bp)
    app.register_blueprint(misc.bp)
    app.register_blueprint(jobs.bp)

    # Register documentation
    logger.debug('Registering documentation.')
    with app.test_request_context():
        for view in app.view_functions.values():
            spec.path(view=view)

    @app.route("/", methods=['GET'])
    def index():
        """The index route, returns the JSON OpenAPI specification."""
        logger.info('Generating the OpenAPI document...')
        return make_response(spec.to_dict(), 200)

    # Register cli commands
    with app.app_context():
        import ipr_service.cli

    logger.debug('Created app.')
    return app
