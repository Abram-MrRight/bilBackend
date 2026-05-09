import os
from pyexpat.errors import messages
import uuid
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from api.models import Agent, Announcement, ChargeRule, CompanyInfo, Country, Currency, ExchangeRate, Proof, Transaction, UploadProofStep, User, WhatsAppContact
from datetime import datetime, timedelta
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User as DjangoUser 
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.http import HttpResponseBadRequest
from django.template.loader import render_to_string
from django.db.models import Count, Sum, Avg, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.apps import apps
from django.forms import modelform_factory
from django.contrib import messages
from datetime import datetime
from api.utils import convert_currency
from dashboard.forms import AgentForm, AnnouncementForm, ChargeRuleForm, CompanyInfoForm, CountryForm, CurrencyForm, ProfileForm, UploadProofStepForm, UserDetailForm, UserEditForm, UserRegistrationForm, WhatsAppContactForm
# views.py
import datetime
import io
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models import Q
from openpyxl import Workbook  # for Excel
from reportlab.pdfgen import canvas  # for PDF


from openpyxl.styles import Font, Alignment
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib.auth.decorators import login_required, user_passes_test

from django.shortcuts import render
from django.db.models import Sum, Count
import json

from api.models import Transaction, ExchangeRate
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator

from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, F, Q
from decimal import Decimal
from collections import defaultdict
from django.conf import settings 

import shutil
import psutil
from django.shortcuts import render
from datetime import datetime, timedelta

def get_file_size(file_field):
    """Return file size in MB, 0 if no file."""
    if file_field and file_field.name:
        try:
            return os.path.getsize(file_field.path) / (1024 ** 2) 
        except:
            return 0
    return 0

import random

def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

@staff_member_required
def system_status(request):
    #  CPU 
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_high = cpu_percent > 80
    cpu_warning = 60 < cpu_percent <= 80

    #  RAM 
    mem = psutil.virtual_memory()
    ram_total = round(mem.total / (1024 ** 3), 2)
    ram_used = round(mem.used / (1024 ** 3), 2)
    ram_percent = mem.percent
    ram_high = ram_percent > 80
    ram_warning = 60 < ram_percent <= 80

    #  Disk 
    disk = shutil.disk_usage('/')
    disk_total = round(disk.total / (1024 ** 3), 2)
    disk_used = round(disk.used / (1024 ** 3), 2)
    disk_percent = round(disk.used / disk.total * 100, 2)
    disk_high = disk_percent > 80
    disk_warning = 60 < disk_percent <= 80

    #  Swap 
    swap = psutil.swap_memory()
    swap_total = round(swap.total / (1024 ** 3), 2)
    swap_used = round(swap.used / (1024 ** 3), 2)
    swap_percent = swap.percent
    swap_high = swap_percent > 80
    swap_warning = 60 < swap_percent <= 80

    #  Old Data (>3 months) 
    three_months_ago = timezone.now() - timedelta(days=90)

    old_proofs = Proof.objects.filter(created_at__lt=three_months_ago)
    old_transactions = Transaction.objects.filter(confirmed_at__lt=three_months_ago)
    old_announcements = Announcement.objects.filter(created_at__lt=three_months_ago)

    def get_files_size(queryset, file_field):
        total_bytes = 0
        for obj in queryset:
            file = getattr(obj, file_field, None)
            if file and os.path.exists(file.path):
                total_bytes += os.path.getsize(file.path)
        return round(total_bytes / (1024 * 1024), 2)  # in MB

    context = {
        'cpu_percent': cpu_percent,
        'cpu_high': cpu_high,
        'cpu_warning': cpu_warning,
        'ram_total': ram_total,
        'ram_used': ram_used,
        'ram_percent': ram_percent,
        'ram_high': ram_high,
        'ram_warning': ram_warning,
        'disk_total': disk_total,
        'disk_used': disk_used,
        'disk_percent': disk_percent,
        'disk_high': disk_high,
        'disk_warning': disk_warning,
        'swap_total': swap_total,
        'swap_used': swap_used,
        'swap_percent': swap_percent,
        'swap_high': swap_high,
        'swap_warning': swap_warning,
        'old_proofs_count': old_proofs.count(),
        'old_proofs_size': get_files_size(old_proofs, 'image'),
        'old_transactions_count': old_transactions.count(),
        'old_transactions_size': get_files_size(old_transactions, 'receipt_file'),
        'old_announcements_count': old_announcements.count(),
        'old_announcements_size': get_files_size(old_announcements, 'image'),
    }
    return render(request, 'system_monitoring/system_status.html', context)


def delete_old_data(request):
    """Delete all old files (Proofs, Transactions, Announcements) older than 3 months"""
    three_months_ago = datetime.now() - timedelta(days=90)
    
    # Delete old proofs
    old_proofs = Proof.objects.filter(created_at__lt=three_months_ago)
    proofs_count = old_proofs.count()
    for proof in old_proofs:
        if proof.image:
            try:
                os.remove(proof.image.path)
            except:
                pass
    old_proofs.delete()

    # Delete old transactions
    old_transactions = Transaction.objects.filter(confirmed_at__lt=three_months_ago)
    transactions_count = old_transactions.count()
    for txn in old_transactions:
        if txn.receipt_file:
            try:
                os.remove(txn.receipt_file.path)
            except:
                pass
    old_transactions.delete()

    # Delete old announcements
    old_announcements = Announcement.objects.filter(created_at__lt=three_months_ago)
    announcements_count = old_announcements.count()
    for ann in old_announcements:
        if ann.image:
            try:
                os.remove(ann.image.path)
            except:
                pass
    old_announcements.delete()

    messages.success(request, f"{proofs_count} old proof(s), {transactions_count} old transaction(s), "
                              f"and {announcements_count} old announcement(s) deleted successfully.")
    return redirect('system_status')

