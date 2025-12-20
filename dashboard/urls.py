from django.urls import path

from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('proofs/', views.admin_proofs, name='admin_proofs'),
    path('reports/', views.admin_reports, name='admin_reports'),
    # path('analytics/', views.admin_analytics, name='admin_analytics'),
    path('proofs/<int:proof_id>/', views.proof_detail, name='proof_detail'),
    # path('proofs/update-status/', views.proof_update_status, name='proof_update_status'),
    path('users/search/', views.search_users, name='search_users'),
    path('proofs/search/', views.search_proofs, name='search_proofs'),
    path('delete-proof/', views.delete_proof, name='delete_proof'),


    #  path('users/', views.users_list, name='users'),
    path('users/', views.users_list, name='users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/edit/<int:pk>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:pk>/', views.delete_user, name='delete_user'),

     # Add CompanyInfo and Agent views
    path('agents/', views.agents_list, name='agents'),
    path('agents/add/', views.add_agent, name='add_agent'),
    path('agents/edit/<int:pk>/', views.edit_agent, name='edit_agent'),
    path('agents/delete/<int:pk>/', views.delete_agent, name='delete_agent'),

    # Specific CRUD first
    path('company-info/', views.company_info, name='company_info'),
    path('company-info/add/', views.add_company, name='add_company'),
    path('company-info/edit/<int:pk>/', views.edit_company, name='edit_company'),
    path('company-info/delete/<int:pk>/', views.delete_company, name='delete_company'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='edit_profile'),
    path('logout/', views.logout_view, name='logout'),

    path('transactions/<int:id>/', views.transaction_receipt, name='transaction_receipt'),
    path('transactions/', views.transactions, name='transactions'),
    path('transactions/delete/', views.delete_transaction, name='delete_transaction'),

    # path('dashboard/transactions/', views.transactions_list, name='transactions_list'),

    # countries
    path('countries/', views.country_list, name='country_list'),
    path('countries/add/', views.add_country, name='add_country'),
    path('countries/edit/<int:pk>/', views.edit_country, name='edit_country'),
    path('countries/delete/<int:pk>/', views.delete_country, name='delete_country'),

    # currencies
    path('currencies/', views.currency_list, name='currency_list'),
    path('currencies/add/', views.add_currency, name='add_currency'),
    path('currencies/edit/<int:pk>/', views.edit_currency, name='edit_currency'),
    path('currencies/delete/<int:pk>/', views.delete_currency, name='delete_currency'),
    path('get-currencies/<int:country_id>/', views.get_currencies, name='get_currencies'),



    # charge rules
    path('charge-rules/', views.charge_rule_list, name='charge_rule_list'),
    path('charge-rules/add/', views.add_charge_rule, name='add_charge_rule'),
    path('charge-rules/edit/<int:pk>/', views.edit_charge_rule, name='edit_charge_rule'),
    path('charge-rules/delete/<int:pk>/', views.delete_charge_rule, name='delete_charge_rule'),

    # dashboard/urls.py
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),


    path('exchange-rates/', views.exchange_rate_list, name='exchange_rate_list'),
    path('exchange-rates/add/', views.exchange_rate_add, name='exchange_rate_add'),
    path('exchange-rates/<int:id>/edit/', views.exchange_rate_edit, name='exchange_rate_edit'),
    path('exchange-rates/<int:id>/delete/', views.exchange_rate_delete, name='exchange_rate_delete'),
    

     path('upload-proof-steps/', views.proof_steps_list, name='proof_steps_list'),
    path('upload-proof-steps/add/', views.add_proof_step, name='add_proof_step'),
    path('upload-proof-steps/edit/<int:pk>/', views.edit_proof_step, name='edit_proof_step'),
    path('upload-proof-steps/delete/<int:pk>/', views.delete_proof_step, name='delete_proof_step'),
   
    path('add-contact/', views.add_whatsapp_contact, name='add_contact'),
    path('contacts_list/', views.contacts_list, name='contacts_list'),
    path('edit-contact/<int:contact_id>/', views.edit_whatsapp_contact, name='edit_contact'),
    path('delete-contact/<int:contact_id>/', views.delete_whatsapp_contact, name='delete_contact'),
    path('admin/system-status/', views.system_status, name='system_status'),
    path('admin/system-status/delete-old-data/', views.delete_old_data, name='delete_old_data'),

    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/add/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.announcement_update, name='announcement_update'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
]
