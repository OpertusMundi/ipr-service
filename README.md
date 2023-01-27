# IPR-Service

## Description

*Intellectual Property Rights (**IPR**) Service* offers various methods to embed and detect IPR in tabular, vector and rasters assets.

For **tabular** and **vector** formats, IPR can be embedded in the following means:
1. Adding *fictitious entries* in random places inside the attributes.
2. Modulating some *geometries* (vector only), supplementing with points collinear to the geometry vertices.
In both cases, embedding is taking place in a random but deterministic way, so that detection is possible given the original asset and the key used for embedding.

For **raster** format, IPR is embedded:
1. as visible *watermark*, positioned and placed in a fully customized way.
2. as hidden *message*.
In the latter case, detection is possible, revealing the embedded message (key).

## Installation

### Dependencies

* Python 3.8
* Running instance of a database
* [GEOS library](https://github.com/libgeos/geos)
* [PROJ 7](https://proj.org)
* [GDAL 3.1](https://gdal.org/download.html#binaries)
* [Apache Arrow binaries](https://github.com/apache/arrow)
* [PCRE development files](https://www.pcre.org)

### Install package

Install `geovaex`:
```
pip install git+https://github.com/OpertusMundi/geovaex
```
Install service with pip:
```
pip install git+https://github.com/OpertusMundi/ipr-service.git
```
Install separately the Python required packages:
```
pip install -r requirements.txt -r requirements-production.txt
```
### Set environment

The following environment variables should be set:
* `FLASK_ENV` `*`: `development` or `production`.
* `FLASK_APP` `*`: `geometry_service` (if running as a container, this will be always set).
* `SECRET_KEY` `*`: The application secret key. **The value of this key should remain the same, in order that detection does not break.**
* `DATABASE_URI` `*`: `engine://user:pass@host:port/database`
* `WORKING_DIR` : The location for storing the session files (*default*: the system temporary path).
* `OUTPUT_DIR` `*`: The location used to store exported files.
* `INPUT_DIR` `*`: The location of the input files.
* `CORS`: List or string of allowed origins (*default*: `*`).
* `LOGGING_CONFIG_FILE` `*`: The logging configuration file.


### Database

A database should have been created in a DataBase server.

Initialize the database, running:
```
flask init-db
```

## Usage

For details about using the service API, you can browse the full [OpenAPI documentation](https://opertusmundi.github.io/ipr-service/).

## Build and run as a container

Copy `.env.example` to `.env` and configure (e.g `FLASK_ENV` variable).

Copy `compose.yml.example` to `compose.yml` (or `docker-compose.yml`) and adjust to your needs (e.g. specify volume source locations etc.).

Build:

    docker-compose -f compose.yml build

Prepare the following files/directories:

   * `./secrets/secret-key`: file needed (by Flask) for signing/encrypting session data.
   * `./secrets/database-password`: file containing the password for the PostGIS database user.
   * `./logs`: a directory to keep logs.
   * `./temp`: a directory to be used as temporary storage.
   * `./output`: a directory to be used to store exported files.
   * `./input`: a directory where input files are read from.

Start application:

    docker-compose -f compose.yml up


## Run tests

Copy `compose-testing.yml.example` to `compose-testing.yml` and adjust to your needs. This is a just a docker-compose recipe for setting up the testing container.

Build testing container:

    docker-compose -f compose-testing.yml build

Run nosetests (in an ephemeral container):

    docker-compose -f compose-testing.yml run --rm --user "$(id -u):$(id -g)" nosetests -v
