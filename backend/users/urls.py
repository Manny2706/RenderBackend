from django.urls import path
from .views import create_order, verify_and_save
urlpatterns = [
    path("create-order/", create_order, name="create_order"),
    path("verify-and-save/", verify_and_save, name="verify_and_save"),
]