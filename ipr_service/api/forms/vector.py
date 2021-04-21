from wtforms import StringField, FloatField, BooleanField
from wtforms.validators import Optional, Length, DataRequired, AnyOf
from .validators import CRS, Encoding, StringList, ListLength, FilePath
from . import BaseForm, ListField

class VectorBaseForm(BaseForm):
    """Base form for vector watermarking.

    Extends:
        BaseForm
    """
    response = StringField('response', default='deferred', validators=[Optional(), AnyOf(['prompt', 'deferred'])])
    original = StringField('original', validators=[DataRequired(), FilePath()])
    delimiter = StringField('delimiter', default=',', validators=[Optional(), Length(min=1, max=2)])
    lat = StringField('lat', validators=[Optional()])
    lon = StringField('lon', validators=[Optional()])
    geom = StringField('geom', validators=[Optional()])
    crs = StringField('crs', validators=[Optional(), CRS()])
    encoding = StringField('encoding', validators=[Optional(), Encoding()])


class VectorEmbedForm(VectorBaseForm):
    """Form for vector watermark embedding.

    Extends:
        VectorBaseForm
    """
    uuid = StringField('key', validators=[DataRequired()])

class VectorDetectForm(VectorBaseForm):
    """Form for vector watermark detection.

    Extends:
        VectorBaseForm
    """
    test = StringField('test', validators=[DataRequired(), FilePath()])
    test_delimiter = StringField('test_delimiter', validators=[Optional(), Length(min=1, max=2)])
    test_lat = StringField('test_lat', validators=[Optional()])
    test_lon = StringField('test_lon', validators=[Optional()])
    test_geom = StringField('test_geom', validators=[Optional()])
    test_crs = StringField('test_crs', validators=[Optional(), CRS()])
    test_encoding = StringField('test_encoding', validators=[Optional(), Encoding()])
    uuids = ListField('keys', validators=[StringList(), ListLength(min_entries=1)])

    def __init__(self, *args, **kwargs):
        """Give default values from the original dataset, in case of empty values."""
        super(VectorDetectForm, self).__init__(*args, **kwargs)
        self.test_delimiter.data = self.test_delimiter.data if self.test_delimiter.data != '' else self.delimiter.data
        self.test_lat.data = self.test_lat.data if self.test_lat.data != '' else self.lat.data
        self.test_lon.data = self.test_lon.data if self.test_lon.data != '' else self.lon.data
        self.test_geom.data = self.test_geom.data if self.test_geom.data != '' else self.geom.data
        self.test_crs.data = self.test_crs.data if self.test_crs.data != '' else self.crs.data
        self.test_encoding.data = self.test_encoding.data if self.test_encoding.data != '' else self.encoding.data

