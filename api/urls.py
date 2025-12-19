from django.urls import path
from . import views

urlpatterns = [
    
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/profile/', views.profile, name='profile'),

    path('users/', views.list_users, name='list_users'),
    path('users/<int:user_id>/', views.get_user, name='get_user'),
    path('users/<int:user_id>/update/', views.update_user, name='update_user'),
    path('users/delete/', views.delete_self, name='delete_self'),

    path('proof_list/', views.list_proofs, name='list_proofs'),
    path('proofs/', views.upload_proof, name='proofs'),
    path('proofs/<int:proof_id>/', views.get_proof, name='get_proof'),
    path('proofs/<int:proof_id>/delete/', views.delete_proof, name='delete_proof'),
    path('proofs/<int:proof_id>/status/', views.update_proof_status, name='update_proof_status'),
    path('proofs/<int:proof_id>/read/', views.mark_proof_read, name='mark_proof_read'),
    path('proofs/unread-count/', views.unread_count, name='unread_count'),
    path('proofs/search/', views.search_proofs, name='search_proofs'),
    path('countries/', views.CountryListView.as_view(), name='country-list'),
    path('api/countries/<int:country_id>/currencies/', views.CurrencyListByCountry.as_view(), name='currencies-by-country'),

    path('charge_rules/', views.ChargeRuleListView.as_view(), name='charge_rule_list_api'),
    path('announcements/', views.announcement_list_create, name='announcement_list_create'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    path('agents/',views.list_agents, name='agents'),
    path('company_info/', views.list_company_info, name='company_info'),
    path('upload_proof_steps/', views.get_upload_proof_steps, name='upload_proof_steps'),
    path("password-reset/request/",views. request_password_reset, name="password-reset-request"),
    path("password-reset/confirm/", views.confirm_password_reset, name="password-reset-confirm"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
    path('get_whatsapp_contact/', views.get_whatsapp_contact, name='get_whatsapp_contact_detail'),

    path('transactions/', views.get_user_transactions, name='user-transactions'),

]
