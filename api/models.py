from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from django.conf import settings



# Base model with timestamps

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, fullname, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, fullname=fullname, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, fullname, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, fullname, password, **extra_fields)


# User model
class User(AbstractUser):
    ROLE_CHOICES = (
        ('client', 'Client'),
        ('admin', 'Admin'),
        ('super_admin', 'Super Admin'),
    )

    username = None
    email = models.EmailField(unique=True)
    fullname = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    location = models.CharField(max_length=255, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)

    is_staff = models.BooleanField(default=False)      
    is_superuser = models.BooleanField(default=False)  
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager() 

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['fullname']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.fullname or self.email



# Proof model
class Proof(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('money_received', 'Money Received'),
        ('receiver_contacted', 'Receiver Contacted'),
        ('money_delivered', 'Money Delivered'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proofs')
    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_proofs'
    ) 
    image = models.ImageField(upload_to='proof-images/')
    sender_name = models.CharField(max_length=255, null=True, blank=True)
    receiver_name = models.CharField(max_length=255, null=True, blank=True)
    receiver_contact = models.CharField(max_length=50, null=True, blank=True)
    receiver_email = models.EmailField(null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    
    # NEW: link proof to a country
    country = models.ForeignKey(
        'Country',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proofs'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_note = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'proofs'

    def __str__(self):
        return f'Proof {self.id} - {self.status}'


# Status Update model
class StatusUpdate(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('money_received', 'Money Received'),
        ('receiver_contacted', 'Receiver Contacted'),
        ('money_delivered', 'Money Delivered'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='status_updates')
    proof = models.ForeignKey(Proof, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = 'status_updates'

    def __str__(self):
        return f"StatusUpdate {self.id} - {self.status}"



# Company Info model
class CompanyInfo(models.Model):
    TYPE_CHOICES = [
        ('logo', 'Logo'),
        ('about', 'About'),
        ('phone', 'Phone'),
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

    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='about')
    title = models.CharField(max_length=255)
    content = models.TextField()
    icon = models.CharField(max_length=50, choices=ICON_CHOICES, null=True, blank=True)
    color = models.CharField(max_length=7, default='#2196F3', null=True, blank=True)
    logo_image = models.ImageField(upload_to='company-images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.type})"


# Agent model
class Agent(TimeStampedModel):
    name = models.CharField(max_length=255)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    logo_image = models.ImageField(upload_to='agent-logos/', null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'agents'

    def __str__(self):
        return self.name


class ProofRead(models.Model):
    proof = models.ForeignKey('Proof', on_delete=models.CASCADE, related_name='proof_reads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='proof_reads')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'proof_reads'
        unique_together = ('proof', 'user') 

    def __str__(self):
        return f"ProofRead: Proof {self.proof.id} - User {self.user.id} - Read: {self.is_read}"


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # UG, KE, etc.
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


class Currency(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="currencies")
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)
    symbol = models.CharField(max_length=10, null=True, blank=True)
    is_active = models.BooleanField(default=True)  # ADD THIS
    color = models.CharField(max_length=7, default="#6c757d")

    class Meta:
        unique_together = ('country', 'code')

    def __str__(self):
        return f"{self.code}"

class ChargeRule(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    charge_amount = models.DecimalField(max_digits=12, decimal_places=2)
    charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('country', 'currency', 'min_amount', 'max_amount')

    def __str__(self):
        return f"{self.country.name} | {self.currency.code} | {self.min_amount}-{self.max_amount}"


class Transaction(models.Model):
    proof = models.OneToOneField(
        Proof,
        on_delete=models.SET_NULL,  
        null=True,                
        blank=True,               
        related_name='transaction'
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transactions')
    sender_name = models.CharField(max_length=255)
    receiver_name = models.CharField(max_length=255)
    receiver_contact = models.CharField(max_length=50, blank=True, null=True)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='UGX')

    transaction_reference = models.CharField(max_length=100, unique=True)

    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_transactions')
    confirmed_at = models.DateTimeField(null=True, blank=True, default=timezone.now)

    receipt_file = models.FileField(upload_to='receipts/', blank=True, null=True)

    # NEW FIELDS
    charge_rule = models.ForeignKey(ChargeRule, on_delete=models.SET_NULL, null=True, blank=True)
    charge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # ADD THESE FIELDS for better analytics
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    original_currency = models.CharField(max_length=10, default='UGX')  # Currency used
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True) 
    ugx_equivalent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    exchange_rate_used = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    
    # Add method to calculate UGX equivalent
    def save(self, *args, **kwargs):
        if not self.ugx_equivalent and self.original_amount and self.original_currency:
            try:
                if self.original_currency == 'UGX':
                    self.ugx_equivalent = self.original_amount
                else:
                    rate = ExchangeRate.objects.filter(
                        currency=self.original_currency
                    ).latest('updated_at')
                    self.ugx_equivalent = self.original_amount * rate.rate_to_ugx
                    self.exchange_rate_used = rate.rate_to_ugx
            except ExchangeRate.DoesNotExist:
                self.ugx_equivalent = self.original_amount  # Fallback
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transaction #{self.transaction_reference} - {self.amount} {self.currency}"
    

class ExchangeRate(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)  # added FK
    currency = models.CharField(max_length=10, unique=True)
    rate_to_ugx = models.DecimalField(max_digits=20, decimal_places=4)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency} → {self.rate_to_ugx} UGX"
    
class Announcement(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='announcements/', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='announcements')
    is_active = models.BooleanField(default=False)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class UploadProofStep(models.Model):
    step_number = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon = models.CharField(max_length=50)  # e.g., "chat", "attach_file"
    color = models.CharField(max_length=7, default="#2196F3")  # hex color

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"Step {self.step_number}: {self.title}"
    
class WhatsAppContact(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Default'}: {self.phone_number}"