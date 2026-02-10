from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from backend.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
from .serializers import StudentPaymentSerializer
from rest_framework.throttling import UserRateThrottle
from rest_framework.exceptions import ValidationError
from .models import Student
from django.db import transaction
from django_ratelimit.decorators import ratelimit

from .utils.recaptcha import verify_recaptcha
# Create your views here.
import razorpay
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

class PaymentVerifyThrottle(UserRateThrottle):
    rate = "5/min"


# view to create razorpay order
@ratelimit(key="ip", rate="10/m", block=True)
@api_view(["POST"])
def create_order(request):
    captcha_token = request.data.get("captcha_token")
    if not captcha_token:
        raise ValidationError({"captcha_token": "This field is required."})
    if not verify_recaptcha(captcha_token, "create_order"):
        raise ValidationError({"captcha_token": "Invalid captcha. Please try again."})
    try:
        order = client.order.create({
            "amount": 10000,  # ₹150 in paise is 15000
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

@ratelimit(key="ip", rate="3/m", block=True)
@ratelimit(key="post:email", rate="2/m", block=True)
@api_view(["POST"])
@throttle_classes([PaymentVerifyThrottle])
def verify_and_save(request):

    serializer = StudentPaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data

    # Block replay attack
    if Student.objects.filter(
        razorpay_payment_id=data["razorpay_payment_id"]
    ).exists():
        return Response(
            {"error": "Payment already processed"},
            status=400
        )

    try:
        # Verify Razorpay signature (NON-NEGOTIABLE)
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        })

        # Atomic save
        with transaction.atomic():
            student = serializer.save()

        return Response({
            "message": "Payment successful. Registration completed.",
            "student_id": student.id
        }, status=201)

    except Exception:
        return Response(
            {"error": "Payment verification failed"},
            status=400
        )