def format_money(amount, decimals=4):
    """Format Decimal or float to string with commas and fixed decimals."""
    amount = Decimal(amount).quantize(Decimal(f"1.{'0'*decimals}"), rounding=ROUND_HALF_UP)
    return f"{amount:,.{decimals}f}"
def analytics_dashboard(request):
    
    # BASE SETUP
    
    base_currency_code = getattr(settings, 'BASE_CURRENCY', 'UGX')

    base_currency = Currency.objects.filter(
        code=base_currency_code
    ).first()

    # fallback if configured currency does not exist
    if not base_currency:
        base_currency = Currency.objects.filter(code='UGX').first()

    # final fallback
    if not base_currency:
        base_currency = Currency.objects.first()

    now = timezone.now()
    date_filter = request.GET.get('period', 'all')

    start_date = None
    if date_filter == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'week':
        start_date = now - timedelta(days=7)
    elif date_filter == 'month':
        start_date = now - timedelta(days=30)
    elif date_filter == 'year':
        start_date = now - timedelta(days=365)

    transactions = Transaction.objects.all()
    if start_date:
        transactions = transactions.filter(confirmed_at__gte=start_date)

    
    # GLOBAL TOTALS (BASE CURRENCY)
    
    total_amount_base = Decimal(str(
        transactions.aggregate(total=Sum('ugx_equivalent'))['total'] or 0
    ))

    total_charges_base = Decimal(str(
        transactions.aggregate(total=Sum('charge_amount'))['total'] or 0
    ))

    total_net_base = total_amount_base - total_charges_base

    overall_charge_rate = (
        (total_charges_base / total_amount_base) * Decimal('100')
        if total_amount_base > 0 else Decimal('0')
    )

    # PER-CURRENCY STATISTICS
    
    currency_stats = []

    for currency in Currency.objects.all():
        txs = transactions.filter(original_currency=currency)
        if not txs.exists():
            continue

        total_original = Decimal(str(
            txs.aggregate(total=Sum('original_amount'))['total'] or 0
        ))

        total_charge = Decimal(str(
            txs.aggregate(total=Sum('charge_amount'))['total'] or 0
        ))

        total_base = Decimal(str(
            txs.aggregate(total=Sum('ugx_equivalent'))['total'] or 0
        ))

        avg_amount = Decimal(str(
            txs.aggregate(avg=Avg('original_amount'))['avg'] or 0
        ))

        avg_charge = Decimal(str(
            txs.aggregate(avg=Avg('charge_amount'))['avg'] or 0
        ))

        charge_rate = (
            (total_charge / total_original) * Decimal('100')
            if total_original > 0 else Decimal('0')
        )

        percentage = (
            (total_base / total_amount_base) * Decimal('100')
            if total_amount_base > 0 else Decimal('0')
        )

         # SAFE exchange rate lookup
        try:
            exchange_rate = convert_currency(1, currency, base_currency)
        except ExchangeRate.DoesNotExist:
            exchange_rate = Decimal('0')

        currency_stats.append({
            'currency': currency.code,
            'currency_name': currency.name,
            'symbol': currency.symbol,
            'count': txs.count(),
            'total_amount': float(total_original),
            'total_charge': float(total_charge),
            'total_net': float(total_original - total_charge),
            'avg_amount': float(avg_amount),
            'avg_charge': float(avg_charge),
            'base_amount': float(total_base),
            'charge_rate': float(charge_rate),
            'percentage': float(percentage),
            'color': random_color(),
            'exchange_rate': exchange_rate,
        })

    
    # TOP STAFF PERFORMANCE
    
    top_staff = transactions.exclude(
        confirmed_by__isnull=True
    ).values(
        'confirmed_by__fullname',
        'confirmed_by__email'
    ).annotate(
        transaction_count=Count('id'),
        total_amount=Sum('ugx_equivalent'),
        total_charge=Sum('charge_amount'),
        avg_amount=Avg('ugx_equivalent')
    ).order_by('-total_amount')[:5]

    
    # TRANSACTION TREND (LAST 7 DAYS)
    
    trend_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_total = transactions.filter(
            confirmed_at__date=day.date()
        ).aggregate(
            total=Sum('ugx_equivalent')
        )['total'] or Decimal('0')

        trend_data.append({
            'date': day.strftime('%a'),
            'amount': float(day_total),
        })

    
    # ADDITIONAL METRICS
    
    active_countries = Country.objects.filter(
        id__in=transactions.exclude(
            country__isnull=True
        ).values_list('country', flat=True).distinct()
    )

    total_transactions = transactions.count()

    avg_amount = Decimal(str(
        transactions.aggregate(avg=Avg('ugx_equivalent'))['avg'] or 0
    ))

    avg_charge = Decimal(str(
        transactions.aggregate(avg=Avg('charge_amount'))['avg'] or 0
    ))

    
    # CONTEXT
    
    context = {
        # Base totals
        'base_currency': base_currency.code,
        'total_amount_base': total_amount_base,
        'total_charges_base': total_charges_base,
        'total_net_base': total_net_base,
        'overall_charge_rate': overall_charge_rate,

        # Counts
        'total_transactions': total_transactions,
        'currency_count': len(currency_stats),
        'country_count': active_countries.count(),
        'staff_count': transactions.exclude(
            confirmed_by__isnull=True
        ).values('confirmed_by').distinct().count(),

        # Currency analytics
        'currency_stats': currency_stats,

        # Staff & trends
        'top_staff': top_staff,
        'trend_data': json.dumps(trend_data),

        # Reference data
        'active_countries': active_countries,
        'exchange_rates': ExchangeRate.objects.all().order_by('created_at'),
        'all_currencies': Currency.objects.all(),

        # Averages
        'avg_amount': avg_amount,
        'avg_charge': avg_charge,

        # UI
        'period': date_filter,
        'last_update': now,
    }

    return render(request, 'dashboard/analytics.html', context)

