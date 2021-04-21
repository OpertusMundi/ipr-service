import logging
import json
import os
from uuid import uuid4
from shutil import copy, rmtree
from ipr_service import create_app
from time import sleep

# Setup/Teardown

app = create_app()

def setup_module():
    print(" == Setting up tests for %s"  % (__name__))
    app.config['TESTING'] = True
    print(" == Using database at %s"  % (app.config['SQLALCHEMY_DATABASE_URI']))
    os.makedirs(os.path.join(os.environ['INPUT_DIR'], 'tmp'))
    pass

def teardown_module():
    print(" == Tearing down tests for %s"  % (__name__))
    try:
        rmtree(os.path.join(os.environ['INPUT_DIR'], 'tmp'))
    except:
        pass

tabular = os.path.join('test_data', 'tabular.csv.gz')
vector = os.path.join('test_data', 'vector.tar.gz')
raster = os.path.join('test_data', 'raster.tif')
watermark = os.path.join('test_data', 'watermark.png')
uuid = str(uuid4())

def test_get_documentation_1():
    """Functional - Get documentation"""
    with app.test_client() as client:
        res = client.get('/', query_string=dict(), headers=dict())
        assert res.status_code == 200
        r = res.get_json()
        assert not (r.get('openapi') is None)

def test_health_1():
    """Functional - Check health"""
    with app.test_client() as client:
        res = client.get('/health', query_string=dict(), headers=dict())
        assert res.status_code == 200
        r = res.get_json()
        assert r.get('status') == 'OK'

def test_tabular_1():
    """Functional - Test tabular; prompt type"""
    with app.test_client() as client:
        data = {
            "original": tabular,
            "response": "prompt",
            "uuid": uuid
        }
        res = client.post('/vector/embed/fictitious', data=data)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get("type") == "prompt"
    resulted_file = os.path.join(os.environ["OUTPUT_DIR"], r.get("path"))
    assert os.path.isfile(resulted_file)
    copy(resulted_file, os.path.join(os.environ["INPUT_DIR"], 'tmp'))
    with app.test_client() as client:
        data = {
            "response": "prompt",
            "original": tabular,
            "test": os.path.join('tmp', os.path.basename(resulted_file)),
            "uuids": [str(uuid4()), str(uuid4()), str(uuid4()), uuid, str(uuid4())]
        }
        res = client.post('/vector/detect/fictitious', data=data)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get("type") == "prompt"
        assert r.get("key") == uuid

def test_tabular_2():
    """Functional - Test tabular; deferred type"""
    with app.test_client() as client:
        data = {
            "original": tabular,
            "response": "deferred",
            "uuid": uuid
        }
        res = client.post('/vector/embed/fictitious', data=data)
        assert res.status_code == 202
        r = res.get_json()
        assert r.get("type") == "deferred"
        ticket = r.get("ticket")
        assert ticket is not None
        assert r.get("statusUri") == "/jobs/status?ticket={ticket}".format(ticket=ticket)
        url = r.get("statusUri")
    with app.test_client() as client:
        res = client.get(url)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get('ticket') == ticket
        for attr in ['idempotencyKey', 'requestType', 'initiated', 'executionTime', 'completed', 'success', 'errorMessage', 'resource', 'key']:
            assert attr in r
        assert r.get('idempotencyKey') is None
        assert r.get('requestType') == 'vector.embed_fictitious'
        assert r.get('errorMessage') is None

def test_vector_1():
    """Functional - Test vector; prompt type"""
    with app.test_client() as client:
        data = {
            "original": vector,
            "response": "prompt",
            "uuid": uuid,
            "encoding": "ISO-8859-7"
        }
        res = client.post('/vector/embed/geometries', data=data)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get("type") == "prompt"
    resulted_file = os.path.join(os.environ["OUTPUT_DIR"], r.get("path"))
    assert os.path.isfile(resulted_file)
    copy(resulted_file, os.path.join(os.environ["INPUT_DIR"], 'tmp'))
    sleep(0.5)
    with app.test_client() as client:
        data = {
            "response": "prompt",
            "original": vector,
            "test": os.path.join('tmp', os.path.basename(resulted_file)),
            "uuids": [str(uuid4()), str(uuid4()), str(uuid4()), uuid, str(uuid4())],
            "encoding": "ISO-8859-7"
        }
        res = client.post('/vector/detect/geometries', data=data)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get("type") == "prompt"
        assert r.get("key") == uuid

