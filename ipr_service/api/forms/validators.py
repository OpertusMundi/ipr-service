"""A collection of custom WTForms Validators."""

from wtforms.validators import ValidationError, StopValidation

class CRS(object):
    """Validates CRS fields."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid CRS.'
        self.message = message

    def __call__(self, form, field):
        import pyproj
        from pyproj.exceptions import CRSError
        try:
            pyproj.crs.CRS.from_user_input(field.data)
        except CRSError:
            raise ValidationError(self.message)


class Encoding(object):
    """Validates an encoding field."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid encoding.'
        self.message = message

    def __call__(self, form, field):
        try:
            ''.encode(encoding=field.data, errors='replace')
        except LookupError:
            raise ValidationError(self.message)


class WKT(object):
    """Validates a Well-Known-Text geometry field."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid Well-Known-Text geometry.'
        self.message = message

    def __call__(self, form, field):
        from pygeos import from_wkt, GEOSException
        try:
            from_wkt(field.data)
        except GEOSException:
            raise ValidationError(self.message)

class StringList(object):
    """Validates a field as a list of strings."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a list of strings.'
        self.message = message

    def __call__(self, form, field):
        import numpy as np
        if not isinstance(field.data, list) or str(np.array(field.data).dtype)[1:2] != 'U':
            raise ValidationError(self.message)

class ListLength(object):
    """Validates the length of a list object."""
    def __init__(self, message=None, min_entries=None, max_entries=None):
        self.min_entries = min_entries
        self.max_entries = max_entries
        if not message:
            if min_entries is not None and max_entries is not None:
                message = 'Field length should from {min} to {max}'.format(min=min_entries, max=max_entries)
            elif min_entries is None:
                message = 'Field length should be at most {max}'.format(max=max_entries)
            elif max_entries is None:
                message = 'Field length should be at least {min}'.format(min=min_entries)
        self.message = message

    def __call__(self, form, field):
        import numpy as np
        arr = np.array(field.data)
        length = len(arr[np.where(arr!='')])
        min_entries = self.min_entries
        max_entries = self.max_entries
        if min_entries is not None and length < min_entries:
            raise ValidationError(self.message)
        if max_entries is not None and length > max_entries:
            raise ValidationError(self.message)

class FilePath(object):
    """Validates that the field represents an existing file."""
    def __init__(self, message=None):
        if not message:
            message = 'Field should be the path of a file.'
        self.message = message

    def __call__(self, form, field):
        import os
        if not os.path.isfile(os.path.join(os.environ['INPUT_DIR'], field.data)):
            raise ValidationError(self.message)

class ConditionallyRequired(object):
    """Validates a field as optional under condition."""
    def __init__(self, field, value, message=None):
        self.field = field
        self.value = value
        if not message:
            message = 'Field is required when {name} is {value}.'.format(name=field, value=value)
        self.message = message

    def __call__(self, form, field):
        if form._fields.get(self.field).data == self.value:
            if field.data is None or field.data == '':
                raise ValidationError(self.message)
        else:
            raise StopValidation()