def get_color_for_currency(currency_code):
    """Assign consistent colors for currencies"""
    colors = {
        'USD': '#0052B4',  # Blue
        'UGX': '#FCDC04',  # Yellow
        'EUR': '#003399',  # Dark Blue
        'GBP': '#C8102E',  # Red
        'KES': '#006600',  # Green
        'TZS': '#1EB53A',  # Light Green
        'RWF': '#00A1DE',  # Cyan
        'CNY': '#DE2910',  # Chinese Red
    }
    return colors.get(currency_code, '#6c757d')  # Default gray

def currency_management(request):
    """View for managing currencies and their settings"""
    if not request.user.is_superuser:
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Handle currency creation/updates
        pass
    
    currencies = Currency.objects.select_related('country').all()
    exchange_rates = ExchangeRate.objects.all()
    countries = Country.objects.all()
    
    context = {
        'currencies': currencies,
        'exchange_rates': exchange_rates,
        'countries': countries,
    }
    
    return render(request, 'dashboard/analytics.html', context)


@login_required(login_url='admin_login')
def country_list(request):
    countries = Country.objects.all()
    return render(request, 'country/list.html', {'countries': countries})

@login_required(login_url='admin_login')
def add_country(request):
    if request.method == 'POST':
        form = CountryForm(request.POST)
        if form.is_valid():
            country = form.save(commit=False)
            country.created_by = request.user
            country.save()
            messages.success(request, 'Country added successfully')
            return redirect('country_list')
    else:
        form = CountryForm()
    return render(request, 'country/add.html', {'form': form})

@login_required(login_url='admin_login')

def edit_country(request, pk):
    country = get_object_or_404(Country, pk=pk)
    if request.method == 'POST':
        form = CountryForm(request.POST, instance=country)
        if form.is_valid():
            form.save()
            messages.success(request, 'Country updated successfully')
            return redirect('country_list')
    else:
        form = CountryForm(instance=country)
    return render(request, 'country/edit.html', {'form': form})

@login_required(login_url='admin_login')

def delete_country(request, pk):
    country = get_object_or_404(Country, pk=pk)
    country.delete()
    messages.success(request, 'Country deleted successfully')
    return redirect('country_list')

#  CURRENCY VIEWS 
@login_required(login_url='admin_login')

def currency_list(request):
    currencies = Currency.objects.select_related('country').all()
    return render(request, 'currency/list.html', {'currencies': currencies})

@login_required(login_url='admin_login')

def add_currency(request):
    if request.method == 'POST':
        form = CurrencyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Currency added successfully')
            return redirect('currency_list')
    else:
        form = CurrencyForm()
    return render(request, 'currency/add.html', {'form': form})

@login_required(login_url='admin_login')

def edit_currency(request, pk):
    currency = get_object_or_404(Currency, pk=pk)
    if request.method == 'POST':
        form = CurrencyForm(request.POST, instance=currency)
        if form.is_valid():
            form.save()
            messages.success(request, 'Currency updated successfully')
            return redirect('currency_list')
    else:
        form = CurrencyForm(instance=currency)
    return render(request, 'currency/edit.html', {'form': form})

@login_required(login_url='admin_login')

def delete_currency(request, pk):
    currency = get_object_or_404(Currency, pk=pk)
    currency.delete()
    messages.success(request, 'Currency deleted successfully')
    return redirect('currency_list')

def get_currencies(request, country_id):
    currencies = Currency.objects.filter(country_id=country_id)
    data = [{'id': c.id, 'name': c.name} for c in currencies]
    return JsonResponse(data, safe=False)


#  CHARGERULE VIEWS 
@login_required(login_url='admin_login')

def charge_rule_list(request):
    rules = ChargeRule.objects.select_related('country', 'currency').all()
    return render(request, 'charge_rule/list.html', {'rules': rules})

@login_required(login_url='admin_login')

def add_charge_rule(request):
    if request.method == 'POST':
        form = ChargeRuleForm(request.POST)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.updated_by = request.user
            charge.save()
            messages.success(request, 'Charge rule added successfully')
            return redirect('charge_rule_list')
    else:
        form = ChargeRuleForm()
    return render(request, 'charge_rule/add.html', {'form': form})

@login_required(login_url='admin_login')

