from wtforms import StringField, FloatField, IntegerField
from wtforms.validators import Optional, Length, DataRequired, AnyOf, NumberRange
from .validators import CRS, ListLength, FilePath, ConditionallyRequired
from . import BaseForm

class RasterBaseForm(BaseForm):
    """Base form for raster watermarking.

    Extends:
        BaseForm
    """
    response = StringField('response', default='deferred', validators=[Optional(), AnyOf(['prompt', 'deferred'])])
    raster = StringField('raster', validators=[DataRequired(), FilePath()])

class RasterEmbedForm(RasterBaseForm):
    """Form for raster invisible watermark embedding.

    Extends:
        RasterBaseForm
    """
    message = StringField('message', validators=[DataRequired()])

class RasterDetectForm(RasterBaseForm):
    """Form for raster invisible watermark detecting.

    Extends:
        RasterBaseForm
    """
    watermarked = StringField('watermarked', validators=[DataRequired(), FilePath()])

class RasterVisibleEmbedForm(RasterBaseForm):
    """Form for raster watermark embedding.

    Extends:
        RasterBaseForm
    """
    watermark = StringField('watermark', validators=[DataRequired(), FilePath()])
    crs = StringField('crs', validators=[Optional(), CRS()])
    transparency = FloatField('transparency', default=1.0, validators=[Optional(), NumberRange(min=0.0, max=1.0)])
    fit = StringField('fit', default='width', validators=[Optional(), AnyOf(['stretch', 'height', 'width', 'original', 'tile'])])
    position = StringField('position', default='center', validators=[Optional(), AnyOf(['topleft', 'topright', 'bottomright', 'bottomleft', 'center'])])
    distance_x = IntegerField('distance_x', validators=[ConditionallyRequired('fit', 'tile'), NumberRange(min=1)])
    distance_y = IntegerField('distance_y', validators=[ConditionallyRequired('fit', 'tile'), NumberRange(min=1)])
