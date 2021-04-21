import os
from flask import Blueprint, make_response, request, jsonify
from ipr_service.database.model import Queue
from ipr_service.database.actions import db_get_active_jobs
from ipr_service.loggers import logger

# FLASK ROUTES

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/', methods=['GET'])
def info():
    """**Flask GET rule**.

    Get the running processes.
    ---
    get:
        summary: Get the running processes.
        description: Get the running processes among all sessions.
        tags:
            - Jobs
        responses:
            200:
                description: The list of the running processes.
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                description: Details of the process.
                                type: object
                                properties:
                                    ticket:
                                        type: string
                                        description: The ticket assigne to the process.
                                        example: caff960ab6f1627c11b0de3c6406a140
                                    idempotencyKey:
                                        type: string
                                        description: The X-Idempotency-Key sent in the headers of the request (null if the request was not associated with an idempotency key).
                                        example: e5d16e99-dee1-4d16-acce-ca0f20a83a0a
                                    requestType:
                                        type: string
                                        description: Type of the request.
                                    initiated:
                                        type: string
                                        format: date-time
                                        description: The timestamp of the request.
    """
    logger.info('API request [endpoint: "%s"]', request.endpoint)
    running = db_get_active_jobs()
    return make_response(jsonify(running), 200)


@bp.route('/status', methods=['GET'])
def status():
    """**Flask GET rule**.

    Returns the status of a process.
    ---
    get:
        summary: Returns the status of a process.
        description: Returns the status of the process identified by a ticket or idempotency key.
        tags:
            - Jobs
        parameters:
            -
                name: ticket
                in: query
                schema:
                    type: string
                required: false
                description: The request ticket (required if *idempotency-key* is not given).
            -
                name: idempotency-key
                in: query
                schema:
                    type: string
                required: false
                description: The idempotency-key sent with the request (required if *ticket* is not given).
        responses:
            200:
                description: The process was found and the response contains its status details.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                ticket:
                                    type: string
                                    description: Request ticket.
                                    example: caff960ab6f1627c11b0de3c6406a140
                                idempotencyKey:
                                    type: string
                                    description: The X-Idempotency-Key sent in the headers of the request (null if the request was not associated with an idempotency key).
                                    example: e5d16e99-dee1-4d16-acce-ca0f20a83a0a
                                requestType:
                                    type: string
                                    enum:
                                        - ingest
                                        - export
                                    description: Type of the request.
                                initiated:
                                    type: string
                                    format: date-time
                                    description: The timestamp of the request.
                                executionTime:
                                    type: number
                                    format: float
                                    description: The execution time in seconds.
                                    example: 8.29
                                completed:
                                    type: boolean
                                    description: Whether the process has been completed.
                                success:
                                    type: boolean
                                    description: Whether the process has been completed succesfully.
                                errorMessage:
                                    type: string
                                    description: The error message in case of failure.
                                resource:
                                    type: object
                                    description: The resource, in case the process result is a resource.
                                    properties:
                                        link:
                                            type: string
                                            description: The link to download a resource resulted from an export request; null for any other type of request.
                                            example: /download/my_dataset.tar.gz
                                        outputPath:
                                            type: string
                                            description: The relative path of the resource resulted from an export request in the output directory; null for any other type of request or if copy to the output directory was not requested.
                                            example: 2102/{token}/caff960ab6f1627c11b0de3c6406a140/my_dataset.tar.gz
                                key:
                                    type: string
                                    description: The result of the process.
                                    example: 09061d7e-3b1a-4a14-bfa5-b65b9ce0412d
            400:
                description: Both query parameters are missing.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    description: Error message
                                    example: One of 'ticket', 'idempotency-key' is required in query parameters.
            404:
                description: The ticket or idempotency-key not found.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    description: Error message
                                    example: Process not found.
    """
    ticket = request.args.get('ticket')
    key = request.args.get('idempotency-key')
    logger.info('API request [endpoint: "%s", ticket: "%s", idempotency-key: "%s"]', request.endpoint, ticket, key)
    if ticket is not None:
        queue = Queue().get(ticket=ticket)
    elif key is not None:
        queue = Queue().get(idempotency_key=key)
    else:
        return make_response({"status": "One of 'ticket', 'idempotency-key' is required in query parameters."}, 400)
    if queue is None:
        return make_response({"status": "Process not found."}, 404)
    resource = {'link': None, 'outputPath': None}
    key = None
    if queue['result'] is not None:
        if os.path.isfile(os.path.join(os.environ['OUTPUT_DIR'], queue['result'])):
            resource = {'link': '/download/{ticket}/{filename}'.format(ticket=queue['ticket'], filename=os.path.basename(queue['result'])), 'outputPath': queue['result']}
        else:
            key = queue['result']
    info = {
        "ticket": queue['ticket'],
        "idempotencyKey": queue['idempotency_key'],
        "requestType": queue['request'],
        "initiated": queue['initiated'],
        "executionTime": queue['execution_time'],
        "completed": queue['completed'],
        "success": queue['success'],
        "errorMessage": queue['error_msg'],
        "resource": resource,
        "key": key
    }
    return make_response(info, 200)
