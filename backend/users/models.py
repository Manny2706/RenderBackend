from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone

# Create your models here.
Gender_CHOICES={
    ('M', 'Male'),
    ( 'F','Female')
}
class Student(models.Model):
    student_no = models.CharField(
        max_length=8,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^25\d{6}$',
                message='Student number must start with 25 followed by 6 digits'
            )
        ]
    )
    name = models.CharField(max_length=100)
    section = models.CharField(max_length=10)
    hostler = models.BooleanField(default=False)
    email = models.EmailField(
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z]+25\d+@akgec\.ac\.in$',
                message='Email must be in format: name25rollno@akgec.ac.in'
            )
        ]
    )
    phone_no = models.CharField(
        max_length=13,
        validators=[
            RegexValidator(
                regex=r'^\d{10,13}$',
                message='Phone number must be 10 to 13 digits'
            )
        ]
    )
    gender = models.CharField(max_length=1, choices=Gender_CHOICES)
    razorpay_payment_id = models.CharField(max_length=100, unique=True)
    razorpay_signature = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_no} - {self.name}"
    class Meta:
        ordering = ['-created_at']