def test_vector_2():
    """Functional - Test vector; deferred type"""
    with app.test_client() as client:
        data = {
            "original": vector,
            "response": "deferred",
            "uuid": uuid,
            "encoding": "ISO-8859-7"
        }
        res = client.post('/vector/embed/geometries', data=data)
        assert res.status_code == 202
        r = res.get_json()
        assert r.get("type") == "deferred"
        ticket = r.get("ticket")
        assert ticket is not None
        assert r.get("statusUri") == "/jobs/status?ticket={ticket}".format(ticket=ticket)
        url = r.get("statusUri")
    with app.test_client() as client:
        res = client.get(url)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get('ticket') == ticket
        for attr in ['idempotencyKey', 'requestType', 'initiated', 'executionTime', 'completed', 'success', 'errorMessage', 'resource', 'key']:
            assert attr in r
        assert r.get('idempotencyKey') is None
        assert r.get('requestType') == 'vector.embed_geoms'
        assert r.get('errorMessage') is None

def test_raster_1():
    """Functional - Test watermark; prompt type"""
    with app.test_client() as client:
        data = {
            "response": "prompt",
            "raster": raster,
            "watermark": watermark,
            "fit": "tile",
            "distance_x": 200,
            "distance_y": 300
        }
        res = client.post('/raster/embed/watermark', data=data)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get("type") == "prompt"
        assert r.get("path") is not None
        assert os.path.isfile(os.path.join(os.environ['OUTPUT_DIR'], r.get("path")))

def test_raster_2():
    """Functional - Test watermark; deferred type"""
    with app.test_client() as client:
        data = {
            "response": "deferred",
            "raster": raster,
            "watermark": watermark
        }
        res = client.post('/raster/embed/watermark', data=data)
        assert res.status_code == 202
        r = res.get_json()
        assert r.get("type") == "deferred"
        ticket = r.get("ticket")
        assert ticket is not None
        assert r.get("statusUri") == "/jobs/status?ticket={ticket}".format(ticket=ticket)
        url = r.get("statusUri")
    with app.test_client() as client:
        res = client.get(url)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get('ticket') == ticket
        for attr in ['idempotencyKey', 'requestType', 'initiated', 'executionTime', 'completed', 'success', 'errorMessage', 'resource', 'key']:
            assert attr in r
        assert r.get('idempotencyKey') is None
        assert r.get('requestType') == 'raster.embed_watermark'
        assert r.get('errorMessage') is None

def test_raster_3():
    """Functional - Test raster; prompt type"""
    with app.test_client() as client:
        data = {
            "response": "prompt",
            "raster": raster,
            "message": uuid
        }
        res = client.post('/raster/embed/message', data=data)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get("type") == "prompt"
        assert r.get("path") is not None
    resulted_file = os.path.join(os.environ["OUTPUT_DIR"], r.get("path"))
    assert os.path.isfile(resulted_file)
    copy(resulted_file, os.path.join(os.environ["INPUT_DIR"], 'tmp'))
    sleep(0.5)
    with app.test_client() as client:
        data = {
            "response": "prompt",
            "raster": raster,
            "watermarked": os.path.join('tmp', os.path.basename(resulted_file))
        }
        res = client.post('/raster/detect/message', data=data)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get("type") == "prompt"
        assert r.get("key") == uuid

def test_raster_4():
    """Functional - Test raster; deferred type"""
    with app.test_client() as client:
        data = {
            "response": "deferred",
            "raster": raster,
            "message": uuid
        }
        res = client.post('/raster/embed/message', data=data)
        assert res.status_code == 202
        r = res.get_json()
        assert r.get("type") == "deferred"
        ticket = r.get("ticket")
        assert ticket is not None
        assert r.get("statusUri") == "/jobs/status?ticket={ticket}".format(ticket=ticket)
        url = r.get("statusUri")
    with app.test_client() as client:
        res = client.get(url)
        assert res.status_code == 200
        r = res.get_json()
        assert r.get('ticket') == ticket
        for attr in ['idempotencyKey', 'requestType', 'initiated', 'executionTime', 'completed', 'success', 'errorMessage', 'resource', 'key']:
            assert attr in r
        assert r.get('idempotencyKey') is None
        assert r.get('requestType') == 'raster.embed_message'
        assert r.get('errorMessage') is None

def test_idempotency_key_1():
    """Functional - Test idempotency key"""
    key = str(uuid4())
    with app.test_client() as client:
        data = {
            "original": tabular,
            "uuid": uuid
        }
        res = client.post('/vector/embed/fictitious', data=data, headers={'X-Idempotency-Key': key})
        assert res.status_code == 202
    with app.test_client() as client:
        res = client.get('jobs/status', query_string={'idempotency-key': key})
        assert res.status_code == 200
        r = res.get_json()
        assert r.get('idempotencyKey') == key