def edit_charge_rule(request, pk):
    charge = get_object_or_404(ChargeRule, pk=pk)
    if request.method == 'POST':
        form = ChargeRuleForm(request.POST, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.updated_by = request.user
            charge.save()
            messages.success(request, 'Charge rule updated successfully')
            return redirect('charge_rule_list')
    else:
        form = ChargeRuleForm(instance=charge)
    return render(request, 'charge_rule/edit.html', {'form': form})

@login_required(login_url='admin_login')

def delete_charge_rule(request, pk):
    charge = get_object_or_404(ChargeRule, pk=pk)
    charge.delete()
    messages.success(request, 'Charge rule deleted successfully')
    return redirect('charge_rule_list')

def exchange_rate_add(request):
    currencies = Currency.objects.all()

    if request.method == "POST":
        base_currency_id = request.POST.get("base_currency")
        target_currency_id = request.POST.get("target_currency")
        rate = request.POST.get("rate")
        source = request.POST.get("source", "manual")
        valid_from = request.POST.get("valid_from")

       
        # VALIDATION
       
        if not all([base_currency_id, target_currency_id, rate, valid_from]):
            messages.error(request, "All fields are required.")
            return redirect("exchange_rate_add")

        if base_currency_id == target_currency_id:
            messages.error(request, "Base and target currency cannot be the same.")
            return redirect("exchange_rate_add")

        try:
            base_currency = Currency.objects.get(id=int(base_currency_id))
            target_currency = Currency.objects.get(id=int(target_currency_id))
            rate = Decimal(rate)
            valid_from = timezone.datetime.fromisoformat(valid_from)
        except Exception:
            messages.error(request, "Invalid input data.")
            return redirect("exchange_rate_add")

       
        # CLOSE PREVIOUS ACTIVE RATE
       
        ExchangeRate.objects.filter(
            base_currency=base_currency,
            target_currency=target_currency,
            valid_to__isnull=True
        ).update(valid_to=timezone.now())

       
        # CREATE NEW RATE
       
        ExchangeRate.objects.create(
            base_currency=base_currency,
            target_currency=target_currency,
            rate=rate,
            source=source,
            valid_from=valid_from
        )

        messages.success(
            request,
            f"Exchange rate {base_currency.code} → {target_currency.code} added successfully."
        )
        return redirect("exchange_rate_list")

    return render(request, "exchange_rate/exchange_rate_form.html", {
        "currencies": currencies,
        "action": "Add",
    })


@csrf_protect
@login_required(login_url='admin_login')
def admin_dashboard(request):
    # Main totals
    total_staff = User.objects.filter(role='admin').count()
    total_clients = User.objects.filter(role='client').count()
    total_proofs = Proof.objects.count()
    total_transactions = Transaction.objects.count()

    # Proof status counts
    proof_stats = Proof.objects.values('status').annotate(count=Count('id'))
    proof_stats_dict = {ps['status'].capitalize(): ps['count'] for ps in proof_stats}

    # Top 5 active clients
    top_clients = (
        User.objects.filter(role='client')
        .annotate(transactions_count=Count('transactions'))
        .order_by('-transactions_count')[:5]
    )

    # Weekly submissions (past 7 days)
    today = timezone.now().date()
    week_labels = [(today - timedelta(days=i)).strftime('%a') for i in reversed(range(7))]
    week_data = [
        Proof.objects.filter(created_at__date=today - timedelta(days=i)).count()
        for i in reversed(range(7))
    ]

    context = {
        'total_staff': total_staff,
        'total_clients': total_clients,
        'total_proofs': total_proofs,
        'proof_stats': proof_stats_dict,
        'top_clients': top_clients,
        'labels': week_labels,
        'week_data': week_data,
        'total_transactions':total_transactions,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@csrf_protect
@login_required(login_url='admin_login')
def admin_proofs(request):
    # Get all proofs
    proofs_list = Proof.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_proofs = proofs_list.count()
    pending_count = proofs_list.filter(status='pending').count()
    received_count = proofs_list.filter(status='money_received').count()
    delivered_count = proofs_list.filter(status='money_delivered').count()    
    
    # Handle search
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        proofs_list = proofs_list.filter(
            Q(sender_name__icontains=search_query) |
            Q(receiver_name__icontains=search_query) |
            Q(receiver_contact__icontains=search_query) |
            Q(amount__icontains=search_query) |
            Q(country__icontains=search_query) |
            Q(currency__icontains=search_query) |
            Q(user__fullname__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    if status_filter:
        proofs_list = proofs_list.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(proofs_list, 20)  # Show 20 proofs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dashboard/proofs.html', {
        'proofs': page_obj,
        'page_obj': page_obj,
        'title': 'Admin Proofs',
        'total_proofs': total_proofs,
        'pending_count': pending_count,
        'received_count': received_count,
        'delivered_count': delivered_count,
        'search_query': search_query,
        'status_filter': status_filter,
    })

@login_required(login_url='admin_login')
def delete_proof(request):
    proof_id = request.POST.get('id')
    try:
        proof = Proof.objects.get(id=proof_id)
        proof.delete()
        return JsonResponse({'success': True, 'message': 'Proof deleted successfully.'})
    except Proof.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Proof not found.'})

@csrf_protect
@login_required(login_url='admin_login')
def admin_reports(request):
    reports = Proof.objects.values('status').annotate(total=Count('id')).order_by('-total')
    return render(request, 'dashboard/reports.html', {'reports': reports})

@csrf_protect
@login_required(login_url='admin_login')
def admin_analytics(request):
    data = Proof.objects.extra({'day': "date(created_at)"}).values('day').annotate(total=Count('id')).order_by('day')
    return render(request, 'dashboard/analytics.html', {'data': data})


@csrf_protect
@login_required(login_url='admin_login')
def users_list(request):
    users_queryset = User.objects.all().order_by('-id')
    
    # Pagination
    paginator = Paginator(users_queryset, 10)  # 10 users per page
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    # Role counts
    role_counts = users_queryset.values('role').annotate(count=Count('role'))
    total_users = users_queryset.count()
    admin_count = client_count = staff_count = 0
    for rc in role_counts:
        role = rc['role']
        count = rc['count']
        if role == 'super_admin':
            admin_count = count
        elif role == 'client':
            client_count = count
        elif role == 'admin':
            staff_count = count

    form = UserRegistrationForm()

    return render(request, 'users/users_list.html', {
        'users': users,
        'title': 'Users',
        'form': form,
        'total_users': total_users,
        'admin_count': admin_count,
        'client_count': client_count,
        'staff_count': staff_count,
        'role_counts': role_counts,
    })

@csrf_protect
@login_required(login_url='admin_login')
def add_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, f'User {user.username} registered successfully.')
                return redirect('users')
            except Exception as e:
                messages.error(request, f'Error saving user: {str(e)}')
        else:
            # Log form errors to see validation issues
            print("Form errors:", form.errors)  # Check console
            messages.error(request, 'Please correct the form errors.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Register User'})

