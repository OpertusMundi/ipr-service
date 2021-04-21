import os
from flask import Blueprint, make_response, g, request, jsonify
from werkzeug.utils import secure_filename
from flask_executor import Executor
from ipr_service.database.actions import db_update_queue_status
from ipr_service.loggers import logger
from ..forms.vector import VectorEmbedForm, VectorDetectForm
from ..context import get_session, clean_working_path
from ..async_ import vector_embed_process, vector_detect_process, async_callback
from ..helpers import parse_read_options, copy_to_output


def _before_requests():
    """Executed before each request for this blueprint.

    Get the request form and session details.

    Returns:
        None|Response: In case of validation error, returns a Flask response, None otherwise.
    """
    logger.info('API request [endpoint: "%s"]', request.endpoint)
    form = VectorEmbedForm() if request.endpoint[7:12] == 'embed' else VectorDetectForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)

    session = get_session()

    src_file = os.path.join(os.environ['INPUT_DIR'], form.original.data)

    g.src_file = src_file
    g.form = form
    g.session = session

    g.params = parse_read_options(form)
    if request.endpoint[7:12] != 'embed':
        g.test_file = os.path.join(os.environ['INPUT_DIR'], form.test.data)
        g.test_params = parse_read_options(form, prefix='test_')


def _vector_embed(action, **kwargs):
    """Embed a watermark in vector.

    Arguments:
        action (str): How to embed the watermark; one of 'fictitious', 'geometries'.
        **kwargs: Vector specific read parameters.

    Returns:
        (flask.response): Flask response.
    """
    if g.form.response.data == 'prompt':
        session, export, success, error_msg = vector_embed_process(action, g.session, g.src_file, g.form.uuid.data, **kwargs)
        if not success:
            db_update_queue_status(g.session['ticket'], completed=True, success=False, error_msg=error_msg)
            return make_response({'error': error_msg}, 500)
        path = copy_to_output(export, session['ticket'])
        db_update_queue_status(session['ticket'], completed=True, success=True, result=path)
        return make_response({'type': 'prompt', 'path': path}, 200)

    future = executor.submit(vector_embed_process, action, g.session, g.src_file, g.form.uuid.data, **kwargs)
    future.add_done_callback(async_callback)
    ticket = g.session['ticket']
    return make_response({'type': 'deferred', 'ticket': ticket, 'statusUri': "/jobs/status?ticket={ticket}".format(ticket=ticket)}, 202)


def _vector_detect(action, **kwargs):
    """Check a vector dataset for embedded uuids.

    Arguments:
        action (str): How the watermark was embedded; one of 'fictitious', 'geometries'.
        **kwargs: Vector specific read parameters.

    Returns:
        (flask.response): Flask response.
    """
    if g.form.response.data == 'prompt':
        session, uuid, success, error_msg = vector_detect_process(action, g.session, g.src_file, g.test_file, g.form.uuids.data, **kwargs)
        if not success:
            db_update_queue_status(g.session['ticket'], completed=True, success=False, error_msg=error_msg)
            return make_response({'error': error_msg}, 500)
        db_update_queue_status(session['ticket'], completed=True, success=True, result=uuid)
        return make_response({'type': 'prompt', 'key': uuid}, 200)

    future = executor.submit(vector_detect_process, action, g.session, g.src_file, g.test_file, g.form.uuids.data, **kwargs)
    future.add_done_callback(async_callback)
    ticket = g.session['ticket']
    return make_response({'type': 'deferred', 'ticket': ticket, 'statusUri': "/jobs/status?ticket={ticket}".format(ticket=ticket)}, 202)


# FLASK ROUTES

executor = Executor()
bp = Blueprint('vector', __name__, url_prefix='/vector')
bp.before_request(_before_requests)
bp.teardown_request(clean_working_path)

@bp.route('/embed/fictitious', methods=['POST'])
def embed_fictitious():
    """**Flask POST rule**.

    Embed fictitious entries in the dataset.
    ---
    post:
        summary: Embed fictitious entries.
        description: Embed fictitious entries in the dataset, according to the given unique key.
        tags:
            - Vector
            - Tabular
        parameters:
            - idempotencyKey
        requestBody:
            required: true
            content:
                application/json:
                    schema: vectorEmbedForm
        responses:
            200: promptEmbedResponse
            202: deferredResponse
            400: validationErrorResponse
    """
    return _vector_embed('fictitious', **g.params)

@bp.route('/embed/geometries', methods=['POST'])
def embed_geoms():
    """**Flask POST rule**.

    Embed collinear points in selected geometries of the dataset.
    ---
    post:
        summary: Embed collinear points in selected geometries.
        description: Embed collinear points in selected geometries of the dataset, according to the given unique key.
        tags:
            - Vector
        parameters:
            - idempotencyKey
        requestBody:
            required: true
            content:
                application/json:
                    schema: vectorEmbedForm
        responses:
            200: promptEmbedResponse
            202: deferredResponse
            400: validationErrorResponse
    """
    return _vector_embed('geometries', **g.params)

@bp.route('/detect/fictitious', methods=['POST'])
def detect_fictitious():
    """**Flask POST rule**.

    Detect fictitious entries in the dataset, applying the given keys.
    ---
    post:
        summary: Detect fictitious entries.
        description: Detect fictitious entries in the dataset, applying the given keys.
        tags:
            - Vector
            - Tabular
        parameters:
            - idempotencyKey
        requestBody:
            required: true
            content:
                application/json:
                    schema: vectorDetectForm
        responses:
            200: promptDetectResponse
            202: deferredResponse
            400: validationErrorResponse
    """
    return _vector_detect('fictitious', original_params=g.params, test_params=g.test_params)

@bp.route('/detect/geometries', methods=['POST'])
def detect_geoms():
    """**Flask POST rule**.

    Detect embedded collinear points in selected geometries of the dataset, applying the given keys.
    ---
    post:
        summary: Detect embedded collinear points in selected geometries.
        description: Detect embedded collinear points in selected geometries of the dataset, applying the given keys.
        tags:
            - Vector
        parameters:
            - idempotencyKey
        requestBody:
            required: true
            content:
                application/json:
                    schema: vectorDetectForm
        responses:
            200: promptDetectResponse
            202: deferredResponse
            400: validationErrorResponse
    """
    return _vector_detect('geometries', original_params=g.params, test_params=g.test_params)
