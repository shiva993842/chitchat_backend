import logging
from django.conf import settings

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        self.send_sms = getattr(settings, 'SEND_SMS_OTP', False)
        
        # Initialize Twilio client only if everything is configured
        if (self.send_sms and self.account_sid and self.auth_token and 
            TWILIO_AVAILABLE and self.account_sid != 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'):
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
    
    def send_otp(self, mobile_number, otp_code):
        """
        Send OTP via SMS to the given mobile number
        """
        if not self.send_sms or not self.client:
            # Fallback to console if SMS is disabled
            print(f"\n{'='*40}")
            print(f"SMS DISABLED - OTP for {mobile_number}: {otp_code}")
            print(f"{'='*40}\n")
            return True
        
        try:
            # Format mobile number (ensure it starts with +)
            if not mobile_number.startswith('+'):
                mobile_number = '+' + mobile_number
            
            # Create message
            message = self.client.messages.create(
                body=f"Your WhatsApp OTP is: {otp_code}. Valid for 5 minutes.",
                from_=self.from_number,
                to=mobile_number
            )
            
            logger.info(f"OTP sent successfully to {mobile_number}. Message SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OTP to {mobile_number}: {str(e)}")
            # Fallback to console
            print(f"\n{'='*40}")
            print(f"SMS FAILED - OTP for {mobile_number}: {otp_code}")
            print(f"Error: {str(e)}")
            print(f"{'='*40}\n")
            return False

# Create singleton instance
sms_service = SMSService()