@csrf_protect
@login_required(login_url='admin_login')
def delete_user(request, pk):
    # Force JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.method == 'POST':
        try:
            # Check if user exists
            user = User.objects.get(id=pk)
            username = user.username
            
            # Prevent deleting yourself
            if user.id == request.user.id:
                return JsonResponse({
                    'success': False,
                    'message': 'You cannot delete your own account!'
                }, status=400)
            
            # Delete the user
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} deleted successfully.',
                'user_id': pk
            })
            
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'User not found.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error deleting user: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False, 
        'message': 'Invalid request method.'
    }, status=405)

@csrf_protect
@login_required(login_url='admin_login')
def edit_user(request, pk): 
    user = get_object_or_404(User, id=pk)

    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'User updated successfully.'})
            messages.success(request, 'User updated successfully.')
            return redirect('users')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return the form HTML with errors
                html = render(request, 'users/user_form_fields.html', {'form': form}).content.decode()
                return JsonResponse({'success': False, 'html': html})
    else:
        form = UserEditForm(instance=user)
    
    # If called via AJAX modal, return only the form fields
    if request.GET.get('modal') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'users/user_form_fields.html', {'form': form})

    return render(request, 'users/user_form.html', {'form': form, 'title': 'Edit User'})

@login_required(login_url='admin_login')
def proof_detail(request, proof_id):
    """Return proof details as JSON"""
    try:
        proof = Proof.objects.select_related('user').get(id=proof_id)
        data = {
            'id': proof.id,
            'user': proof.user.fullname,
            'email': proof.user.email,
            'phone': proof.user.phone_number,
            'status': proof.status,
            'submitted_at': proof.created_at.strftime('%Y-%m-%d %H:%M'),
            'description': proof.description if hasattr(proof, 'description') else ''
        }
        return JsonResponse({'success': True, 'proof': data})
    except Proof.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Proof not found'})



@csrf_protect
@login_required(login_url='admin_login')
def search_users(request):
    """Return filtered users as JSON"""
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    
    users = User.objects.all()
    
    if query:
        users = users.filter(fullname__icontains=query)  # search by name
    if role_filter:
        users = users.filter(role=role_filter)

    data = []
    for u in users:
        data.append({
            'id': u.id,
            'fullname': u.fullname,
            'email': u.email,
            'role': u.role,
            'date_joined': u.date_joined.strftime('%Y-%m-%d'),
        })
    return JsonResponse({'users': data})

