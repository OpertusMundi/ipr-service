import os
from flask import Blueprint, make_response, g, request, jsonify
from werkzeug.utils import secure_filename
from flask_executor import Executor
from ipr_service.database.actions import db_update_queue_status
from ipr_service.loggers import logger
from ..forms.raster import RasterVisibleEmbedForm, RasterEmbedForm, RasterDetectForm
from ..context import get_session, clean_working_path
from ..async_ import raster_embed_process, raster_detect_process, async_callback
from ..helpers import copy_to_output

executor = Executor()
bp = Blueprint('raster', __name__, url_prefix='/raster')
bp.teardown_request(clean_working_path)


@bp.route('/embed/watermark', methods=['POST'])
def embed_watermark():
    """**Flask POST rule**.

    Embed a visible watermark.
    ---
    post:
        summary: Embed a visible watermark.
        description: Embed a visible watermark, placed according to the given parameters.
        tags:
            - Raster
        parameters:
            - idempotencyKey
        requestBody:
            required: true
            content:
                application/json:
                    schema: rasterEmbedWatermarkForm
        responses:
            200: promptEmbedResponse
            202: deferredResponse
            400: validationErrorResponse
    """
    logger.info('API request [endpoint: "%s"]', request.endpoint)
    form = RasterVisibleEmbedForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    g.session = get_session()
    raster = os.path.join(os.environ['INPUT_DIR'], form.raster.data)
    watermark = os.path.join(os.environ['INPUT_DIR'], form.watermark.data)
    params = {'transparency': form.transparency.data, 'fit': form.fit.data, 'position': form.position.data}
    if params['fit'] == 'tile':
        params['distance'] = (form.distance_x.data, form.distance_y.data)

    if form.response.data == 'prompt':
        session, export, success, error_msg = raster_embed_process('watermark', g.session, raster, watermark, **params)
        if not success:
            db_update_queue_status(g.session['ticket'], completed=True, success=False, error_msg=error_msg)
            return make_response({'error': error_msg}, 500)
        path = copy_to_output(export, session['ticket'])
        db_update_queue_status(session['ticket'], completed=True, success=True, result=path)
        return make_response({'type': 'prompt', 'path': path}, 200)

    future = executor.submit(raster_embed_process, 'watermark', g.session, raster, watermark, **params)
    future.add_done_callback(async_callback)
    return make_response({'type': 'deferred', 'ticket': g.session['ticket'], 'statusUri': "/jobs/status?ticket={ticket}".format(ticket=g.session['ticket'])}, 202)


@bp.route('/embed/message', methods=['POST'])
def embed_message():
    """**Flask POST rule**.

    Embed an invisible message.
    ---
    post:
        summary: Embed an invisible message.
        description: Embed an invisible message to raster.
        tags:
            - Raster
        parameters:
            - idempotencyKey
        requestBody:
            required: true
            content:
                application/json:
                    schema: rasterEmbedMessageForm
        responses:
            200: promptEmbedResponse
            202: deferredResponse
            400: validationErrorResponse
    """
    logger.info('API request [endpoint: "%s"]', request.endpoint)
    form = RasterEmbedForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    g.session = get_session()
    raster = os.path.join(os.environ['INPUT_DIR'], form.raster.data)

    if form.response.data == 'prompt':
        session, export, success, error_msg = raster_embed_process('message', g.session, raster, form.message.data)
        if not success:
            db_update_queue_status(g.session['ticket'], completed=True, success=False, error_msg=error_msg)
            return make_response({'error': error_msg}, 500)
        path = copy_to_output(export, session['ticket'])
        db_update_queue_status(session['ticket'], completed=True, success=True, result=path)
        return make_response({'type': 'prompt', 'path': path}, 200)

    future = executor.submit(raster_embed_process, 'message', g.session, raster, form.message.data)
    future.add_done_callback(async_callback)
    return make_response({'type': 'deferred', 'ticket': g.session['ticket'], 'statusUri': "/jobs/status?ticket={ticket}".format(ticket=g.session['ticket'])}, 202)


@bp.route('/detect/message', methods=['POST'])
def detect_message():
    """**Flask POST rule**.

    Detect an invisible message.
    ---
    post:
        summary: Detect an invisible message.
        description: Detect an invisible message, previously embedded to the raster.
        tags:
            - Raster
        parameters:
            - idempotencyKey
        requestBody:
            required: true
            content:
                application/json:
                    schema: rasterDetectForm
        responses:
            200: promptDetectResponse
            202: deferredResponse
            400: validationErrorResponse
    """
    logger.info('API request [endpoint: "%s"]', request.endpoint)
    form = RasterDetectForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    g.session = get_session()
    raster = os.path.join(os.environ['INPUT_DIR'], form.raster.data)
    watermarked = os.path.join(os.environ['INPUT_DIR'], form.watermarked.data)

    if form.response.data == 'prompt':
        session, message, success, error_msg = raster_detect_process(g.session, raster, watermarked)
        if not success:
            db_update_queue_status(g.session['ticket'], completed=True, success=False, error_msg=error_msg)
            return make_response({'error': error_msg}, 500)
        db_update_queue_status(session['ticket'], completed=True, success=True, result=message)
        return make_response({'type': 'prompt', 'key': message}, 200)

    future = executor.submit(raster_detect_process, g.session, raster, watermarked)
    future.add_done_callback(async_callback)
    return make_response({'type': 'deferred', 'ticket': g.session['ticket'], 'statusUri': "/jobs/status?ticket={ticket}".format(ticket=g.session['ticket'])}, 202)
