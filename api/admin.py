from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpRequest
from django.shortcuts import render
from django.urls import path
from django.db.models import Count, Q
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import *

# Create custom admin site
class CustomAdminSite(admin.AdminSite):
    def has_permission(self, request: HttpRequest) -> bool:
        """Override to allow only superusers"""
        return request.user.is_active and request.user.is_superuser
    
    def login(self, request, extra_context=None):
        """Custom login view"""
        return super().login(request, extra_context)

# Use custom admin site instead of default
custom_admin_site = CustomAdminSite(name='terminator')

# Register your models with custom admin site
@admin.register(User, site=custom_admin_site)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'image_tag',
        'email',
        'fullname',
        'phone_number',
        'location',
        'role',
        'is_staff',
        'is_active',
    )
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'fullname', 'phone_number')
    ordering = ('email',)
    readonly_fields = ('image_tag',)
    
    def get_queryset(self, request):
        """Show only super_admin and admin users"""
        qs = super().get_queryset(request)
        
        # Superusers see all users
        if request.user.is_superuser:
            return qs
        
        # Staff see only users with admin or super_admin roles
        if request.user.is_staff:
            return qs.filter(role__in=['admin', 'super_admin'])
        
        # Regular users see only themselves
        return qs.filter(id=request.user.id)
    
    def has_view_permission(self, request, obj=None):
        """Control view permissions"""
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        # Staff can only view staff users or themselves
        if request.user.is_staff:
            return obj.is_staff or obj.id == request.user.id
        return obj.id == request.user.id
    
    def has_change_permission(self, request, obj=None):
        """Control edit permissions"""
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        # Staff can edit staff users or themselves
        if request.user.is_staff:
            return obj.is_staff or obj.id == request.user.id
        return obj.id == request.user.id
    
    def has_delete_permission(self, request, obj=None):
        """Control delete permissions"""
        if request.user.is_superuser:
            return True
        if obj is None:
            return False
        # Don't allow deleting yourself
        if obj.id == request.user.id:
            return False
        # Staff can delete other staff users
        if request.user.is_staff and obj.is_staff:
            return True
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """Make specific fields readonly for non-superusers"""
        if not request.user.is_superuser and obj and obj.id != request.user.id:
            # Staff can't change role or permissions of other staff
            return self.readonly_fields + ('role', 'is_staff', 'is_superuser')
        return self.readonly_fields
    
    fieldsets = (
        (None, {
            'fields': (
                'email',
                'fullname',
                'password',
                'role',
                'phone_number',
                'location',
                'profile_image', 
                'image_tag',     
            )
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'fullname',
                'password1',
                'password2',
                'role',
                'is_staff',
                'is_active',
            ),
        }),
    )
    
    def image_tag(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" width="80" height="80" style="border-radius:8px;" />',
                obj.profile_image.url
            )
        return "No Image"
    image_tag.short_description = 'Profile Image'

# Keep the default admin site settings for any other admin interfaces
admin.site.site_header = "BilSend"
admin.site.site_title = "Bior Investment LTD"
admin.site.index_title = "Dashboard"