@csrf_protect
@login_required(login_url='admin_login')
def search_proofs(request):
    """Return filtered proofs as JSON"""
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    proofs = Proof.objects.select_related('user').all()

    if query:
        proofs = proofs.filter(user__fullname__icontains=query)
    if status_filter:
        proofs = proofs.filter(status=status_filter)

    data = []
    for p in proofs:
        data.append({
            'id': p.id,
            'user': p.user.fullname,
            'status': p.status,
            'submitted_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    return JsonResponse({'proofs': data})

@csrf_protect
def admin_login(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard')

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if (
            user
            and user.is_active
            and user.is_staff
            and user.role in ['super_admin']
        ):
            login(request, user)
            request.session.cycle_key()
            return redirect('admin_dashboard')

        messages.error(request, "Invalid credentials or access denied.")

    return render(request, 'dashboard/login.html')


@csrf_protect
@login_required(login_url='admin_login')
def company_info(request):
    data = CompanyInfo.objects.all()
    return render(request, 'dashboard/company_info.html', {'companies': data})

@csrf_protect
@login_required(login_url='admin_login')
def agents_list(request):
    data = Agent.objects.all()
    return render(request, 'dashboard/agents.html', {'agents': data})

#  List Agents 
@csrf_protect
@login_required(login_url='admin_login')
def agents_list(request):
    agents = Agent.objects.all()
    return render(request, 'agents/agents.html', {'agents': agents, 'page_title': 'Agents'})

#  Add Agent 
@csrf_protect
@login_required(login_url='admin_login')
def add_agent(request):
    form = AgentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Company agentagentline added successfully.')
        return redirect('agents')
    return render(request, 'agents/agent_form.html', {'form': form, 'title': 'Add Agent'})

#  Edit Agent 
@csrf_protect
@login_required(login_url='admin_login')
def edit_agent(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    form = AgentForm(request.POST or None, request.FILES or None, instance=agent)
    if form.is_valid():
        form.save()
        messages.success(request, 'Company agentagentline updated successfully.')
        return redirect('agents')
    return render(request, 'agents/agent_form.html', {'form': form, 'title': 'Edit Agent'})

#  Delete Agent 
@csrf_protect
@login_required(login_url='admin_login')
def delete_agent(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    if request.method == 'POST':
        agent.delete()
        messages.success(request, 'Company agentline deleted successfully.')
        return redirect('agents')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': agent,
        'title': 'Delete Agent',
        'cancel_url': '/agents/'
    })

@csrf_protect
@login_required(login_url='admin_login')
def company_info(request):
 
    companies = CompanyInfo.objects.all()
    context = {
        'companies': companies,
        'page_title': 'Company Information',
    }
    return render(request, 'company_info/company_info.html', context)

@csrf_protect
@login_required(login_url='admin_login')
def add_company(request):
    if request.method == "POST":
        form = CompanyInfoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company info added successfully.')
            return redirect('company_info')
    else:
        form = CompanyInfoForm()

    return render(request, 'company_info/company_form.html', {
        'form': form,
        'title': 'Add Company'
    })

@csrf_protect
@login_required(login_url='admin_login')
def edit_company(request, pk):
    company = get_object_or_404(CompanyInfo, pk=pk)
    if request.method == 'POST':
        form = CompanyInfoForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company info updated successfully.')
            # Redirect back to the list after editing
            return redirect('company_info')
    else:
        form = CompanyInfoForm(instance=company)

    return render(request, 'company_info/company_form.html', {
        'form': form,
        'title': 'Edit Company'
    })

@csrf_protect
@login_required(login_url='admin_login')
def delete_company(request, pk):
    company = get_object_or_404(CompanyInfo, pk=pk)
    if request.method == 'POST':
        company.delete()
        messages.success(request, 'Company info deleted successfully.')
        return redirect('company_info')  # Back to list after deletion

    # GET request → show confirmation page
    return render(request, 'company_info/confirm_delete.html', {
        'object': company,
        'title': 'Delete Company',
        'cancel_url': '/company-info/'  # optional: cancel button URL
    })

@login_required(login_url='admin_login')
def profile_view(request):
    return render(request, 'profile/profile.html', {'user': request.user})

@login_required(login_url='admin_login')
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'profile/edit_profile.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('admin_login')


def transaction_receipt(request, id):
    transaction = Transaction.objects.select_related('proof').get(id=id)
    return render(request, 'transactions/receipt.html', {'transaction': transaction})


def transactions(request):
    #  Base queryset 
    transactions_qs = Transaction.objects.select_related(
        'confirmed_by', 'charge_rule', 'charge_rule__country', 'proof'
      ).all().order_by('-confirmed_at')

    #  Base currency for reporting 
    base_currency = Currency.objects.filter(code='UGX').first()

    if not base_currency:
        base_currency = Currency.objects.first()

    #  Calculate global stats dynamically for all currencies 
    total_amount_base = Decimal('0.00')
    total_charge_base = Decimal('0.00')

    # Compute base currency equivalent per transaction
    tx_base_amounts = []
    for tx in transactions_qs:
        try:
            base_currency_obj = Currency.objects.get(code=tx.currency)
            rate_obj = ExchangeRate.objects.filter(
                base_currency=base_currency_obj,
                target_currency=base_currency,
                valid_from__lte=timezone.now()
            ).filter(Q(valid_to__gte=timezone.now()) | Q(valid_to__isnull=True)
            ).latest('valid_from')
            rate = rate_obj.rate
        except (Currency.DoesNotExist, ExchangeRate.DoesNotExist):
            rate = Decimal('1.00')

        amount_base = tx.amount * rate
        charge_base = tx.charge_amount * rate
        total_amount_base += amount_base
        total_charge_base += charge_base

        tx_base_amounts.append({
            'tx': tx,
            'amount_base': amount_base,
            'charge_base': charge_base
        })

        total_amount_base += tx.amount * rate
        total_charge_base += tx.charge_amount * rate

    total_net_base = total_amount_base - total_charge_base

    #  Filter form values 
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    sender = request.GET.get('sender', '').strip()
    receiver = request.GET.get('receiver', '').strip()
    currency_code = request.GET.get('currency', '').strip()
    confirmed_by = request.GET.get('confirmed_by', '').strip()
    status_filter = request.GET.get('status', '').strip()

    filters = Q()
    if date_from:
        filters &= Q(confirmed_at__date__gte=date_from)
    if date_to:
        filters &= Q(confirmed_at__date__lte=date_to)
    if sender:
        filters &= Q(sender_name__icontains=sender)
    if receiver:
        filters &= Q(receiver_name__icontains=receiver)
    if currency_code:
        filters &= Q(currency__code__iexact=currency_code)
    if confirmed_by:
        filters &= Q(confirmed_by__fullname__icontains=confirmed_by)
    if status_filter:
        if status_filter == 'completed':
            filters &= Q(is_completed=True)
        elif status_filter == 'pending':
            filters &= Q(is_completed=False)

    filtered_qs = transactions_qs.filter(filters)

    #  Filtered totals in base currency 
    filtered_total_amount_base = Decimal('0.00')
    filtered_total_charge_base = Decimal('0.00')
    for tx in filtered_qs:
        rate_obj = ExchangeRate.objects.filter(
        base_currency__code=tx.currency,
        target_currency__code=base_currency
        ).order_by('-created_at').first()
        rate = Decimal(str(rate_obj.rate)) if rate_obj else Decimal('1.00')
        filtered_total_amount_base += tx.amount * rate
        filtered_total_charge_base += tx.charge_amount * rate
    filtered_total_net_base = filtered_total_amount_base - filtered_total_charge_base

    #  Aggregate filtered stats by currency 
    currency_stats = filtered_qs.values('currency').annotate(
        count=Count('id'),
        total_amount=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField()),
        total_charge=Coalesce(Sum('charge_amount'), Decimal('0.00'), output_field=DecimalField()),
        total_net=Coalesce(Sum(F('amount') - F('charge_amount')), Decimal('0.00'), output_field=DecimalField())
    ).order_by('-total_amount')

    #  Top staff 
    top_staff = filtered_qs.values(
        'confirmed_by__id',
        'confirmed_by__fullname',
        'confirmed_by__email'
    ).annotate(
        transaction_count=Count('id'),
        total_amount=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField()),
        total_charge=Coalesce(Sum('charge_amount'), Decimal('0.00'), output_field=DecimalField())
    ).order_by('-total_amount')[:5]

    # Top currencies
    top_currencies = filtered_qs.values('currency').annotate(
        transaction_count=Count('id'),
        total_amount=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    ).order_by('-total_amount')[:5]

    #  Pagination 
    paginator = Paginator(filtered_qs, 10)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    #  Download options 
    download_format = request.GET.get('download_format')
    if download_format == 'excel':
        return download_transactions_excel(filtered_qs)
    elif download_format == 'pdf':
        return download_transactions_pdf(filtered_qs)

    #  AJAX Live Search 
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'transactions/transactions_table.html', {
            'transactions': page_obj,
            'page_obj': page_obj
        })

    #  Render page 
    context = {
        'transactions': page_obj,
        'page_obj': page_obj,
        'currency_stats': currency_stats,
        'top_staff': top_staff,
        'top_currencies': top_currencies,
        'total_amount_base': total_amount_base,
        'total_charge_base': total_charge_base,
        'total_net_base': total_net_base,
        'filtered_total_amount_base': filtered_total_amount_base,
        'filtered_total_charge_base': filtered_total_charge_base,
        'filtered_total_net_base': filtered_total_net_base,
        # Form persistence
        'date_from': date_from,
        'date_to': date_to,
        'sender': sender,
        'receiver': receiver,
        'currency': currency_code,
        'confirmed_by': confirmed_by,
        'status_filter': status_filter,
        'title': 'Transactions Management',
    }

    return render(request, 'transactions/transactions.html', context)

