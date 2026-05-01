from django import forms
from django.contrib.auth.models import User

from api.models import Agent, Announcement, ChargeRule, CompanyInfo, Country, Currency, UploadProofStep, User, WhatsAppContact
from django.contrib.auth.forms import UserCreationForm, UserChangeForm


class CountryForm(forms.ModelForm):
    class Meta:
        model = Country
        fields = ['name', 'code']

class CurrencyForm(forms.ModelForm):
    class Meta:
        model = Currency
        fields = ['country', 'name', 'code', 'symbol']

class ChargeRuleForm(forms.ModelForm):
    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        empty_label="Select Country",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    currency = forms.ModelChoiceField(
      queryset=Currency.objects.all(),        empty_label="Select Currency",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ChargeRule
        fields = ['country', 'currency', 'min_amount', 'max_amount', 'charge_amount']
        widgets = {
            'min_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'charge_amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'country' in self.data:
            try:
                country_id = int(self.data.get('country'))
                self.fields['currency'].queryset = Currency.objects.filter(country_id=country_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['currency'].queryset = Currency.objects.filter(country=self.instance.country)



class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['fullname', 'email', 'phone_number', 'role', 'location', 'profile_image', 'password1', 'password2']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'fullname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class UserEditForm(UserChangeForm):
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['fullname', 'email', 'phone_number', 'role', 'location', 'profile_image', 'password']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'fullname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_password(self):
        # Keep old password if blank
        return self.initial["password"]
class UserDetailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['fullname', 'email', 'phone_number', 'role', 'location', 'profile_image']
        widgets = {
            'fullname': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'role': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'disabled': True}),
        }
class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name', 'account_name', 'phone', 'email', 'logo_image', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        
TYPE_CHOICES = [
    ('logo', 'Logo'),
    ('about', 'About'),
    ('phone', 'Phone'),
    ('email', 'Email'),
    ('address', 'Address'),
]

TITLE_CHOICES = [
    ('logo', 'Logo'),
    ('about', 'About Us'),
    ('phone', 'Phone Numbers'),
    ('email', 'Email'),
    ('address', 'Address'),
]

ICON_CHOICES = [
    ('info_outline', 'Info Outline'),
    ('phone', 'Phone'),
    ('email', 'Email'),
    ('location_on', 'Location On'),
    ('business', 'Business'),
    ('home', 'Home'),
    ('logo', 'Logo'),
]


class CompanyInfoForm(forms.ModelForm):
    type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'typeSelect'
        })
    )

    title = forms.ChoiceField(
        choices=TITLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'titleField'
        })
    )

    icon = forms.ChoiceField(
        choices=ICON_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'iconField'
        })
    )

    color = forms.CharField(
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control',
            'id': 'colorField'
        })
    )

    logo_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'id': 'logoField'
        })
    )

    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'id': 'contentField'
        })
    )

    class Meta:
        model = CompanyInfo
        fields = ['type', 'title', 'content', 'icon', 'color', 'logo_image']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

ICON_CHOICES = [
    ("chat", "Chat"),
    ("attach_file", "Attach File"),
    ("image", "Image"),
    ("send", "Send"),
    ("check_circle", "Check Circle"),
    ("info_outline", "Info Outline"),
]

class UploadProofStepForm(forms.ModelForm):
    step_number = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    title = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}))
    icon = forms.ChoiceField(choices=ICON_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    color = forms.CharField(widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}))

    class Meta:
        model = UploadProofStep
        fields = ['step_number', 'title', 'description', 'icon', 'color']

class WhatsAppContactForm(forms.ModelForm):
    class Meta:
        model = WhatsAppContact
        fields = ['name', 'phone_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '211XXXXX'}),
        }

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'description', 'image', 'is_active', 'start_at', 'end_at']
        widgets = {
            'start_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }