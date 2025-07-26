from django import forms
from .models import SubnetBlock

class SubnetBlockForm(forms.ModelForm):
    class Meta:
        model = SubnetBlock
        fields = ['network', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }