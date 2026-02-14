from urllib import request
from django.conf import settings
import razorpay
from rest_framework.decorators import  throttle_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from backend.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
from .serializers import StudentSerializer
from .models import Student
from .utils.recaptcha import verify_recaptcha
from .utils.otp_manager import OTPManager
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import logging
from django.core.validators import RegexValidator


def  verify_mail_fail(email):
    if RegexValidator(
        regex=r'^[a-zA-Z]+24\d+@akgec\.ac\.in$',
        message='Email is incorrect format. Use College Email')(email):
        return True
    return False




# Create your views here.
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

class PaymentVerifyThrottle(UserRateThrottle):
    rate = "5/min"


# VERIFY OTP VIEWfrom rest_framework.views import APIView

logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key='ip', rate='10/m', method='POST',block=False), name='post')
class SendOTPView(APIView):
    def post(self, request):
        if getattr(request, "limited", False):
            pass
            return Response({"detail": "Too many requests. Please try again later."}, status=429)
        try:
            email = request.data.get('email')
            # print(email)
            
            if not email:
                return Response(
                    {'success': False, 'message': 'Email is required'},
                    status=400
                )
            
            if verify_mail_fail(email):
                    return Response(
                        {'success': False, 'message': 'Invalid email format. Use College Email'},
                        status=400
                    )
            
            ip_address = self.get_client_ip(request)
            # print(ip_address)
            # OTPManager handles cooldown, attempts, email
            success, message = OTPManager.send_otp(email, ip_address)
            
            return Response(
                {'success': success, 'message': message},
                status=200 if success else 429
            )
        
        except Exception as e:
            logger.error(f"SendOTPView error: {str(e)}")
            return Response(
                {'success': False, 'message': f"Error sending OTP: {str(e)}"},
                status=500
            )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST',block=False), name='post')
class VerifyOTPAPIView(APIView):
    def post(self, request):
        if getattr(request, "limited", False):
            return Response({"detail": "Too many requests. Please try again later."}, status=429)
        email = request.data.get('email')
        otp = request.data.get('otp')
        data = request.data

        if not email or not otp:
            return Response({"detail": "email and otp are required"}, status=400)

        # if email exists
        existing = Student.objects.filter(email=email).first()
        if existing:
            if existing.payment_status == 'SUCCESS':
                return Response({"detail": "Payment already completed for this email"}, status=400)

            if existing.is_email_verified and existing.payment_status in ['PENDING', 'FAILED']:
                return Response({"id": existing.id}, status=200)

            # not verified yet -> verify OTP and update record
            if not OTPManager.verify_otp(email, otp):
                return Response({"detail": "Invalid OTP"}, status=400)

            serializer = StudentSerializer(existing, data=data, partial=True)
            if serializer.is_valid():
                serializer.save(is_email_verified=True)
                return Response({"id": existing.id, "is_email_verified": True}, status=200)
            return Response(serializer.errors, status=400)

        # new email -> verify OTP, then create
        if not(str(data["name"]).split()[0]+str(data["student_no"])+"@akgec.ac.in" == str(data["email"])):
            return Response(
                {"error": "Email is in wrong format"},
                status=400)
        if not OTPManager.verify_otp(email, otp):
            return Response({"detail": "Invalid OTP", }, status=400)

        serializer = StudentSerializer(data=data)
        if serializer.is_valid():
            student = serializer.save(is_email_verified=True)
            return Response({"id": student.id}, status=200)

        return Response(serializer.errors, status=400)



@method_decorator(ratelimit(key='ip', rate='5/m', method='POST',block=False), name='post')
class PaymentInitiationAPIView(APIView):
    def post(self, request):
        if getattr(request, "limited", False):
            return Response({"detail": "Too many requests. Please try again later."}, status=429)
        student_id = request.data.get('student_id')
        recaptcha_token = request.data.get('recaptcha_token')

        if not verify_recaptcha(recaptcha_token):
            return Response({"detail": "Invalid reCAPTCHA"}, status= 400)

        student = Student.objects.filter(id=student_id).first()
        if not student:
            return Response({"detail": "Student not found"}, status= 404 )

        if not student.is_email_verified:
            return Response({"detail": "Email not verified"}, status= 400 )

        if student.payment_status == 'SUCCESS':
            return Response({"detail": "Payment already completed, You are registered"}, status= 400 )

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        order_data = {
            "amount": settings.REGISTRATION_AMOUNT,
            "currency": "INR",
            "receipt": f"receipt_{student_id}",
            "payment_capture": 1
        }

        try:
            order = client.order.create(data=order_data)
            student.order_id = order.get('id')
            student.save(update_fields=['order_id'])
            return Response(order, status= 200)
        except Exception as e:
            return Response({"detail": str(e)}, status= 500)


@method_decorator(ratelimit(key='ip', rate='7/m', method='POST',block=False), name='post')
class RazorpayWebhookAPIView(APIView):
    def post(self, request):
        if getattr(request, "limited", False):
            return Response({"detail": "Too many requests. Please try again later."}, status=429)
        payload = request.body
        signature = request.headers.get('X-Razorpay-Signature')

        # verify signature
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_webhook_signature(payload, signature, settings.RAZORPAY_WEBHOOK_SECRET)
        except Exception:
            return Response({"detail": "Invalid signature"}, status= 400 )

        event = request.data.get('event')
        payment_entity = request.data.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')

        student = Student.objects.filter(order_id=order_id).first()
        if not student:
            return Response({"detail": "Student not found"}, status= 404 )

        if event == 'payment.captured':
            student.payment_status = 'SUCCESS'
        elif event == 'payment.failed':
            student.payment_status = 'FAILED'

        student.payment_id = payment_id
        student.save(update_fields=['payment_status', 'payment_id'])
        return Response({"detail": "OK , Payment Verified"}, status=200)


@method_decorator(ratelimit(key='ip', rate='5/m', method='GET',block=False), name='get')
class PaymentStatusAPIView(APIView):
    
    def get(self, request, student_id):
        if getattr(request, "limited", False):
            return Response({"detail": "Too many requests. Please try again later."}, status=429)   \
            
        student = Student.objects.filter(id=student_id).first()
        if not student:
            return Response({"detail": "Student not found"}, status= 404 )
        return Response({"id": student.id, "payment_status": student.payment_status}, status= 200)

# # view to create razorpay order

# @ratelimit(key="ip", rate="10/m", block=False)
# @api_view(["POST"])
# def create_order(request):
#     if getattr(request, "limited", False):
#         return Response(
#             {"error": "Too many requests. Please try again later."},
#             status=429
#         )
#     captcha_token = request.data.get("captcha_token")
#     if not captcha_token:
#         return Response(
#             {"error": "Captcha token is required"} , status=400)
#     if not verify_recaptcha(captcha_token, "create_order"):
#         return Response(
#             {"error": "Captcha verification failed"}, status=400)
#     try:
#         order = client.order.create({
#             "amount": 10000,  # ₹100 in paise is 10000
#             "currency": "INR",
#             "payment_capture": 1
#         })

#         return Response({
#             "razorpay_order_id": order["id"],
#             "razorpay_key":RAZORPAY_KEY_ID,
#             "amount": 10000,
#         })
#     except Exception:
#         return Response(
#             {"error": "Failed to create order"},
#             status=500
#         )
    
# # view to verify payment and save student details

# @ratelimit(key="ip", rate="3/m", block=False)
# @ratelimit(key="post:email", rate="2/m", block=False)
# @api_view(["POST"])
# @throttle_classes([PaymentVerifyThrottle])
# def verify_and_save(request):
#     if getattr(request, "limited", False):
#         return Response(
#             {"error": "Too many requests. Please try again later."},
#             status=429
#         )
#     # Validate input data
#     serializer = StudentPaymentSerializer(data=request.data)
#     # Check if serializer is valid
#     if not serializer.is_valid():
#         return Response(serializer.errors, status=400)
#     # Get validated data
#     data = serializer.validated_data

#     # Block replay attack
#     if Student.objects.filter(
#         razorpay_payment_id=data["razorpay_payment_id"]
#     ).exists():
#         return Response(
#             {"error": "Payment already processed"},
#             status=400
#         )
#     # Validate email format
#     if not(str(data["name"]).split()[0]+str(data["student_no"])+"@akgec.ac.in" == str(data["email"])):
#         return Response(
#             {"error": "Email is in wrong format"},
#             status=400)
#     try:
#         # Verify Razorpay signature (NON-NEGOTIABLE)
#         client.utility.verify_payment_signature({
#             "razorpay_order_id": data["razorpay_order_id"],
#             "razorpay_payment_id": data["razorpay_payment_id"],
#             "razorpay_signature": data["razorpay_signature"],
#         })

#         # Atomic save in case of any failure, the transaction will be rolled back means no student will be created without valid payment and no payment will be considered successful without creating student record
#         with transaction.atomic():
#             student = serializer.save()
                
#         send_mail(
#             subject="Registration Successful",
#             message=f"Dear {student.name},\n\nYour registration for the event has been successful. Your student number is {student.student_no}.\n\nThank you for registering!",
#             from_email=EMAIL_HOST_USER,
#             recipient_list=data.get("email"),
#             fail_silently=False
#         )
#         return Response({
#             "message": "Payment successful. Registration completed.",
#             "student_id": student.id
#         }, status=201)
        
#     except Exception:
#         return Response(
#             {"error": "Payment verification failed"},
#             status=400
#         )
        
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