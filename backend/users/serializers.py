from rest_framework import serializers
from .models import  Student

# class StudentPaymentSerializer(serializers.ModelSerializer):

#     def validate(self, attrs):
#         if Student.objects.filter(student_no=attrs["student_no"]).exists():
#             raise serializers.ValidationError(
#                 {"student_no": "Student already registered"}
#             )

#         if Student.objects.filter(email=attrs["email"]).exists():
#             raise serializers.ValidationError(
#                 {"email": "Email already registered"}
#             )

#         return attrs
    
#     class Meta:
#         model = Student
#         fields = [
#             "student_no",
#             "name",
#             "section",
#             "hostler",
#             "email",
#             "phone_no",
#             "gender",
#             "razorpay_order_id",
#             "razorpay_payment_id",
#             "razorpay_signature",
#         ]
#         extra_kwargs = {
#             "student_no": {
#                 "required": True,
#                 "allow_blank": False,
#                 "min_length": 8,
#                 "max_length": 8
#             },
#             "name": {"required": True, "allow_blank": False},
#             "section": {"required": True, "allow_blank": False},
#             "hostler": {"required": True},
#             "email": {"required": True, "allow_blank": False},
#             "phone_no": {
#                 "required": True,
#                 "allow_blank": False,
#                 "min_length": 10,
#                 "max_length": 13
#             },
#             'gender': {"required": True},
#             "razorpay_order_id": {"required": True},
#             "razorpay_payment_id": {"required": True},
#             "razorpay_signature": {"required": True},
#         }


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'student_number',
            'year',
            'branch',
            'is_email_verified',
            'payment_status',
            'is_present',
            'razorpay_order_id',
            'razorpay_payment_id',
            'razorpay_signature',
            "created_at",
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'is_email_verified',
            'payment_status',
            'is_present',
            'razorpay_order_id',
            'razorpay_payment_id',
            'razorpay_signature',
            'created_at',
            'updated_at'
        ]
    def validate_email(self, value):
        if Student.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
