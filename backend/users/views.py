from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from backend.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,EMAIL_HOST_USER
from .serializers import StudentPaymentSerializer
from rest_framework.throttling import UserRateThrottle
from .models import Student
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django.core.mail import send_mail

from .utils.recaptcha import verify_recaptcha
# Create your views here.
import razorpay
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

class PaymentVerifyThrottle(UserRateThrottle):
    rate = "5/min"


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