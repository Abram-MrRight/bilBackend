from datetime import timezone
from tokenize import TokenError
import uuid
from warnings import filters
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from api.utils import generate_receipt_pdf, send_receipt_email
from .serializers import AgentSerializer, AnnouncementSerializer, ChargeRuleSerializer, CompanyInfoSerializer, CountrySerializer, CurrencySerializer, ProofSerializer, ProofStatusUpdateSerializer, RegisterSerializer, LoginSerializer, TransactionSerializer, UploadProofStepSerializer, UserSerializer, WhatsAppContactSerializer

from rest_framework import generics, permissions, status
from .models import Agent, Announcement, ChargeRule, CompanyInfo, Country, Currency, Proof, ProofRead, Transaction, UploadProofStep, User, WhatsAppContact
from .serializers import UserSerializer, UserUpdateSerializer
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import viewsets
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail

from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib import messages

from django.contrib.auth import get_user_model

User = get_user_model()

# REGISTER

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,  # ✅ Added success field
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    # If serializer is invalid, include success=False
    return Response({
        'success': False,
        'message': 'Registration failed',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# LOGIN
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    phone_number = request.data.get('phone_number', '').strip()
    password = request.data.get('password', '').strip()

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return Response({'success': False, 'message': 'Phone number not found'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({'success': False, 'message': 'Incorrect password'}, status=status.HTTP_401_UNAUTHORIZED)

    # Generate JWT
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return Response({
        'success': True,
        'message': 'Login successful',
        'user': UserSerializer(user).data,
        'token': {
            'access': access_token,
            'refresh': refresh_token
        }
    })

# LOGOUT
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response({"error": "No refresh token provided"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Logged out successfully"}, status=status.HTTP_205_RESET_CONTENT)
    except TokenError:
        return Response({"error": "Invalid token or already logged out"}, status=status.HTTP_400_BAD_REQUEST)

# PROFILE (Authenticated)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user
    return Response(UserSerializer(user).data)

# List all users except yourself
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_users(request):
    users = User.objects.exclude(id=request.user.id)
    serializer = UserSerializer(users, many=True)
    return Response({'success': True, 'data': serializer.data})
 
# Get a single user
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'success': False, 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user)
    return Response({'success': True, 'data': serializer.data})

# Update a user
@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'success': False, 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Only super_admin or the user themselves can update
    if request.user.id != user.id and request.user.role != 'super_admin':
        return Response({'success': False, 'message': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = UserUpdateSerializer(user, data=request.data, partial=True, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({'success': True, 'message': 'User updated successfully.', 'data': serializer.data})

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get("email", "").strip()

    if not email:
        return Response({"success": False, "message": "Email is required"}, status=400)

    User = get_user_model()  # <-- use custom user model
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"success": False, "message": "User not found"}, status=404)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject="Reset Your Password",
        message="Click the link: " + reset_url,
        html_message=f'<p>Click <a href="{reset_url}">here</a> to reset your password.</p>',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )

    return Response({
        "success": True,
        "message": "Password reset link sent successfully."
    })

class ResetPasswordView(View):
    template_name = 'password_reset_form.html'
    def get(self, request):
        uid = request.GET.get('uid')
        token = request.GET.get('token')
        return render(request, 'password_reset_form.html', {'uid': uid, 'token': token})

    def post(self, request):
        uid = request.POST.get('uid')
        token = request.POST.get('token')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        context = {'uid': uid, 'token': token}  

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect(request.path)

        User = get_user_model()
        try:
            uid_decoded = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=uid_decoded)
        except:
            messages.error(request, "Invalid link")
            return redirect(request.path)

        if not default_token_generator.check_token(user, token):
            messages.error(request, "Invalid or expired token")
            return redirect(request.path)

        user.set_password(new_password)
        user.save()
        messages.success(request, "Password reset successful! You can now log in.")
        return render(request, self.template_name, context)
 
def reset_password_page(request):
    if request.method == 'POST':
        uidb64 = request.POST.get('uid')
        token = request.POST.get('token')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            messages.error(request, "Please fill all fields")
            return redirect(request.path)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect(request.path)

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except:
            messages.error(request, "Invalid link")
            return redirect(request.path)

        if not default_token_generator.check_token(user, token):
            messages.error(request, "Invalid or expired token")
            return redirect(request.path)

        user.set_password(new_password)
        user.save()
        messages.success(request, "Password reset successful! You can now log in.")
        return redirect('/login/') 

    # GET request - render form
    uid = request.GET.get('uid')
    token = request.GET.get('token')
    return render(request, 'password_reset_form.html', {'uid': uid, 'token': token})

@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    uidb64 = request.data.get("uid")
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    if not uidb64 or not token or not new_password:
        return Response({"success": False, "message": "Missing fields"}, status=400)

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        return Response({"success": False, "message": "Invalid user"}, status=400)

    if not default_token_generator.check_token(user, token):
        return Response({"success": False, "message": "Invalid or expired token"}, status=400)

    user.set_password(new_password)
    user.save()

    return Response({
        "success": True,
        "message": "Password reset successful"
    }, status=200)

# Delete the authenticated user
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_self(request):
    user = request.user
    user.delete()
    return Response({'success': True, 'message': 'Your account has been deleted successfully.'})

# List proofs (role-based)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_proofs(request):
    user = request.user
    if user.role == 'admin':
        proofs = Proof.objects.filter(user__role='client').select_related('user').prefetch_related('proof_reads')
    elif user.role == 'client':
        proofs = Proof.objects.filter(user=user).select_related('user').prefetch_related('proof_reads')
    else:
        # fallback
        proofs = Proof.objects.filter(user=user) | Proof.objects.filter(proofread__user=user)

    proofs = proofs.order_by('-created_at')
    serializer = ProofSerializer(proofs, many=True)
    return Response({'success': True, 'data': serializer.data})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_agents(request):
    user = request.user

    # Role-based filtering
    if user.role in ['admin', 'client']:
        agents = Agent.objects.all()
    else:
        agents = Agent.objects.none()

    agents = agents.order_by('-created_at')
    serializer = AgentSerializer(agents, many=True)
    return Response({'success': True, 'data': serializer.data})

# Upload proof
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_proof(request):
    data = request.data.copy()
    # Ensure image is included
    if 'image' not in data:
        return Response(
            {'message': 'Image file is required'},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    # Set default status
    data['status'] = 'pending'

    # Validate and save
    serializer = ProofSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    proof = serializer.save(user=request.user)  # Only assign logged-in user

    return Response(
        {'message': 'Proof uploaded successfully', 'data': serializer.data},
        status=status.HTTP_201_CREATED
    )

# Show single proof
@api_view(['GET'])
@permission_classes([permissions])
def get_proof(request, proof_id):
    proof = get_object_or_404(Proof, id=proof_id)
    serializer = ProofSerializer(proof)
    return Response(serializer.data)

# Delete proof
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_proof(request, proof_id):
    proof = get_object_or_404(Proof, id=proof_id)
    proof.delete()
    return Response({'message': 'Proof deleted successfully'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_proof_status(request, proof_id):
    user = request.user

    if not hasattr(user, 'role') or user.role.lower() != 'admin':
        return Response({'message': 'Unauthorized - Admins only'}, status=status.HTTP_403_FORBIDDEN)

    proof = get_object_or_404(Proof, id=proof_id)
    serializer = ProofStatusUpdateSerializer(proof, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    status_value = serializer.validated_data.get('status')
    selected_charge_rule = serializer.validated_data.get('charge_rule')

    print(f"DEBUG: Status value = {status_value}") 
    print(f"DEBUG: Proof ID = {proof_id}") 
    print(f"DEBUG: Charge rule = {selected_charge_rule}") 

    if status_value == 'money_delivered':
        print(f"DEBUG: Entering money_delivered block") 
        
        if not Transaction.objects.filter(proof=proof).exists():
            print(f"DEBUG: Creating new transaction")  
            
            try:
                # Create transaction with ALL required fields
                tx = Transaction.objects.create(
                    proof=proof,
                    user=proof.user,
                    sender_name=proof.sender_name or "Unknown",
                    receiver_name=proof.receiver_name or "Unknown",
                    receiver_contact=proof.receiver_contact or "",
                    amount=proof.amount,
                    currency=proof.currency,
                    transaction_reference=f"TXN-{uuid.uuid4().hex[:10].upper()}",
                    confirmed_by=user,
                    charge_rule=selected_charge_rule,
                    charge_amount=selected_charge_rule.charge_amount if selected_charge_rule else 0,
                    net_amount=proof.amount - (selected_charge_rule.charge_amount if selected_charge_rule else 0),
                    # ADD THESE NEW FIELDS:
                    country=proof.country,  
                    original_currency=proof.currency, 
                    original_amount=proof.amount, 
                    ugx_equivalent=0, 
                )
                
                print(f"DEBUG: Transaction created with ID {tx.id}")  # Debug
                
                # Force save to trigger ugx_equivalent calculation
                tx.save()
                
                print(f"DEBUG: Transaction saved. UGX equivalent = {tx.ugx_equivalent}")  # Debug

                # Generate PDF receipt
                pdf_bytes = generate_receipt_pdf(tx)  

                # Send PDF to sender email
                send_receipt_email(tx, pdf_bytes)
                
                # Delete proof
                proof.delete()

                return Response({
                    'message': 'Delivery confirmed, transaction recorded, and proof deleted permanently',
                    'transaction_id': tx.id
                })
                
            except Exception as e:
                print(f"DEBUG: Error creating transaction: {str(e)}")  # Debug
                import traceback
                print(f"DEBUG: Traceback: {traceback.format_exc()}")  # Debug
                return Response({
                    'message': f'Error creating transaction: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ProofRead.objects.update_or_create(
        proof=proof,
        user=proof.user,
        defaults={'is_read': False, 'read_at': None}
    )

    return Response({
        'message': 'Proof status updated successfully',
        'data': serializer.data
    })

@permission_classes([permissions.IsAuthenticated])
def search_proofs(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    proofs = Proof.objects.select_related('user').all()

    if q:
        proofs = proofs.filter(Q(sender_name__icontains=q) | Q(user__fullname__icontains=q))

    if status:
        proofs = proofs.filter(status=status)

    data = [{
        'id': p.id,
        'sender_name': p.sender_name or (p.user.fullname if p.user else ''),
        'user': p.user.fullname if p.user else '',
        'amount': str(p.amount),
        'currency': p.currency,
        'status': p.status,
        'image': p.image.url if p.image else '',
        'created_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
    } for p in proofs]

    return JsonResponse({'proofs': data})

# Mark proof as read
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_proof_read(request, proof_id):
    proof = get_object_or_404(Proof, id=proof_id)
    ProofRead.objects.update_or_create(proof=proof, user=request.user, defaults={'is_read': True, 'read_at': timezone.now()})
    return Response({'message': 'Proof marked as read.'})

# Unread proofs count
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    count = ProofRead.objects.filter(user=request.user, is_read=False).count()
    return Response({'unread_count': count})

def admin_dashboard(request):
    return HttpResponse("this is admin dashashboard")
# List all announcements or create a new one
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def announcement_list_create(request):
    if request.method == 'GET':
        announcements = Announcement.objects.all().order_by('-created_at')  
        serializer = AnnouncementSerializer(announcements, many=True, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = AnnouncementSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Retrieve, update, delete a single announcement
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def announcement_detail(request, pk):
    try:
        announcement = Announcement.objects.get(pk=pk)
    except Announcement.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = AnnouncementSerializer(announcement, context={'request': request})
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        serializer = AnnouncementSerializer(announcement, data=request.data, partial=(request.method=='PATCH'), context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        announcement.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
class CountryListView(generics.ListAPIView):
    queryset = Country.objects.all().order_by('name')
    serializer_class = CountrySerializer

class ChargeRuleListView(generics.ListAPIView):
    queryset = ChargeRule.objects.all().order_by('country__name')
    serializer_class = ChargeRuleSerializer
    
class CurrencyListByCountry(generics.ListAPIView):
    def get(self, request, country_id):
        try:
            country = Country.objects.get(id=country_id)
            currencies = Currency.objects.filter(country=country)
            serializer = CurrencySerializer(currencies, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Country.DoesNotExist:
            return Response({"detail": "Country not found."}, status=status.HTTP_404_NOT_FOUND)
        
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_company_info(request):
   
    type_filter = request.GET.get('type')
    if type_filter:
        info_items = CompanyInfo.objects.filter(type=type_filter)
    else:
        info_items = CompanyInfo.objects.all()
    
    info_items = info_items.order_by('id')
    serializer = CompanyInfoSerializer(info_items, many=True)
    return Response({'success': True, 'data': serializer.data})

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_upload_proof_steps(request):
    steps = UploadProofStep.objects.all()
    serializer = UploadProofStepSerializer(steps, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_whatsapp_contact(request, contact_id=None):
    if contact_id:  # Single contact
        try:
            contact = WhatsAppContact.objects.get(id=contact_id)
        except WhatsAppContact.DoesNotExist:
            return Response({'success': False, 'message': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = WhatsAppContactSerializer(contact)
        return Response({'success': True, 'data': serializer.data})
    else:  # All contacts
        contacts = WhatsAppContact.objects.all()
        serializer = WhatsAppContactSerializer(contacts, many=True)
        return Response({'success': True, 'data': serializer.data})
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_transactions(request):
    transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-confirmed_at')

    serializer = TransactionSerializer(transactions, many=True)

    return Response(
        {
            'success': True,
            'total_transactions': transactions.count(),
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )