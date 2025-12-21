from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.db.models import Count
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import *


# Admin display settings
admin.site.site_header = "BilSend"
admin.site.site_title = "Bior Investment LTD"
admin.site.index_title = "Dashboard"


admin.site.register(Proof)
admin.site.register(StatusUpdate)
admin.site.register(CompanyInfo)
admin.site.register(Agent)
admin.site.register(Country)
admin.site.register(Currency)
admin.site.register(ChargeRule)
admin.site.register(Transaction)
admin.site.register(ExchangeRate)
admin.site.register(Announcement)
admin.site.register(WhatsAppContact)
@admin.register(User)
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

