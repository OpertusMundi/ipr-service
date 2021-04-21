from flask_wtf import FlaskForm
from wtforms import Field

class BaseForm(FlaskForm):
    """The WTForms base form, it disables CSRF.

    Extends:
        FlaskForm
    """
    class Meta:
        csrf = False

class ListField(Field):
    def process_formdata(self, valuelist):
        self.data = valuelist
