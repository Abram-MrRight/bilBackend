from pyexpat.errors import messages
import uuid
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from api.models import Agent, ChargeRule, CompanyInfo, Country, Currency, ExchangeRate, Proof, Transaction, UploadProofStep, User, WhatsAppContact
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
from dashboard.forms import AgentForm, ChargeRuleForm, CompanyInfoForm, CountryForm, CurrencyForm, ProfileForm, UploadProofStepForm, UserDetailForm, UserEditForm, UserRegistrationForm, WhatsAppContactForm
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

from django.core.paginator import Paginator

from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, F, Q
from decimal import Decimal
from collections import defaultdict
from django.conf import settings 

def format_money(amount, decimals=4):
    """Format Decimal or float to string with commas and fixed decimals."""
    amount = Decimal(amount).quantize(Decimal(f"1.{'0'*decimals}"), rounding=ROUND_HALF_UP)
    return f"{amount:,.{decimals}f}"
def analytics_dashboard(request):
    # Get base currency from settings or use UGX as default
    base_currency = getattr(settings, 'BASE_CURRENCY', 'UGX')
    
    # Get date range filter
    date_filter = request.GET.get('period', 'all')
    now = timezone.now()
    
    if date_filter == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'week':
        start_date = now - timedelta(days=7)
    elif date_filter == 'month':
        start_date = now - timedelta(days=30)
    elif date_filter == 'year':
        start_date = now - timedelta(days=365)
    else:
        start_date = None
    
    # Filter transactions based on date range
    transactions = Transaction.objects.all()
    if start_date:
        transactions = transactions.filter(confirmed_at__gte=start_date)
    
    # Get current USD to UGX exchange rate
    try:
        usd_rate_obj = ExchangeRate.objects.filter(currency='USD').latest('updated_at')
        exchange_rate = Decimal(str(usd_rate_obj.rate_to_ugx))  # Ensure Decimal
    except ExchangeRate.DoesNotExist:
        exchange_rate = Decimal('3800')  # Default fallback
    
    # ===== USD TRANSACTIONS =====
    usd_transactions = transactions.filter(original_currency='USD')
    usd_count = usd_transactions.count()
    
    # USD amounts (in USD) - convert to Decimal
    usd_total_amount = Decimal(str(usd_transactions.aggregate(
        total=Sum('original_amount')
    )['total'] or Decimal('0')))
    
    usd_total_charge = Decimal(str(usd_transactions.aggregate(
        total=Sum('charge_amount')
    )['total'] or Decimal('0')))
    
    usd_total_net = usd_total_amount - usd_total_charge
    
    # Convert USD to UGX
    usd_amount_ugx = usd_total_amount * exchange_rate
    usd_charge_ugx = usd_total_charge * exchange_rate
    usd_net_ugx = usd_total_net * exchange_rate
    
    # USD averages
    usd_stats_agg = usd_transactions.aggregate(
        avg_amount=Avg('original_amount'),
        avg_charge=Avg('charge_amount')
    )
    usd_avg_amount = Decimal(str(usd_stats_agg['avg_amount'] or Decimal('0')))
    usd_avg_charge = Decimal(str(usd_stats_agg['avg_charge'] or Decimal('0')))
    
    # ===== UGX TRANSACTIONS =====
    ugx_transactions = transactions.filter(original_currency='UGX')
    ugx_count = ugx_transactions.count()
    
    # UGX amounts (already in UGX) - convert to Decimal
    ugx_total_amount = Decimal(str(ugx_transactions.aggregate(
        total=Sum('original_amount')
    )['total'] or Decimal('0')))
    
    ugx_total_charge = Decimal(str(ugx_transactions.aggregate(
        total=Sum('charge_amount')
    )['total'] or Decimal('0')))
    
    ugx_total_net = ugx_total_amount - ugx_total_charge
    
    # UGX averages
    ugx_stats_agg = ugx_transactions.aggregate(
        avg_amount=Avg('original_amount'),
        avg_charge=Avg('charge_amount')
    )
    ugx_avg_amount = Decimal(str(ugx_stats_agg['avg_amount'] or Decimal('0')))
    ugx_avg_charge = Decimal(str(ugx_stats_agg['avg_charge'] or Decimal('0')))
    
    # ===== TOTALS IN UGX =====
    total_amount_ugx = usd_amount_ugx + ugx_total_amount
    total_charges_ugx = usd_charge_ugx + ugx_total_charge
    total_net = total_amount_ugx - total_charges_ugx
    
    # ===== CHARGE RATES =====
    # USD charge rate - ensure both are Decimal
    usd_charge_rate = Decimal('0')
    if usd_total_amount > Decimal('0'):
        usd_charge_rate = (usd_total_charge / usd_total_amount) * Decimal('100')
    
    # UGX charge rate - ensure both are Decimal
    ugx_charge_rate = Decimal('0')
    if ugx_total_amount > Decimal('0'):
        ugx_charge_rate = (ugx_total_charge / ugx_total_amount) * Decimal('100')
    
    # Overall charge rate
    overall_charge_rate = Decimal('0')
    if total_amount_ugx > Decimal('0'):
        overall_charge_rate = (total_charges_ugx / total_amount_ugx) * Decimal('100')
    
    # ===== CURRENCY STATS FOR DYNAMIC DISPLAY =====
    currency_stats = []
    
    # Add USD stats
    if usd_count > 0:
        currency_stats.append({
            'currency': 'USD',
            'country_name': 'United States',
            'currency_name': 'US Dollar',
            'color': '#0052B4',
            'symbol': '$',
            'count': usd_count,
            'total_amount': float(usd_total_amount),
            'total_charge': float(usd_total_charge),
            'total_net': float(usd_total_net),
            'avg_amount': float(usd_avg_amount),
            'avg_charge': float(usd_avg_charge),
            'exchange_rate': float(exchange_rate),
            'base_amount': float(usd_amount_ugx),
            'base_charge': float(usd_charge_ugx),
            'charge_rate': float(usd_charge_rate),
        })
    
    # Add UGX stats
    if ugx_count > 0:
        currency_stats.append({
            'currency': 'UGX',
            'country_name': 'Uganda',
            'currency_name': 'Ugandan Shilling',
            'color': '#FCDC04',
            'symbol': 'UGX',
            'count': ugx_count,
            'total_amount': float(ugx_total_amount),
            'total_charge': float(ugx_total_charge),
            'total_net': float(ugx_total_net),
            'avg_amount': float(ugx_avg_amount),
            'avg_charge': float(ugx_avg_charge),
            'exchange_rate': 1.0,  # UGX to UGX rate is 1
            'base_amount': float(ugx_total_amount),
            'base_charge': float(ugx_total_charge),
            'charge_rate': float(ugx_charge_rate),
        })
    
    # Calculate percentages for currency contribution
    for stat in currency_stats:
        if total_amount_ugx > Decimal('0'):
            stat['percentage'] = float((Decimal(str(stat['base_amount'])) / total_amount_ugx) * Decimal('100'))
        else:
            stat['percentage'] = 0.0
    
    # ===== NEW VARIABLES FOR THE NEW TEMPLATE =====
    # Calculate base currency totals (using UGX as base)
    total_amount_base = total_amount_ugx
    total_charges_base = total_charges_ugx
    total_net_base = total_net
    
    # Calculate net to total ratio
    net_to_total_ratio = Decimal('0')
    if total_amount_base > Decimal('0'):
        net_to_total_ratio = (total_net_base / total_amount_base) * Decimal('100')
    
    # Get top performing staff
    top_staff = transactions.values(
        'confirmed_by__fullname',
        'confirmed_by__email'
    ).annotate(
        transaction_count=Count('id'),
        total_amount=Sum('ugx_equivalent'),
        total_charge=Sum('charge_amount'),
        avg_amount=Avg('ugx_equivalent')
    ).order_by('-total_amount')[:5]
    
    # Get transaction trend (last 7 days)
    trend_data = []
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        day_transactions = transactions.filter(confirmed_at__range=(day_start, day_end))
        day_count = day_transactions.count()
        day_amount = day_transactions.aggregate(total=Sum('ugx_equivalent'))['total'] or Decimal('0')
        
        trend_data.append({
            'date': date.strftime('%a'),
            'count': day_count,
            'amount': float(day_amount),
        })
    
    # Get active countries
    active_countries = Country.objects.filter(
        id__in=transactions.exclude(country__isnull=True).values_list('country', flat=True).distinct()
    )
    
    # Calculate average transaction value and charge
    total_transactions = transactions.count()
    
    # Get averages as Decimal
    avg_amount_agg = transactions.aggregate(avg=Avg('ugx_equivalent'))
    avg_charge_agg = transactions.aggregate(avg=Avg('charge_amount'))
    
    avg_amount = Decimal(str(avg_amount_agg['avg'] or Decimal('0')))
    avg_charge = Decimal(str(avg_charge_agg['avg'] or Decimal('0')))
    
    context = {
        # NEW VARIABLES FOR THE NEW TEMPLATE
        'total_amount_base': total_amount_base,
        'total_charges_base': total_charges_base,
        'total_net_base': total_net_base,
        'overall_charge_rate': overall_charge_rate,
        'net_to_total_ratio': net_to_total_ratio,
        'base_currency': base_currency,
        
        # Basic counts
        'total_transactions': total_transactions,
        'usd_count': usd_count,
        'ugx_count': ugx_count,
        
        # USD amounts (in USD)
        'usd_total_amount': usd_total_amount,
        'usd_total_charge': usd_total_charge,
        'usd_total_net': usd_total_net,
        
        # UGX amounts (in UGX)
        'ugx_total_amount': ugx_total_amount,
        'ugx_total_charge': ugx_total_charge,
        'ugx_total_net': ugx_total_net,
        
        # Exchange rate and conversions
        'exchange_rate': exchange_rate,
        'usd_amount_ugx': usd_amount_ugx,
        'usd_charge_ugx': usd_charge_ugx,
        'usd_net_ugx': usd_net_ugx,
        
        # Totals in UGX
        'total_amount_ugx': total_amount_ugx,
        'total_charges_ugx': total_charges_ugx,
        'total_net': total_net,
        
        # Statistics
        'usd_stats': {
            'avg_amount': usd_avg_amount,
            'avg_charge': usd_avg_charge,
        },
        'ugx_stats': {
            'avg_amount': ugx_avg_amount,
            'avg_charge': ugx_avg_charge,
        },
        
        # Charge rates
        'charge_rate': overall_charge_rate,
        'usd_charge_rate': usd_charge_rate,
        'ugx_charge_rate': ugx_charge_rate,
        
        # For dynamic display
        'currency_stats': currency_stats,
        'currency_count': len(currency_stats),
        'country_count': active_countries.count(),
        'staff_count': transactions.exclude(confirmed_by__isnull=True).values('confirmed_by').distinct().count(),
        
        # Additional metrics for template
        'top_staff': top_staff,
        'trend_data': json.dumps(trend_data),
        'active_countries': active_countries,
        'period': date_filter,
        'exchange_rates': ExchangeRate.objects.all().order_by('currency'),
        'all_currencies': Currency.objects.all(),
        'last_update': now,
        
        # For summary stats
        'avg_amount': avg_amount,
        'avg_charge': avg_charge,
        'total_amount': total_amount_ugx,  # For charge rate calculation in template
        'total_charge': total_charges_ugx,  # For charge rate calculation in template
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


@login_required
def country_list(request):
    countries = Country.objects.all()
    return render(request, 'country/list.html', {'countries': countries})

@login_required
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

@login_required

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

@login_required

def delete_country(request, pk):
    country = get_object_or_404(Country, pk=pk)
    country.delete()
    messages.success(request, 'Country deleted successfully')
    return redirect('country_list')

#  CURRENCY VIEWS 
@login_required

def currency_list(request):
    currencies = Currency.objects.select_related('country').all()
    return render(request, 'currency/list.html', {'currencies': currencies})

@login_required

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

@login_required

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

@login_required

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
@login_required

def charge_rule_list(request):
    rules = ChargeRule.objects.select_related('country', 'currency').all()
    return render(request, 'charge_rule/list.html', {'rules': rules})

@login_required

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

@login_required

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

@login_required

def delete_charge_rule(request, pk):
    charge = get_object_or_404(ChargeRule, pk=pk)
    charge.delete()
    messages.success(request, 'Charge rule deleted successfully')
    return redirect('charge_rule_list')

def exchange_rate_add(request):
    countries = Country.objects.all()
    currencies = Currency.objects.all()  # or filter dynamically via AJAX

    if request.method == "POST":
        country_id = request.POST.get("country")
        currency_id = request.POST.get("currency")
        rate_to_ugx = request.POST.get("rate_to_ugx")

        # Validation
        if not country_id or not currency_id or not rate_to_ugx:
            messages.error(request, "All fields are required.")
            return redirect("exchange_rate_add")

        try:
            country = Country.objects.get(id=int(country_id))
            currency = Currency.objects.get(id=int(currency_id))
            rate_to_ugx = float(rate_to_ugx)
        except (ValueError, Country.DoesNotExist, Currency.DoesNotExist):
            messages.error(request, "Invalid input data.")
            return redirect("exchange_rate_add")

        # Prevent duplicates
        if ExchangeRate.objects.filter(country=country, currency=currency).exists():
            messages.error(request, "Exchange rate for this country/currency already exists.")
            return redirect("exchange_rate_add")

        # Save
        ExchangeRate.objects.create(
            country=country,
            currency=currency,
            rate_to_ugx=rate_to_ugx
        )
        messages.success(request, "Exchange rate added successfully.")
        return redirect("exchange_rate_list")

    return render(request, "exchange_rate/exchange_rate_form.html", {
        "countries": countries,
        "currencies": currencies,
        "action": "Add"
    })


@csrf_protect
@login_required
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
        .annotate(proofs_count=Count('proofs'))
        .order_by('-proofs_count')[:5]
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


# @csrf_protect
# @login_required
# def admin_proofs(request):
#     proofs_list = Proof.objects.select_related('user').order_by('-created_at')

#     paginator = Paginator(proofs_list, 10)  
#     page_number = request.GET.get("page")
#     page_obj = paginator.get_page(page_number)

#     return render(request, 'dashboard/proofs.html', {
#         'page_obj': page_obj,
#         'proofs': page_obj.object_list, 
#     })
@csrf_protect
@login_required
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

@login_required
def delete_proof(request):
    proof_id = request.POST.get('id')
    try:
        proof = Proof.objects.get(id=proof_id)
        proof.delete()
        return JsonResponse({'success': True, 'message': 'Proof deleted successfully.'})
    except Proof.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Proof not found.'})

@csrf_protect
@login_required
def admin_reports(request):
    reports = Proof.objects.values('status').annotate(total=Count('id')).order_by('-total')
    return render(request, 'dashboard/reports.html', {'reports': reports})

@csrf_protect
@login_required
def admin_analytics(request):
    data = Proof.objects.extra({'day': "date(created_at)"}).values('day').annotate(total=Count('id')).order_by('day')
    return render(request, 'dashboard/analytics.html', {'data': data})


@csrf_protect
@login_required
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
@login_required
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
@login_required
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
@login_required
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

@csrf_protect
@login_required
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
@login_required
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
@login_required
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
def web_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('admin_dashboard')
        return render(request, 'dashboard/login.html', {'error': 'Invalid credentials'})
    return render(request, 'dashboard/login.html')

@csrf_protect
@login_required
def company_info(request):
    data = CompanyInfo.objects.all()
    return render(request, 'dashboard/company_info.html', {'companies': data})

@csrf_protect
@login_required
def agents_list(request):
    data = Agent.objects.all()
    return render(request, 'dashboard/agents.html', {'agents': data})

# --- List Agents ---
@csrf_protect
@login_required
def agents_list(request):
    agents = Agent.objects.all()
    return render(request, 'agents/agents.html', {'agents': agents, 'page_title': 'Agents'})

# --- Add Agent ---
@csrf_protect
@login_required
def add_agent(request):
    form = AgentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Company agentagentline added successfully.')
        return redirect('agents')
    return render(request, 'agents/agent_form.html', {'form': form, 'title': 'Add Agent'})

# --- Edit Agent ---
@csrf_protect
@login_required
def edit_agent(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    form = AgentForm(request.POST or None, request.FILES or None, instance=agent)
    if form.is_valid():
        form.save()
        messages.success(request, 'Company agentagentline updated successfully.')
        return redirect('agents')
    return render(request, 'agents/agent_form.html', {'form': form, 'title': 'Edit Agent'})

# --- Delete Agent ---
@csrf_protect
@login_required
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
@login_required
def company_info(request):
 
    companies = CompanyInfo.objects.all()
    context = {
        'companies': companies,
        'page_title': 'Company Information',
    }
    return render(request, 'company_info/company_info.html', context)

@csrf_protect
@login_required
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
@login_required
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
@login_required
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

@login_required
def profile_view(request):
    return render(request, 'profile/profile.html', {'user': request.user})

@login_required
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
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


def transaction_receipt(request, id):
    transaction = Transaction.objects.select_related('proof').get(id=id)
    return render(request, 'transactions/receipt.html', {'transaction': transaction})


def transactions(request):
    # Base queryset with all related data
    transactions_qs = Transaction.objects.select_related(
        'confirmed_by',
        'charge_rule',
        'charge_rule__country',
        'proof'
    ).all().order_by('-confirmed_at')

    #CALCULATE GLOBAL STATISTICS BY CURRENCY (before filtering)
    # USD transactions
    usd_transactions = transactions_qs.filter(currency='USD')
    ugx_transactions = transactions_qs.filter(currency='UGX')
    
    # USD Statistics
    usd_stats = usd_transactions.aggregate(
        total_count=Count('id'),
        total_amount=Coalesce(Sum('amount'), 0.0, output_field=DecimalField()),
        total_charge=Coalesce(Sum('charge_amount'), 0.0, output_field=DecimalField()),
        total_net=Coalesce(Sum('net_amount'), 0.0, output_field=DecimalField()),
        avg_amount=Coalesce(Avg('amount'), 0.0, output_field=DecimalField()),
        avg_charge=Coalesce(Avg('charge_amount'), 0.0, output_field=DecimalField()),
    )
    
    # UGX Statistics
    ugx_stats = ugx_transactions.aggregate(
        total_count=Count('id'),
        total_amount=Coalesce(Sum('amount'), 0.0, output_field=DecimalField()),
        total_charge=Coalesce(Sum('charge_amount'), 0.0, output_field=DecimalField()),
        total_net=Coalesce(Sum('net_amount'), 0.0, output_field=DecimalField()),
        avg_amount=Coalesce(Avg('amount'), 0.0, output_field=DecimalField()),
        avg_charge=Coalesce(Avg('charge_amount'), 0.0, output_field=DecimalField()),
    )
    
    # Combined statistics (for backward compatibility)
    global_stats = transactions_qs.aggregate(
        total_count=Count('id'),
        total_amount=Coalesce(Sum('amount'), 0.0, output_field=DecimalField()),
        total_charge=Coalesce(Sum('charge_amount'), 0.0, output_field=DecimalField()),
        total_net=Coalesce(Sum('net_amount'), 0.0, output_field=DecimalField()),
        avg_amount=Coalesce(Avg('amount'), 0.0, output_field=DecimalField()),
        avg_charge=Coalesce(Avg('charge_amount'), 0.0, output_field=DecimalField()),
        staff_count=Count('confirmed_by', distinct=True),
        currency_count=Count('currency', distinct=True),
        country_count=Count('charge_rule__country', distinct=True),
    )
    
    # Assuming you have an ExchangeRate model with fields: currency, rate_to_ugx, updated_at
    try:
        exchange_rate = ExchangeRate.objects.filter(currency='USD').first()
        usd_to_ugx_rate = exchange_rate.rate_to_ugx if exchange_rate else Decimal('3800.00')
    except:
        usd_to_ugx_rate = Decimal('3800.00')  # Default rate

    # Calculate UGX equivalent for USD transactions
    usd_amount_ugx = (usd_stats['total_amount'] or Decimal('0.00')) * usd_to_ugx_rate
    usd_charge_ugx = (usd_stats['total_charge'] or Decimal('0.00')) * usd_to_ugx_rate
    
    # Calculate totals in UGX
    total_amount_ugx = (ugx_stats['total_amount'] or Decimal('0.00')) + usd_amount_ugx
    total_charges_ugx = (ugx_stats['total_charge'] or Decimal('0.00')) + usd_charge_ugx

    # Calculate by currency (for stats display)
    currency_stats = transactions_qs.values('currency').annotate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_charge=Sum('charge_amount'),
        total_net=Sum('net_amount')
    ).order_by('-total_amount')

    #  APPLY FILTERS 
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    sender = request.GET.get('sender', '').strip()
    receiver = request.GET.get('receiver', '').strip()
    currency = request.GET.get('currency', '').strip()
    confirmed_by = request.GET.get('confirmed_by', '').strip()
    status_filter = request.GET.get('status', '').strip()

    filters = Q()

    if date_from:
        transactions_qs = transactions_qs.filter(confirmed_at__date__gte=date_from)
        filters &= Q(confirmed_at__date__gte=date_from)
    if date_to:
        transactions_qs = transactions_qs.filter(confirmed_at__date__lte=date_to)
        filters &= Q(confirmed_at__date__lte=date_to)
    if sender:
        transactions_qs = transactions_qs.filter(sender_name__icontains=sender)
        filters &= Q(sender_name__icontains=sender)
    if receiver:
        transactions_qs = transactions_qs.filter(receiver_name__icontains=receiver)
        filters &= Q(receiver_name__icontains=receiver)
    if currency:
        transactions_qs = transactions_qs.filter(currency__iexact=currency)
        filters &= Q(currency__iexact=currency)
    if confirmed_by:
        transactions_qs = transactions_qs.filter(confirmed_by__fullname__icontains=confirmed_by)
        filters &= Q(confirmed_by__fullname__icontains=confirmed_by)
    if status_filter:
        if status_filter == 'completed':
            transactions_qs = transactions_qs.filter(is_completed=True)
            filters &= Q(is_completed=True)
        elif status_filter == 'pending':
            transactions_qs = transactions_qs.filter(is_completed=False)
            filters &= Q(is_completed=False)

    # Filtered USD transactions
    filtered_usd_transactions = transactions_qs.filter(currency='USD')
    filtered_ugx_transactions = transactions_qs.filter(currency='UGX')
    
    filtered_usd_stats = filtered_usd_transactions.aggregate(
        total_count=Count('id'),
        total_amount=Coalesce(Sum('amount'), 0.0, output_field=DecimalField()),
        total_charge=Coalesce(Sum('charge_amount'), 0.0, output_field=DecimalField()),
        total_net=Coalesce(Sum('net_amount'), 0.0, output_field=DecimalField()),
    )
    
    filtered_ugx_stats = filtered_ugx_transactions.aggregate(
        total_count=Count('id'),
        total_amount=Coalesce(Sum('amount'), 0.0, output_field=DecimalField()),
        total_charge=Coalesce(Sum('charge_amount'), 0.0, output_field=DecimalField()),
        total_net=Coalesce(Sum('net_amount'), 0.0, output_field=DecimalField()),
    )
    
    # Calculate filtered UGX equivalents
    filtered_usd_amount_ugx = (filtered_usd_stats['total_amount'] or Decimal('0.00')) * usd_to_ugx_rate
    filtered_usd_charge_ugx = (filtered_usd_stats['total_charge'] or Decimal('0.00')) * usd_to_ugx_rate
    
    filtered_total_amount_ugx = (filtered_ugx_stats['total_amount'] or Decimal('0.00')) + filtered_usd_amount_ugx
    filtered_total_charges_ugx = (filtered_ugx_stats['total_charge'] or Decimal('0.00')) + filtered_usd_charge_ugx

    # Combined filtered stats
    filtered_stats = transactions_qs.aggregate(
        filtered_count=Count('id'),
        filtered_amount=Coalesce(Sum('amount'), 0.0, output_field=DecimalField()),
        filtered_charge=Coalesce(Sum('charge_amount'), 0.0, output_field=DecimalField()),
        filtered_net=Coalesce(Sum('net_amount'), 0.0, output_field=DecimalField()),
        avg_filtered_amount=Coalesce(Avg('amount'), 0.0, output_field=DecimalField()),
    )

    # Top staff by transaction count
    top_staff = transactions_qs.values(
        'confirmed_by__id', 
        'confirmed_by__fullname', 
        'confirmed_by__email'
    ).annotate(
        transaction_count=Count('id'),
        total_amount=Sum('amount'),
        total_charge=Sum('charge_amount')
    ).order_by('-transaction_count')[:5]

    # Top currencies by amount
    top_currencies = transactions_qs.values('currency').annotate(
        transaction_count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-total_amount')[:5]

    #  DOWNLOAD 
    download_format = request.GET.get('download_format')
    if download_format == 'excel':
        return download_transactions_excel(transactions_qs)
    elif download_format == 'pdf':
        return download_transactions_pdf(transactions_qs)

    #  PAGINATION 
    paginator = Paginator(transactions_qs, 10)
    page_number = request.GET.get("page")
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    # Clean querystring (remove page=)
    params = request.GET.copy()
    if 'page' in params:
        params.pop('page')

    #  AJAX LIVE SEARCH 
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'transactions/transactions_table.html', {
            'transactions': page_obj,
            'page_obj': page_obj,
        })

    #  RENDER FULL PAGE 
    context = {
        'transactions': page_obj,
        'page_obj': page_obj,
        'clean_query': params.urlencode(),
        
        # Exchange rate for conversions
        'exchange_rate': usd_to_ugx_rate,
        
        # USD Statistics
        'usd_total_amount': usd_stats['total_amount'] or Decimal('0.00'),
        'usd_total_charge': usd_stats['total_charge'] or Decimal('0.00'),
        'usd_total_net': usd_stats['total_net'] or Decimal('0.00'),
        'usd_count': usd_stats['total_count'] or 0,
        
        # UGX Statistics
        'ugx_total_amount': ugx_stats['total_amount'] or Decimal('0.00'),
        'ugx_total_charge': ugx_stats['total_charge'] or Decimal('0.00'),
        'ugx_total_net': ugx_stats['total_net'] or Decimal('0.00'),
        'ugx_count': ugx_stats['total_count'] or 0,
        
        # Converted amounts
        'usd_amount_ugx': usd_amount_ugx,
        'usd_charge_ugx': usd_charge_ugx,
        'total_amount_ugx': total_amount_ugx,
        'total_charges_ugx': total_charges_ugx,
        
        # Filtered USD Statistics
        'filtered_usd_total_amount': filtered_usd_stats['total_amount'] or Decimal('0.00'),
        'filtered_usd_total_charge': filtered_usd_stats['total_charge'] or Decimal('0.00'),
        'filtered_usd_count': filtered_usd_stats['total_count'] or 0,
        
        # Filtered UGX Statistics
        'filtered_ugx_total_amount': filtered_ugx_stats['total_amount'] or Decimal('0.00'),
        'filtered_ugx_total_charge': filtered_ugx_stats['total_charge'] or Decimal('0.00'),
        'filtered_ugx_count': filtered_ugx_stats['total_count'] or 0,
        
        # Filtered converted amounts
        'filtered_usd_amount_ugx': filtered_usd_amount_ugx,
        'filtered_usd_charge_ugx': filtered_usd_charge_ugx,
        'filtered_total_amount_ugx': filtered_total_amount_ugx,
        'filtered_total_charges_ugx': filtered_total_charges_ugx,
        
        # Global statistics (combined)
        'total_transactions': global_stats['total_count'],
        'total_amount': global_stats['total_amount'],
        'total_charge': global_stats['total_charge'],
        'total_net': global_stats['total_net'],
        'avg_amount': global_stats['avg_amount'],
        'avg_charge': global_stats['avg_charge'],
        'staff_count': global_stats['staff_count'],
        'currency_count': global_stats['currency_count'],
        'country_count': global_stats['country_count'],
        
        # Filtered statistics (combined)
        'filtered_count': filtered_stats['filtered_count'],
        'filtered_amount': filtered_stats['filtered_amount'],
        'filtered_charge': filtered_stats['filtered_charge'],
        'filtered_net': filtered_stats['filtered_net'],
        'avg_filtered_amount': filtered_stats['avg_filtered_amount'],
        
        # Leaderboards
        'top_staff': top_staff,
        'top_currencies': top_currencies,
        'currency_stats': currency_stats[:5],
        
        # Filter values for form persistence
        'date_from': date_from,
        'date_to': date_to,
        'sender': sender,
        'receiver': receiver,
        'currency': currency,
        'confirmed_by': confirmed_by,
        'status_filter': status_filter,
        
        'title': 'Transactions Management',
    }
    
    return render(request, 'transactions/transactions.html', context)

@login_required
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
    rates = ExchangeRate.objects.all().order_by('currency')

    # compute reverse FX
    for rate in rates:
        if rate.currency != "UGX":
            rate.reverse_fx = 1 / float(rate.rate_to_ugx)
        else:
            rate.reverse_fx = None

    context = {"rates": rates}
    return render(request, "exchange_rate/exchange_rate_list.html", context)


def exchange_rate_edit(request, id):
    rate_obj = get_object_or_404(ExchangeRate, id=id)

    if request.method == "POST":
        rate_obj.currency = request.POST.get("currency").upper().strip()
        rate_obj.rate_to_ugx = request.POST.get("rate")
        rate_obj.save()

        messages.success(request, "Exchange rate updated successfully.")
        return redirect("exchange_rate_list")

    return render(request, "exchange_rate/exchange_rate_form.html", {"action": "Edit", "rate": rate_obj})


def exchange_rate_delete(request, id):
    rate_obj = get_object_or_404(ExchangeRate, id=id)
    rate_obj.delete()
    messages.success(request, "Exchange rate deleted successfully.")
    return redirect("exchange_rate_list")

# List
@csrf_protect
@login_required
def proof_steps_list(request):
    steps = UploadProofStep.objects.all()
    return render(request, 'upload_guide/steps_list.html', {'steps': steps, 'title': 'Upload Proof Steps'})

# Add
@csrf_protect
@login_required
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
@login_required
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
@login_required
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

@login_required
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


@login_required
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



@login_required
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


@login_required
def delete_whatsapp_contact(request, contact_id):
    contact = WhatsAppContact.objects.get(id=contact_id)
    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'Contact deleted successfully.')
        return redirect('contacts_list')
    return render(request, 'contacts/delete_contact.html', {'contact': contact, 'title': 'Delete Contact'})
