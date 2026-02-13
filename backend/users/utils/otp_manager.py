import redis
import random
import string
import os
from django.core.mail import send_mail
from django.conf import settings

redis_client = redis.from_url(os.getenv('REDIS_URL'), decode_responses=True)

class OTPManager:
    OTP_LENGTH = 6
    OTP_EXPIRY = 300  # 5 minutes
    COOLDOWN = 180 # 3 minutes
    MAX_ATTEMPTS = 3
    
    @staticmethod
    def send_otp(email, ip_address):
        """Send OTP - handles cooldown, email sending"""
        
        try:
            # ✅ Cooldown check (3 min wait)
            cooldown_key = f"Cooldown:{email}"
            if redis_client.exists(cooldown_key):
                ttl = redis_client.ttl(cooldown_key)
                return False, f"Wait {ttl} seconds before requesting again"
            
            # ✅ Generate OTP
            otp = ''.join(random.choices(string.digits, k=OTPManager.OTP_LENGTH))
            
            # ✅ Store OTP in Redis
            otp_key = f"OTP:{email}"
            redis_client.setex(otp_key, OTPManager.OTP_EXPIRY, otp)
            
            # ✅ Set cooldown
            redis_client.setex(cooldown_key, OTPManager.COOLDOWN, "1")
            
            # ✅ Reset attempts
            attempts_key = f"Attempts:{email}"
            redis_client.setex(attempts_key, OTPManager.OTP_EXPIRY, "0")
        except Exception as e:
            return False, f"Failed to send OTP: {str(e)}"
            # ✅ Send email
        try:
                send_mail(
                subject="Your OTP Code",
                message=f"Your OTP is: {otp}\n\nThis OTP will expire in 5 minutes.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False
            )
        except Exception as e:
            return False, f"Failed to send OTP email: {str(e)}"
    
    @staticmethod
    def verify_otp(email, otp_input, ip_address):
        """Verify OTP - handles attempt limiting, verification"""
        
        try:
            # ✅ Check email-based attempts
            attempts_key = f"Attempts:{email}"
            attempts = int(redis_client.get(attempts_key) or 0)
            
            if attempts >= OTPManager.MAX_ATTEMPTS:
                return False, "Max attempts reached. Request new OTP"
            
            # ✅ Get stored OTP
            otp_key = f"OTP:{email}"
            stored_otp = redis_client.get(otp_key)
            
            if not stored_otp:
                return False, "OTP expired or invalid"
            
            # ✅ Increment attempts
            redis_client.incr(attempts_key)
            
            if stored_otp == otp_input:
                # Mark as verified
                verified_key = f"Verified:{email}"
                redis_client.setex(verified_key, 60, "1")
                
                # Cleanup
                redis_client.delete(otp_key)
                redis_client.delete(attempts_key)
                redis_client.delete(f"Cooldown:{email}")
                
                return True, "OTP verified successfully"
            
            remaining = OTPManager.MAX_ATTEMPTS - attempts
            return False, f"Invalid OTP. {remaining-1} attempts left"
        
        except Exception as e:
            return False, f"Verification failed: {str(e)}"