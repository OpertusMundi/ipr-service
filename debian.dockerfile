# vim: set syntax=dockerfile:

FROM debian:stable-20230109-slim 

RUN apt-get update && \
  apt-get install -y \
    git \
    python3 python3-pip python3-numpy python3-pyproj python3-gdal python3-psycopg2 python3-pillow python3-pywt \
    python3-qrcode python3-requests python3-pandas python3-psutil \
    python3-flask python3-flask-cors python3-flask-sqlalchemy python3-flaskext.wtf \
    python3-astropy python3-tabulate python3-future python3-toolz python3-nest-asyncio python3-partd python3-dask \
    libpcre3 libpcre3-dev libzbar0

RUN pip3 install --system --no-cache-dir \
  apispec==4.0.0 apispec-webframeworks==0.5.2 \
  pyzbar==0.1.8 \
  flask-executor==0.9.3 \
  pyarrow==3.0.0 'vaex-core>=2.0.3,<2.0.4' 'vaex-arrow>=0.5.1,<0.5.2' 'pygeos>=0.9.0,<1.0.0' \
  gunicorn==20.0.4

# NOTE: --no-deps to prevent re-installing {gdal,pyproj} package
RUN pip3 install --no-deps git+https://github.com/OpertusMundi/geovaex.git@v0.2.1

RUN mkdir /usr/local/ipr_service/
COPY setup.py /usr/local/ipr_service/
COPY ipr_service /usr/local/ipr_service/ipr_service
RUN (cd /usr/local/ipr_service && python3 setup.py install)

COPY wsgi.py docker-command.sh /usr/local/bin/
RUN chmod a+x /usr/local/bin/wsgi.py /usr/local/bin/docker-command.sh

RUN useradd -u 1000 -m -d /var/local/ipr_service flask

WORKDIR /var/local/ipr_service
RUN mkdir ./logs
COPY --chown=flask logging.conf .

ARG VERSION

ENV VERSION="${VERSION}" \
    FLASK_ENV="production" \
    FLASK_DEBUG="false" \
    CORS="*" \
    OUTPUT_DIR="/var/local/ipr_service/output" \
    INPUT_DIR="/var/local/ipr_service/input" \
    WORKING_DIR="/var/local/ipr_service/temp" \
    SECRET_KEY_FILE="/secrets/secret_key" \
    DB_PASS_FILE="/secrets/database-password" \
    TLS_CERTIFICATE="" \
    TLS_KEY=""

USER flask
CMD ["/usr/local/bin/docker-command.sh"]

EXPOSE 5000
EXPOSE 5443
