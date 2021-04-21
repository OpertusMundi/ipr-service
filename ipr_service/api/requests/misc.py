import os
from flask import Blueprint, make_response, request
import tempfile
import sqlalchemy
from ipr_service.database.model import Queue
from ipr_service.loggers import logger
from ..helpers import send_file

def _checkDirectoryWritable(d):
    fd, fname = tempfile.mkstemp(None, None, d)
    os.unlink(fname)

def _checkConnectToDB():
    url = os.environ['DATABASE_URI']
    engine = sqlalchemy.create_engine(url)
    conn = engine.connect()
    conn.execute('SELECT 1')
    logger.debug("_checkConnectToDB(): Connected to %s", engine.url)

bp = Blueprint('misc', __name__)

@bp.route("/download/<ticket>/<filename>", methods=['GET'])
def download(ticket, filename):
    """**Flask GET rule

    Download a resource.
    ---
    get:
        summary: Download a resource.
        tags:
            - Misc
        parameters:
            -
                name: ticket
                in: path
                schema:
                    type: string
                description: The ticket of the request resulted in the resource.
            -
                name: filename
                in: path
                schema:
                    type: string
                description: The requested file name.
        responses:
            200:
                description: The requested file.
                content:
                    application/x-tar:
                        schema:
                            type: string
                            format: binary
            404:
                description: Ticket not found.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    description: Error message
                                    example: Ticket not found.
            410:
                description: Resource not available.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    description: Error message
                                    example: Resource not available.
    """
    logger.info('API request [endpoint: "%s"]', request.endpoint)
    queue = Queue().get(ticket=ticket)
    if queue is None:
        return make_response({"status": "Ticket not found."}, 404)
    path = os.path.join(os.environ['OUTPUT_DIR'], queue['result'])
    if filename != os.path.basename(queue['result']) or not os.path.isfile(path):
        return make_response({"status": "Resource not available."}, 410)
    return send_file(path)



@bp.route("/health", methods=['GET'])
def health():
    """**Flask GET rule**

    Perform basic health checks.
    ---
    get:
        summary: Get health status.
        tags:
            - Misc
        responses:
            200:
                description: An object with status information.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    enum:
                                        - OK
                                        - FAILED
                                    description: A status of 'OK' or 'FAILED'.
                                details:
                                    type: object
                                    description: The reason of failure for each component, or 'OK' if not failed.
                                    properties:
                                        gdal:
                                            type: string
                                            example: OK
                                        filesystem:
                                            type: string
                                            example: OK
                                        db:
                                            type: string
                                            example: OK
    """
    from osgeo import ogr

    logger.info('Performing health checks...')
    msg = {'gdal': 'OK', 'filesystem': 'OK', 'db': 'OK'}
    status = True

    for drv in ['CSV', 'GeoJSON', 'ESRI Shapefile']:
        if ogr.GetDriverByName(drv) is None:
            msg['gdal'] = 'GDAL is not properly installed.'
            status = False
            break

    for path in [os.environ['WORKING_DIR'], os.environ['OUTPUT_DIR']]:
        try:
            _checkDirectoryWritable(path)
        except Exception as e:
            msg['filesystem'] = str(e)
            status = False
            break

    try:
        _checkConnectToDB()
    except Exception as e:
        msg['db'] = str(e)
        status = False

    return make_response({'status': 'OK' if status else 'FAILED', 'details': msg}, 200)
