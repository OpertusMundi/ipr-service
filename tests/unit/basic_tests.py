import logging
import json
import os
from shutil import rmtree

# Setup/Teardown
def setup_module():
    print(" == Setting up tests for %s"  % (__name__))
    pass

def teardown_module():
    print(" == Tearing down tests for %s"  % (__name__))
    pass

# Tests

def test_validators_1():
    """Unit - Test CRS form validator"""
    from wtforms.validators import ValidationError
    from ipr_service.api.forms.validators import CRS
    class Field:
        def __init__(self, data):
            self.data = data
    message = 'Test message'
    validator = CRS(message)
    try:
        validator(None, Field('wrongcrs'))
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    assert str(exc) == message
    validator(None, Field('EPSG:4326'))

def test_validators_2():
    """Unit - Test Encoding form validator"""
    from wtforms.validators import ValidationError
    from ipr_service.api.forms.validators import Encoding
    class Field:
        def __init__(self, data):
            self.data = data
    message = 'Test message'
    validator = Encoding(message)
    try:
        validator(None, Field('utf-1'))
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    assert str(exc) == message
    validator(None, Field('utf-8'))

def test_validators_3():
    """Unit - Test WKT form validator"""
    from wtforms.validators import ValidationError
    from ipr_service.api.forms.validators import WKT
    class Field:
        def __init__(self, data):
            self.data = data
    message = 'Test message'
    validator = WKT(message)
    try:
        validator(None, Field('wrongwkt'))
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    assert str(exc) == message
    validator(None, Field('POINT(24. 37)'))

def test_validators_4():
    """Unit - Test StringList form validator"""
    from wtforms.validators import ValidationError
    from ipr_service.api.forms.validators import StringList
    class Field:
        def __init__(self, data):
            self.data = data
    message = 'Test message'
    validator = StringList(message)
    try:
        validator(None, Field('field'))
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    assert str(exc) == message
    validator(None, Field(['field1', 'field2']))

def test_validators_5():
    """Unit - Test ListLength form validator"""
    from wtforms.validators import ValidationError
    from ipr_service.api.forms.validators import ListLength
    class Field:
        def __init__(self, data):
            self.data = data
    validator = ListLength(min_entries=4)
    field = Field(['field1', 'field2', 'field3'])
    try:
        validator(None, field)
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    validator = ListLength(max_entries=2)
    try:
        validator(None, field)
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    validator = ListLength(min_entries=2, max_entries=4)
    validator(None, field)

def test_validators_6():
    """Unit - Test FilePath form validator"""
    from wtforms.validators import ValidationError
    from ipr_service.api.forms.validators import FilePath
    class Field:
        def __init__(self, data):
            self.data = data
    validator = FilePath()
    try:
        validator(None, Field('file'))
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    # TODO Test correct path

def test_validators_7():
    """Unit - Test ConditionallyRequired form validator"""
    from wtforms import Form, StringField
    from werkzeug.datastructures import MultiDict
    from wtforms.validators import ValidationError, StopValidation
    from ipr_service.api.forms.validators import ConditionallyRequired
    class TestForm(Form):
        key1 = StringField()
        key2 = StringField()
        key3 = StringField()
    form = TestForm(formdata=MultiDict([('key1', 'value1'), ('key3', 'value3')]))
    validator = ConditionallyRequired('key1', 'value1')
    try:
        validator(form, form._fields.get('key2'))
    except Exception as e:
        exc = e
    assert 'exc' in locals()
    assert isinstance(exc, ValidationError)
    validator(form, form._fields.get('key3'))
    validator = ConditionallyRequired('key1', 'value2')
    try:
        validator(form, form._fields.get('key2'))
    except Exception as e:
        exc = e
    assert isinstance(exc, StopValidation)

def test_scramble_1():
    """Unit - Test array scrambling"""
    from ipr_service.lib.raster_ipr import scramble, unscramble
    import numpy as np
    arr = np.array(np.random.randint(0, 2, size=(10,10), dtype=bool))
    scrambled = scramble(arr, iterations=10)
    assert (arr != unscramble(scrambled, iterations=1)).any()
    assert (arr == unscramble(scrambled, iterations=10)).all()

def test_create_qr_1():
    """Unit - Test create QR"""
    from ipr_service.lib.raster_ipr import createQR
    from pyzbar.pyzbar import decode

    msg = "Hello world!"
    qr = createQR(msg, dim=256)
    width, height = qr.size
    assert width == 256
    assert height == 256
    assert decode(qr)[0].data.decode() == msg
