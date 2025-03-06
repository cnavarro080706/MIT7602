from django import forms
from django.contrib.auth.models import User
from .models import Profile

# User Registration Form
class UserRegistrationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password', 'password2']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control django-form-field'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control django-form-field'}),
            'username': forms.TextInput(attrs={'class': 'form-control django-form-field'}),
            'email': forms.EmailInput(attrs={'class': 'form-control django-form-field'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control django-form-field'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control django-form-field'}),
        }

    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)
    # Method to check if passwords match
    def check_password(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError('Passwords do not match!')
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Hash the password
        if commit:
            user.save()
            Profile.objects.create(user=user)  # Create a profile for the user
        return user

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

# User Profile Update Form (for username, email)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control django-form-field form-control-sm', 'style':'font-size:small; font-weight: bold;'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control django-form-field form-control-sm', 'style':'font-size:small; font-weight: bold;'}),
            'username': forms.TextInput(attrs={'class': 'form-control django-form-field form-control-sm', 'style':'font-size:small; font-weight: bold;', 'readonly': 'readonly'}),
            'email': forms.EmailInput(attrs={'class': 'form-control django-form-field form-control-sm', 'style':'font-size:small; font-weight: bold;'}),
        }
        def __init__(self, *args, **kwargs):
            super(UserUpdateForm, self).__init__(*args, **kwargs)
            # Make the username field read-only
            self.fields['username'].disabled = True

# Profile Update Form (for profile picture)
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control django-form-field form-control-sm mt-1','style':'font-size:small; font-weight: bold;'}),
        }