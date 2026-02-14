from django.urls import path
from .views import SendOTPView, VerifyOTPAPIView , PaymentInitiationAPIView ,RazorpayWebhookAPIView , PaymentStatusAPIView #, test_email
urlpatterns = [
    #path("test-email/", test_email, name="test_email"),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPAPIView.as_view(), name='verify-otp'),
    path('payment-initiation/', PaymentInitiationAPIView.as_view(), name='payment-initiation'),
    path('razorpay-webhook/', RazorpayWebhookAPIView.as_view(), name='razorpay-webhook'),   
    path('payment-status/', PaymentStatusAPIView.as_view(), name='payment-status'),
]