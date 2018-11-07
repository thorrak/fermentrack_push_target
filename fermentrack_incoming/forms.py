from django import forms
from fermentrack_incoming.models import UpstreamFermentrackInstallation
from django.core import validators

from django.forms import ModelForm


# For the actual fermentation profile points, we're going to do something more complex. For the overriding
# FermentationProfile object, however, let's just use a model form.
class FermentrackInstallationForm(ModelForm):
    class Meta:
        model = UpstreamFermentrackInstallation
        fields = ['name', 'api_key']

    def __init__(self, *args, **kwargs):
        super(FermentrackInstallationForm, self).__init__(*args, **kwargs)
        for this_field in self.fields:
            self.fields[this_field].widget.attrs['class'] = "form-control"

