from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from crispy_forms.bootstrap import FieldWithButtons

from tinymce.widgets import TinyMCE

from notes.models import STATUS_OPTIONS, PRIORITY_OPTIONS, RECURRENCE_OPTIONS, Note

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        exclude = ['create_date', 'link_check_date', 'user']

    url = forms.CharField(required=False)
    title = forms.CharField(required=True)
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    description = forms.CharField(widget=TinyMCE(
                                mce_attrs={
                                    'content_style': 'body { width: 100%; height: 50px; }',
                                }),
                                  required=False)
    tags = forms.CharField(
                required=True,
                error_messages={'required':
                                _('Please enter at least one tag')},)
    status = forms.ChoiceField(
        choices=STATUS_OPTIONS,
        required=True,
    )
    priority = forms.ChoiceField(
        choices=[('', 'Select an option')] + list(PRIORITY_OPTIONS),
        required=False,
    )
    recurrence = forms.ChoiceField(
        choices=[('', 'Select an option')] + list(RECURRENCE_OPTIONS),
        required=False,
    )
    reminder_days = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super(NoteForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-4'
        self.helper.layout = Layout(
                'title',
                'url',
                'due_date',
                'tags',
                'status',
                'priority',
                'recurrence',
                'reminder_days',
                'estimated_effort',
                'description',
                Div(
                   Submit('action', 'save', css_class='btn btn-default', title=_("Save")),
                    Submit('action', 'save_and_add',  css_class='btn btn-default', title=_("Save and add another")),
                   css_class='col-lg-offset-2 col-lg-4',
                ),
            )


class SearchForm(forms.Form):
    q = forms.CharField(
        required=True,
        error_messages={'required':
                        _(u'Please enter something to search for')},)

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_method = "GET"
        self.helper.form_class = 'form-horizontal'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            FieldWithButtons('q', Submit('submit', _(u'Go'),
                                         css_class='btn btn-default')))