@login_required(login_url='admin_login')
def delete_transaction(request):
    transaction_id = request.POST.get('id')
    try:
        txn = Transaction.objects.get(id=transaction_id)
        txn.delete()
        return JsonResponse({'success': True, 'message': 'Transaction deleted successfully.'})
    except Transaction.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Transaction not found.'})
#  Excel download 
def download_transactions_excel(transactions):
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"
    headers = ['Date','Ref No','Sender','Receiver','Receiver Contact','Staff','Country','Total','Charge','Client Receives','Currency']
    ws.append(headers)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    for t in transactions:
        ws.append([
            t.confirmed_at.strftime('%Y-%m-%d %H:%M'),
            t.transaction_reference,
            t.sender_name,
            t.receiver_name,
            t.receiver_contact or '-',
            t.confirmed_by.fullname if t.confirmed_by else 'System',
            t.charge_rule.country.name if t.charge_rule and t.charge_rule.country else '-',
            str(t.amount),
            str(t.charge_amount),
            str(t.net_amount),
            t.currency,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=transactions.xlsx'
    wb.save(response)
    return response

#  PDF download 
def download_transactions_pdf(transactions):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    styles = getSampleStyleSheet()
    styleN = styles['Normal']


    headers = ['Date','Ref No','Sender','Receiver','Receiver Contact','Staff','Country','Total','Charge','Client Receives','Currency']
    data = [headers]
    for t in transactions:
        data.append([
            Paragraph(t.confirmed_at.strftime('%Y-%m-%d %H:%M'), styleN),
            Paragraph(t.transaction_reference, styleN),
            Paragraph(t.sender_name, styleN),
            Paragraph(t.receiver_name, styleN),
            Paragraph(t.receiver_contact or '-', styleN),
            Paragraph(t.confirmed_by.fullname if t.confirmed_by else 'System', styleN),
            Paragraph(t.charge_rule.country.name if t.charge_rule and t.charge_rule.country else '-', styleN),
            Paragraph(str(t.amount), styleN),
            Paragraph(str(t.charge_amount), styleN),
            Paragraph(str(t.net_amount), styleN),
            Paragraph(t.currency, styleN),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),10),
        ('GRID',(0,0),(-1,-1),0.5,colors.black),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),3),
        ('RIGHTPADDING',(0,0),(-1,-1),3)
    ]))
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(
        buffer,
        content_type='application/pdf',
        headers={'Content-Disposition':'attachment; filename="transactions.pdf"'}
    )


def exchange_rate_list(request):
    """List all exchange rates with optional reverse FX calculation."""

    # Use the correct fields: base_currency and target_currency
    rates = ExchangeRate.objects.select_related('base_currency', 'target_currency').all().order_by('base_currency__code')

    # Compute reverse FX (for display purposes)
    for rate in rates:
        if rate.target_currency.code != "UGX":
            try:
                rate.reverse_fx = round(1 / float(rate.rate), 6)
            except ZeroDivisionError:
                rate.reverse_fx = None
        else:
            rate.reverse_fx = None

    context = {
        "rates": rates,
        "title": "Exchange Rates List"
    }
    return render(request, "exchange_rate/exchange_rate_list.html", context)


def exchange_rate_edit(request, id):
    """Edit an existing exchange rate."""
    rate_obj = get_object_or_404(ExchangeRate, id=id)
    currencies = Currency.objects.all()
    countries = Country.objects.all()

    if request.method == "POST":
        currency_id = request.POST.get("currency")
        country_id = request.POST.get("country")
        rate_to_ugx = request.POST.get("rate")

        # Validation
        if not currency_id or not rate_to_ugx:
            messages.error(request, "Currency and rate are required.")
            return redirect("exchange_rate_edit", id=id)

        try:
            currency = Currency.objects.get(id=int(currency_id))
            country = Country.objects.get(id=int(country_id)) if country_id else None
            rate_to_ugx = float(rate_to_ugx)
        except (ValueError, Currency.DoesNotExist, Country.DoesNotExist):
            messages.error(request, "Invalid input.")
            return redirect("exchange_rate_edit", id=id)

        # Update
        rate_obj.currency = currency
        rate_obj.country = country
        rate_obj.rate_to_ugx = rate_to_ugx
        rate_obj.save()

        messages.success(request, "Exchange rate updated successfully.")
        return redirect("exchange_rate_list")

    context = {
        "action": "Edit",
        "rate": rate_obj,
        "currencies": currencies,
        "countries": countries,
        "title": "Edit Exchange Rate"
    }
    return render(request, "exchange_rate/exchange_rate_form.html", context)


