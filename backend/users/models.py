from django.db import models
from django.core.validators import RegexValidator


class Student(models.Model):
    BRANCH_CHOICES = [
        ('CSE', 'CSE'),
        ('CS', 'CS'),
        ('CS-IT', 'CS-IT'),
        ('CSE-DS', 'CSE-DS'),
        ('CS-HINDI', 'CS-HINDI'),
        ('CSE-AIML', 'CSE-AIML'),
        ('IT', 'IT'),
        ('AIML', 'AIML'),
        ('ECE', 'ECE'),
        ('ME', 'ME'),
        ('EN', 'EN'),
        ('CIVIL', 'CIVIL'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    ]
    email_regex = RegexValidator(
        regex=r'^[a-zA-Z]+25\d+@akgec\.ac\.in$',
        message="Email must end with @akgec.ac.in"
    )
    
    phone_regex = RegexValidator(
        regex=r'^\d{10,12}$',
        message="Phone number must be 10 to 12 digits"
    )
    student_number_regex = RegexValidator(
        regex=r'^25\d{4,6}$',
        message="Student number must start with 25 and be 6 to 8 digits long"
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, validators=[email_regex],null=False, blank=False)
    phone = models.CharField(validators=[phone_regex], max_length=12)
    student_number = models.CharField(max_length=20, unique=True, validators=[student_number_regex] )
    branch = models.CharField(max_length=20, choices=BRANCH_CHOICES)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    hostler = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    is_present = models.BooleanField(default=False)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.student_number}"
    class Meta:
        ordering = ['-created_at']