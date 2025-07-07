from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import strip_tags
from django.conf import settings
from django.template.loader import render_to_string
from smtplib import SMTPAuthenticationError
import logging

logger = logging.getLogger(__name__)

def send_custom_email(subject, message, recipient_list, use_pw_reset=False):
    try:
        if use_pw_reset:
            email_host_user = settings.EMAIL_PW_RESET_USER
            email_host_password = settings.EMAIL_PW_RESET_PASS
            from_email = f"NDAS Password Reset <{settings.EMAIL_PW_RESET_USER}>"
        else:
            email_host_user = settings.EMAIL_HOST_USER
            email_host_password = settings.EMAIL_HOST_PASSWORD
            from_email = settings.DEFAULT_FROM_EMAIL

        connection = get_connection(
            backend=settings.EMAIL_BACKEND,
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=email_host_user,
            password=email_host_password,
            use_tls=settings.EMAIL_USE_TLS,
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(message),
            from_email=from_email,
            to=recipient_list,
            connection=connection
        )
        email.attach_alternative(message, "text/html")
        email.send()
        return True
    except SMTPAuthenticationError as e:
        logger.error(f"SMTP Auth Failed: {e}")
        # Implement fallback logic here
        return False
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False

def send_password_reset_confirmation(user):
    """
    New dedicated function for password reset confirmations
    Uses your existing send_custom_email function
    """
    subject = "Your Password Has Been Reset Successfully"  
    context = {
        'username': user.username,
        'support_email': settings.SUPPORT_EMAIL,
        'site_name': settings.SITE_NAME
    }
    # Render HTML template
    html_message = render_to_string(
        'user_app/email_reset_pw_confirmation.html',
        context
    )
    send_custom_email(
        subject=subject,
        message=html_message,
        recipient_list=[user.email],
        use_pw_reset=False  # Uses default email credentials
    )