def exchange_rate_delete(request, id):
    """Delete an exchange rate."""
    rate_obj = get_object_or_404(ExchangeRate, id=id)
    rate_obj.delete()
    messages.success(request, "Exchange rate deleted successfully.")
    return redirect("exchange_rate_list")
# List
@csrf_protect
@login_required(login_url='admin_login')
def proof_steps_list(request):
    steps = UploadProofStep.objects.all()
    return render(request, 'upload_guide/steps_list.html', {'steps': steps, 'title': 'Upload Proof Steps'})

# Add
@csrf_protect
@login_required(login_url='admin_login')
def add_proof_step(request):
    if request.method == "POST":
        form = UploadProofStepForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Step added successfully")
            return redirect('proof_steps_list')
    else:
        form = UploadProofStepForm()

    return render(request, 'upload_guide/step_form.html', {'form': form, 'title': 'Add Step'})

# Edit
@csrf_protect
@login_required(login_url='admin_login')
def edit_proof_step(request, pk):
    step = get_object_or_404(UploadProofStep, pk=pk)
    if request.method == 'POST':
        form = UploadProofStepForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            messages.success(request, "Step updated successfully")
            return redirect('proof_steps_list')
    else:
        form = UploadProofStepForm(instance=step)

    return render(request, 'upload_guide/step_form.html', {'form': form, 'title': 'Edit Step'})

# Delete
@csrf_protect
@login_required(login_url='admin_login')
def delete_proof_step(request, pk):
    step = get_object_or_404(UploadProofStep, pk=pk)
    if request.method == 'POST':
        step.delete()
        messages.success(request, "Step deleted successfully")
        return redirect('proof_steps_list')

    return render(request, 'upload_guide/confirm_delete.html', {
        'object': step,
        'title': 'Delete Step',
        'cancel_url': '/upload-proof-steps/'  # Adjust to list URL
    })

@login_required(login_url='admin_login')
def add_whatsapp_contact(request):
    if request.method == 'POST':
        form = WhatsAppContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'WhatsApp contact added successfully.')
            return redirect('contacts_list')  # Correct name
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = WhatsAppContactForm()

    context = {
        'form': form,
        'title': 'Add WhatsApp Contact',
    }
    return render(request, 'contacts/add_contact.html', context)


@login_required(login_url='admin_login')
def contacts_list(request):
    contacts = WhatsAppContact.objects.all().order_by('-id')

    # Handle Add Contact
    add_form = WhatsAppContactForm(prefix='add')
    if request.method == 'POST' and 'add-submit' in request.POST:
        add_form = WhatsAppContactForm(request.POST, prefix='add')
        if add_form.is_valid():
            add_form.save()
            messages.success(request, "Contact added successfully.")
            return redirect('contacts_list')

    # Handle Edit Contact (direct update)
    edit_contact_id = request.POST.get('edit-id')
    if edit_contact_id:
        contact = WhatsAppContact.objects.get(id=edit_contact_id)
        name = request.POST.get('name')
        phone_number = request.POST.get('phone_number')
        if name and phone_number:
            contact.name = name
            contact.phone_number = phone_number
            contact.save()
            messages.success(request, "Contact updated successfully.")
            return redirect('contacts_list')

    # Handle Delete Contact
    delete_contact_id = request.POST.get('delete-id')
    if delete_contact_id:
        contact = WhatsAppContact.objects.get(id=delete_contact_id)
        contact.delete()
        messages.success(request, "Contact deleted successfully.")
        return redirect('contacts_list')

    return render(request, 'contacts/contacts_list.html', {
        'contacts': contacts,
        'add_form': add_form,
        'title': 'WhatsApp Contacts'
    })



@login_required(login_url='admin_login')
def edit_whatsapp_contact(request, contact_id):
    contact = WhatsAppContact.objects.get(id=contact_id)

    if request.method == 'POST':
        form = WhatsAppContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contact updated successfully.')
            return redirect('contacts_list')
    else:
        form = WhatsAppContactForm(instance=contact)

    return render(request, 'contacts/edit_contact.html', {'form': form, 'contact': contact, 'title': 'Edit Contact'})


@login_required(login_url='admin_login')
def delete_whatsapp_contact(request, contact_id):
    contact = WhatsAppContact.objects.get(id=contact_id)
    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'Contact deleted successfully.')
        return redirect('contacts_list')
    return render(request, 'contacts/delete_contact.html', {'contact': contact, 'title': 'Delete Contact'})
# List all announcements
def announcement_list(request):
    announcements = Announcement.objects.all()
    return render(request, 'announcements/announcement_list.html', {'announcements': announcements})

# Create new announcement
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement created successfully.')
            return redirect('announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_form.html', {'form': form, 'title': 'Add Announcement'})

# Update announcement
def announcement_update(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement updated successfully.')
            return redirect('announcement_list')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'announcements/announcement_form.html', {'form': form, 'title': 'Edit Announcement'})

# Delete announcement
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        if announcement.image:
            try:
                import os
                os.remove(announcement.image.path)
            except:
                pass
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully.')
        return redirect('announcement_list')
    return render(request, 'announcements/announcement_confirm_delete.html', {'announcement': announcement})
