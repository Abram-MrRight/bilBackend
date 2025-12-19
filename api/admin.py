from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.db.models import Count
from .models import User, Proof, StatusUpdate, CompanyInfo, Agent
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html



@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('image_tag','email', 'fullname','phone_number','location', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'fullname', 'phone_number')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'fullname', 'password', 'role', 'phone_number', 'location', 'image_tag')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'fullname', 'password1', 'password2', 'role'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Hash the password if it was entered in plain text
        if form.cleaned_data.get('password'):
            obj.set_password(form.cleaned_data['password'])
        # Default role to 'client' if not set and not superuser
        if not obj.role and not obj.is_superuser:
            obj.role = 'client'
        super().save_model(request, obj, form, change)

    def image_tag(self, obj):
        if obj.profile_image:
            return format_html('<img src="{}" width="100" height="100" />', obj.profile_image.url)
        return "-"
    image_tag.short_description = 'Image'


@admin.register(Proof)
class ProofAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'image_tag',  # Make sure this matches the method name below
        'sender_name',
        'receiver_name',
        'receiver_contact',
        'status_note',
        'status',
        'amount',
        'currency',
        'created_at'
    )
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('user__email', 'user__fullname', 'sender_name', 'receiver_name')
    ordering = ('-created_at',)

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Image'

# # -----------------------
# # Custom Dashboard
# # -----------------------
# def custom_dashboard(request):
#     total_users = User.objects.count()
#     total_clients = User.objects.filter(role='client').count()
#     total_proofs = Proof.objects.count()
#     top_clients = User.objects.filter(role='client').annotate(
#         proofs_count=Count('proofs')
#     ).order_by('-proofs_count')[:5]

#     context = {
#         'total_users': total_users,
#         'total_clients': total_clients,
#         'total_proofs': total_proofs,
#         'top_clients': top_clients,
#     }
#     return render(request, 'admin/dashboard.html', context)

# # Override admin URLs
# def get_admin_urls(urls):
#     def get_urls():
#         my_urls = [
#             path('dashboard/', admin.site.admin_view(custom_dashboard), name='dashboard'),
#         ]
#         return my_urls + urls()
#     return get_urls

# admin.site.get_urls = get_admin_urls(admin.site.get_urls)

# # Unregister unnecessary models

