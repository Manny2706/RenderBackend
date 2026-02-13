import razorpay
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from backend.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,EMAIL_HOST_USER
from .serializers import StudentPaymentSerializer
from .models import Student
from .utils.recaptcha import verify_recaptcha
from .utils.otp_manager import OTPManager
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.utils.decorators import method_decorator
import logging

# Create your views here.
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

class PaymentVerifyThrottle(UserRateThrottle):
    rate = "5/min"


# VERIFY OTP VIEWfrom rest_framework.views import APIView

logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key='ip', rate='10/m', method='POST'), name='post')
class SendOTPView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            
            if not email:
                return Response(
                    {'success': False, 'message': 'Email is required'},
                    status=400
                )
            
            # Email format validation
            email_validator = RegexValidator(
                regex=r'^[a-zA-Z]+25\d+@akgec\.ac\.in$',
                message="Email must be in correct format. Use College Email"
            )
            try:
                email_validator(email)
            except Exception as e:
                logger.error(f"Email validation error: {str(e)}")
                return Response(
                    {'success': False, 'message': f'Invalid email format: {str(e)}'},
                    status=400
                )
            
            ip_address = self.get_client_ip(request)
            
            # OTPManager handles cooldown, attempts, email
            success, message = OTPManager.send_otp(email, ip_address)
            
            return Response(
                {'success': success, 'message': message},
                status=200 if success else 429
            )
        
        except Exception as e:
            logger.error(f"SendOTPView error: {str(e)}")
            return Response(
                {'success': False, 'message': 'Internal server error'},
                status=500
            )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST'), name='post')
class VerifyOTPView(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            otp = request.data.get('otp')
            
            if not email or not otp:
                return Response(
                    {'success': False, 'message': 'Email and OTP are required'},
                    status=400
                )
            if len(otp) != OTPManager.OTP_LENGTH:
                return Response(
                    {'success': False, 'message': "invalid OTP format"},
                    status=400
                )
            # Email format validation
            email_validator = RegexValidator(
                regex=r'^[a-zA-Z]+25\d+@akgec\.ac\.in$' ,#test email
                message="Email must be in correct format. Use College Email"
            )
            try:
                email_validator(email)
            except Exception as e:
                logger.error(f"Email validation error: {str(e)}")
                return Response(
                    {'success': False, 'message': f'Invalid email format: {str(e)}'},
                    status=400
                )
            
            ip_address = self.get_client_ip(request)
            if not ip_address:
                return Response(
                    {'success': False, 'message': 'Could not determine IP address'},
                    status=400
                )
            # OTPManager handles IP rate limit, attempts, verification
            success, message = OTPManager.verify_otp(email, otp, ip_address)
            
            return Response(
                {'success': success, 'message': message},
                status=200 if success else 400
            )
        
        except Exception as e:
            logger.error(f"VerifyOTPView error: {str(e)}")
            return Response(
                {'success': False, 'message': 'Internal server error'},
                status=500
            )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
# view to create razorpay order

@ratelimit(key="ip", rate="10/m", block=False)
@api_view(["POST"])
def create_order(request):
    if getattr(request, "limited", False):
        return Response(
            {"error": "Too many requests. Please try again later."},
            status=429
        )
    captcha_token = request.data.get("captcha_token")
    if not captcha_token:
        return Response(
            {"error": "Captcha token is required"} , status=400)
    if not verify_recaptcha(captcha_token, "create_order"):
        return Response(
            {"error": "Captcha verification failed"}, status=400)
    try:
        order = client.order.create({
            "amount": 10000,  # ₹100 in paise is 10000
            "currency": "INR",
            "payment_capture": 1
        })

        return Response({
            "razorpay_order_id": order["id"],
            "razorpay_key":RAZORPAY_KEY_ID,
            "amount": 10000,
        })
    except Exception:
        return Response(
            {"error": "Failed to create order"},
            status=500
        )
    
# view to verify payment and save student details

@ratelimit(key="ip", rate="3/m", block=False)
@ratelimit(key="post:email", rate="2/m", block=False)
@api_view(["POST"])
@throttle_classes([PaymentVerifyThrottle])
def verify_and_save(request):
    if getattr(request, "limited", False):
        return Response(
            {"error": "Too many requests. Please try again later."},
            status=429
        )
    # Validate input data
    serializer = StudentPaymentSerializer(data=request.data)
    # Check if serializer is valid
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    # Get validated data
    data = serializer.validated_data

    # Block replay attack
    if Student.objects.filter(
        razorpay_payment_id=data["razorpay_payment_id"]
    ).exists():
        return Response(
            {"error": "Payment already processed"},
            status=400
        )
    # Validate email format
    if not(str(data["name"]).split()[0]+str(data["student_no"])+"@akgec.ac.in" == str(data["email"])):
        return Response(
            {"error": "Email is in wrong format"},
            status=400)
    try:
        # Verify Razorpay signature (NON-NEGOTIABLE)
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        })

        # Atomic save in case of any failure, the transaction will be rolled back means no student will be created without valid payment and no payment will be considered successful without creating student record
        with transaction.atomic():
            student = serializer.save()
                
        send_mail(
            subject="Registration Successful",
            message=f"Dear {student.name},\n\nYour registration for the event has been successful. Your student number is {student.student_no}.\n\nThank you for registering!",
            from_email=EMAIL_HOST_USER,
            recipient_list=data.get("email"),
            fail_silently=False
        )
        return Response({
            "message": "Payment successful. Registration completed.",
            "student_id": student.id
        }, status=201)
        
    except Exception:
        return Response(
            {"error": "Payment verification failed"},
            status=400
        )
        
# VIEW TO TEST EMAIL FUNCTIONALITY
# @api_view(["POST"])
# def test_email(request):
#     from django.core.mail import send_mail
#     data = request.data
#     send_mail(
#         subject="Test Email from Django",
#         message="This is a test email sent from the Django backend.",
#         from_email=EMAIL_HOST_USER,
#         recipient_list=[data.get("email")],
#         fail_silently=False
#     )
#     return Response({"message": "Test email sent successfully"})