from django.urls import path
from .views import VerifyOTPView, create_order, verify_and_save,SendOTPView #, test_email
urlpatterns = [
    path("create-order/", create_order, name="create_order"),
    path("verify-and-save/", verify_and_save, name="verify_and_save"),
    #path("test-email/", test_email, name="test_email"),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
]