from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from crispy_forms.bootstrap import FieldWithButtons


class AskForm(forms.Form):
    question = forms.CharField(
        required=True,
        error_messages={'required':
                        _(u'Please enter something to search for')},)

    def __init__(self, *args, **kwargs):
        super(AskForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_method = "POST"
        self.helper.form_class = 'form-horizontal'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            FieldWithButtons('question', Submit('submit', _(u'Go'),
                                         css_class='btn btn-default')))