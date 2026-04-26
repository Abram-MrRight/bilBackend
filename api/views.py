from datetime import timezone
from decimal import Decimal, InvalidOperation
from tokenize import TokenError
import traceback
import uuid
from warnings import filters
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.db import transaction as db_transaction 
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from api.utils import decrypt_message, encrypt_message, generate_receipt_pdf, send_receipt_email
from .serializers import AgentSerializer, AnnouncementSerializer, ChargeRuleSerializer, CompanyInfoSerializer, CountrySerializer, CurrencySerializer, ProofSerializer, ProofStatusUpdateSerializer, RegisterSerializer, LoginSerializer, TransactionSerializer, UploadProofStepSerializer, UserSerializer, WhatsAppContactSerializer
from rest_framework.views import APIView
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
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from api import serializers

User = get_user_model()


def decrypt_required_fields(request_data, fields):
    decrypted_fields = {}

    for field in fields:
        encrypted_val = str(request_data.get(field, "")).strip()
        if not encrypted_val:
            continue  # skip empty fields
        try:
            decrypted_fields[field] = decrypt_message(encrypted_val)
        except Exception:
            raise ValueError(f"Invalid encrypted value for {field}")
    
    return decrypted_fields

# REGISTER
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    # Decrypt required fields first
    fields_to_decrypt = ["fullname", "email", "phone_number", "password"]
    try:
        decrypted = decrypt_required_fields(request.data, fields_to_decrypt)
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # Merge decrypted values into request.data for serializer
    mutable_data = request.data.copy()
    mutable_data.update(decrypted)

    # Pass decrypted data to serializer
    serializer = RegisterSerializer(data=mutable_data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True, 
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    # If serializer is invalid
    return Response({
        'success': False,
        'message': 'Registration failed',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# LOGIN
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    # Decrypt required fields
    try:
        decrypted = decrypt_required_fields(request.data, ["phone_number", "password"])
        phone_number = decrypted.get("phone_number", "").strip()
        password = decrypted.get("password", "").strip()
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return Response({'success': False, 'message': 'Phone number not found'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({'success': False, 'message': 'Incorrect password'}, status=status.HTTP_401_UNAUTHORIZED)

    # Generate JWT
    refresh = RefreshToken.for_user(user)
    return Response({
        'success': True,
        'message': 'Login successful',
        'user': UserSerializer(user).data,
        'token': {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
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
    
    # Create a mutable copy of the data
    mutable_data = {}
    try:
        # Handle both QueryDict and regular dict
        for key in request.data:
            mutable_data[key] = request.data.get(key)
            
        # Debug print
        print(f"Update user data received: {list(mutable_data.keys())}")
        
        # Decrypt relevant fields if present
        fields_to_decrypt = ["fullname", "email", "phone_number", "location"]
        encrypted_fields = {}
        
        for field in fields_to_decrypt:
            if field in mutable_data and mutable_data[field]:
                try:
                    encrypted_fields[field] = mutable_data[field]
                except Exception as e:
                    print(f"Error with field {field}: {str(e)}")
                    # If decryption fails, use original value
        
        # Try to decrypt
        try:
            decrypted = decrypt_required_fields(encrypted_fields, fields_to_decrypt)
            mutable_data.update(decrypted)
        except Exception as e:
            print(f"Decryption error: {str(e)}")
            # Continue without decryption for now
        
    except Exception as e:
        return Response({
            'success': False, 
            'message': f'Error processing request data: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        serializer = UserUpdateSerializer(
            user, 
            data=mutable_data, 
            partial=True, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True, 
            'message': 'User updated successfully.', 
            'data': serializer.data
        })
        
    except serializers.ValidationError as e:
        print(f"Serializer validation error: {e.detail}")
        return Response({
            'success': False,
            'message': 'Validation error',
            'errors': e.detail
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        print(f"Unexpected error in update_user: {str(e)}")
        return Response({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    
 
    # Check for image file specifically
    if 'image' in request.data:
        image_obj = request.data['image']
        if hasattr(image_obj, 'name'):
            print(f"Image filename: {image_obj.name}")
            print(f"Image size: {image_obj.size}")
            print(f"Image content_type: {image_obj.content_type}")
        else:
            print("Image exists but is not a file object!")
    else:
        # Check all keys to see what's actually there
        for key, value in request.data.items():
            if hasattr(value, '__class__'):
                print(f"  Class: {value.__class__.__name__}")
    
    data = request.data.copy()
    
    # Ensure image is included
    if 'image' not in data:
        return Response(
            {'success': False, 'message': 'Image file is required'},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    try:
        # Prepare decrypted data
        decrypted_data = {}
        
        # Fields that should be decrypted (text fields)
        text_fields_to_decrypt = [
            "sender_name", 
            "receiver_name", 
            "receiver_email", 
            "receiver_contact",
            "notes"
        ]
        
        # Try to decrypt text fields
        for field in text_fields_to_decrypt:
            if field in data and data[field]:
                try:
                    decrypted_data[field] = decrypt_message(data[field])
                except Exception as e:
                    # If decryption fails, use original value
                    decrypted_data[field] = data[field]
        
        # Handle amount field
        if 'amount' in data and data['amount']:
            amount_value = data['amount']
            try:
                # Try to decrypt if it looks like encrypted text
                if isinstance(amount_value, str) and len(amount_value) > 100:
                    # Likely encrypted
                    decrypted_amount = decrypt_message(amount_value)
                    amount = Decimal(decrypted_amount)
                else:
                    # Plain number
                    amount = Decimal(str(amount_value))
                decrypted_data['amount'] = amount
            except InvalidOperation as e:
                return Response(
                    {'success': False, 'message': f'Invalid amount format: {amount_value}. Must be a number.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                # Try to parse as decimal anyway
                try:
                    decrypted_data['amount'] = Decimal(str(amount_value))
                except:
                    return Response(
                        {'success': False, 'message': f'Invalid amount: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        # Handle other fields
        for key in ['currency', 'country', 'country_id']:
            if key in data and data[key]:
                decrypted_data[key] = data[key]
        
        # Add image file to decrypted_data
        decrypted_data['image'] = data['image']
        
    
        for key, value in decrypted_data.items():
            if key != 'image':
                print(f"  {key}: {value}")
            else:
                print(f"  image: {type(value)}")

        # Validate and save using the serializer
        serializer = ProofSerializer(data=decrypted_data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        
        # Use transaction to ensure data consistency
        with db_transaction.atomic():
            proof = serializer.save(user=request.user)

        
        # Return the serialized proof
        response_serializer = ProofSerializer(proof)
        
        return Response(
            {
                'success': True, 
                'message': 'Proof uploaded successfully', 
                'data': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        traceback.print_exc()
        return Response(
            {'success': False, 'message': f'Server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
@permission_classes([IsAuthenticated])
def update_proof_status(request, proof_id):
    user = request.user
    
    print(f"=== UPDATE PROOF STATUS REQUEST ===")
    print(f"User: {user.username} (Role: {getattr(user, 'role', 'N/A')})")
    print(f"Proof ID: {proof_id}")
    print(f"Request data: {request.data}")
    print(f"Data types:")
    for key, value in request.data.items():
        print(f"  {key}: {value} (type: {type(value)})")
        if isinstance(value, str) and len(value) > 100:
            print(f"    Looks encrypted: Yes")
        else:
            print(f"    Looks encrypted: No")

    # Only admin can update
    if not hasattr(user, 'role') or user.role.lower() != 'admin':
        return Response({'success': False, 'message': 'Unauthorized - Admins only'}, status=status.HTTP_403_FORBIDDEN)

    proof = get_object_or_404(Proof, id=proof_id)

    # Prepare data for processing
    data = request.data.copy()
    
    # Handle decryption for text fields only
    decrypted_data = {}
    
    # Decrypt status field if it's encrypted
    if 'status' in data and data['status']:
        try:
            if isinstance(data['status'], str) and len(data['status']) > 100:
                # Likely encrypted
                decrypted_data['status'] = decrypt_message(data['status'])
            else:
                decrypted_data['status'] = data['status']
        except Exception as e:
            print(f"Error decrypting status: {e}")
            decrypted_data['status'] = data['status']
    
    # Decrypt status_note field if it exists
    if 'status_note' in data and data['status_note']:
        try:
            if isinstance(data['status_note'], str) and len(data['status_note']) > 100:
                decrypted_data['status_note'] = decrypt_message(data['status_note'])
            else:
                decrypted_data['status_note'] = data['status_note']
        except Exception as e:
            print(f"Error decrypting status_note: {e}")
            decrypted_data['status_note'] = data['status_note']
    
    # Handle charge_rule - it should be an ID
    if 'charge_rule' in data and data['charge_rule']:
        try:
            charge_rule_value = data['charge_rule']
            print(f"Processing charge_rule value: {charge_rule_value} (type: {type(charge_rule_value)})")
            
            # If it's a string that looks encrypted, decrypt it
            if isinstance(charge_rule_value, str):
                if len(charge_rule_value) > 100:
                    # Likely encrypted
                    try:
                        decrypted_value = decrypt_message(charge_rule_value)
                        print(f"Decrypted charge_rule: {decrypted_value}")
                        decrypted_data['charge_rule'] = int(decrypted_value)
                    except Exception as e:
                        print(f"Error decrypting charge_rule: {e}")
                        # Try to parse as int directly
                        try:
                            decrypted_data['charge_rule'] = int(charge_rule_value)
                        except:
                            decrypted_data['charge_rule'] = None
                else:
                    # Not encrypted, try to convert to int
                    try:
                        decrypted_data['charge_rule'] = int(charge_rule_value)
                    except:
                        decrypted_data['charge_rule'] = None
            elif isinstance(charge_rule_value, int):
                # Already an int
                decrypted_data['charge_rule'] = charge_rule_value
            elif isinstance(charge_rule_value, dict):
                # Received an object, extract ID
                decrypted_data['charge_rule'] = charge_rule_value.get('id')
            else:
                decrypted_data['charge_rule'] = None
        except Exception as e:
            print(f"Error processing charge_rule: {e}")
            decrypted_data['charge_rule'] = None
    
    print(f"Decrypted data for serializer: {decrypted_data}")
    
    # Update proof status
    serializer = ProofStatusUpdateSerializer(proof, data=decrypted_data, partial=True)
    
    if not serializer.is_valid():
        print(f"Serializer validation errors: {serializer.errors}")
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Use atomic transaction for data consistency
        with db_transaction.atomic():
            # Save the serializer - this will update the proof
            updated_proof = serializer.save()
            
            status_value = serializer.validated_data.get('status')
            
            # Get the charge_rule from the serializer's validated_data
            # It will be a ChargeRule object instance if it was saved
            charge_rule_obj = serializer.validated_data.get('charge_rule')
            selected_charge_rule = None
            
            if charge_rule_obj:
                selected_charge_rule = charge_rule_obj
                print(f"Selected charge rule: {selected_charge_rule.id} - {selected_charge_rule}")
            
            # If money delivered, create transaction  
            if status_value == 'money_delivered':
                # Check if transaction already exists
                if not Transaction.objects.filter(proof=proof).exists():
                    # Calculate charge amount
                    charge_amount = Decimal('0')
                    if selected_charge_rule:
                        charge_amount = selected_charge_rule.charge_amount
                    
                    # Calculate net amount
                    net_amount = proof.amount - charge_amount
                    if net_amount < 0:
                        net_amount = Decimal('0')
                    
                    # Create transaction
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
                        charge_amount=charge_amount,
                        net_amount=net_amount,
                        country=proof.country,  
                        original_currency=proof.currency, 
                        original_amount=proof.amount, 
                        ugx_equivalent=Decimal('0'),
                    )
                    
                    # Generate PDF and send email
                    try:
                        pdf_bytes = generate_receipt_pdf(tx)
                        send_receipt_email(tx, pdf_bytes)
                        print(f"Receipt email sent for transaction {tx.id}")
                    except Exception as e:
                        print(f"Error generating PDF or sending email: {e}")
                        # Don't fail the transaction if email fails
                    
                    # Delete proof (optional)
                    proof.delete()
                    
                    return Response({
                        'success': True,
                        'message': 'Delivery confirmed, transaction recorded, and proof deleted',
                        'transaction_id': tx.id
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': 'Transaction already exists for this proof'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update proof read status if not deleted
            ProofRead.objects.update_or_create(
                proof=proof,
                user=proof.user,
                defaults={'is_read': False, 'read_at': None}
            )

            # Get the updated proof data for response
            response_data = ProofStatusUpdateSerializer(updated_proof).data
            
            return Response({
                'success': True,
                'message': 'Proof status updated successfully',
                'data': response_data
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        print(f"Error in update_proof_status: {str(e)}")
        traceback.print_exc()
        return Response({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
@permission_classes([IsAuthenticated])
def get_upload_proof_steps(request):
    steps = UploadProofStep.objects.all()
    serializer = UploadProofStepSerializer(steps, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
    user = request.user
    
    # Check user role
    is_admin = hasattr(user, 'role') and user.role.lower() == 'admin'
    
    # Filter based on role
    if is_admin:
        # Admin can see all transactions
        transactions = Transaction.objects.all().order_by('-confirmed_at')
        filter_message = "Showing all transactions (admin view)"
    else:
        # Client can only see their own transactions
        transactions = Transaction.objects.filter(
            user=user
        ).order_by('-confirmed_at')
        filter_message = "Showing your transactions"
    
    # FIX: Pass transactions to the serializer
    serializer = TransactionSerializer(transactions, many=True)
    
    return Response(
        {
            'success': True,
            'message': filter_message,
            'total_transactions': transactions.count(),
            'is_admin_view': is_admin,
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )

class EncryptMessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        message = request.data.get('message')
        if not message:
            return Response({'error': 'No message provided.'}, status=status.HTTP_400_BAD_REQUEST)

        encrypted = encrypt_message(message)
        return Response({'encrypted_message': encrypted}, status=status.HTTP_200_OK)
    