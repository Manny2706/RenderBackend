from django.db import models

# Create your models here.

class Student(models.Model):
    student_no = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    section = models.CharField(max_length=10)
    hostler = models.BooleanField(default=False)
    email = models.EmailField(unique=True)

    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, unique=True)
    razorpay_signature = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_no} - {self.name}"
