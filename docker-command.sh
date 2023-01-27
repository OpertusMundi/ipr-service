#!/bin/sh
#set -x
set -e -u


# Check environment

if [ ! -f "${SECRET_KEY_FILE}" ]; then
    echo "SECRET_KEY_FILE=${SECRET_KEY_FILE}: file does not exist!" 1>&2 && exit 1
fi

if [ ! -d "${OUTPUT_DIR}" ]; then
    echo "OUTPUT_DIR=${OUTPUT_DIR}: directory does not exist!" 1>&2 && exit 1
fi

if [ ! -f "${DB_PASS_FILE}" ]; then
    echo "DB_PASS_FILE=${DB_PASS_FILE}: file does not exist!" 1>&2 && exit 1
fi
DB_PASS="$(cat ${DB_PASS_FILE})"

export LOGGING_FILE_CONFIG="./logging.conf"
if [ ! -f "${LOGGING_FILE_CONFIG}" ]; then
    echo "LOGGING_FILE_CONFIG (configuration for Python logging) does not exist!" 1>&2 && exit 1
fi

if [ -n "${LOGGING_ROOT_LEVEL}" ]; then
    sed -i -e "/^\[logger_root\]/,/^\[.*/ { s/^level=.*/level=${LOGGING_ROOT_LEVEL}/ }" ${LOGGING_FILE_CONFIG}
fi

export DATABASE_URI="${DB_ENGINE}://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
export FLASK_APP="ipr_service"
export SECRET_KEY="$(cat ${SECRET_KEY_FILE})"

# Initialize/Upgrade database

flask init-db

# Configure and start WSGI server

if [ "${FLASK_ENV}" = "development" ]; then
    # Run a development server
    exec /usr/local/bin/wsgi.py
fi

num_workers="4"
server_port="5000"
timeout="1200"
num_threads="1"
gunicorn_ssl_options=
if [ -n "${TLS_CERTIFICATE}" ] && [ -n "${TLS_KEY}" ]; then
    gunicorn_ssl_options="--keyfile ${TLS_KEY} --certfile ${TLS_CERTIFICATE}"
    server_port="5443"
fi

exec gunicorn --log-config ${LOGGING_FILE_CONFIG} --access-logfile - \
  --workers ${num_workers} \
  -t ${timeout} \
  --threads ${num_threads} \
  --bind "0.0.0.0:${server_port}" ${gunicorn_ssl_options} \
  "ipr_service:create_app()"
