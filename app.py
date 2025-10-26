from flask import Flask, request, jsonify
from datetime import datetime
import smtplib
import uuid
import os
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config

# Initialize Flask app
app = Flask(__name__)

# Email configuration from environment variables
GMAIL_EMAIL = config('GMAIL_EMAIL', default='hadibadami14@gmail.com')
GMAIL_APP_PASSWORD = config('GMAIL_APP_PASSWORD', default='')
SMTP_SERVER = config('SMTP_SERVER', default='smtp.gmail.com')
SMTP_PORT = config('SMTP_PORT', default=587, cast=int)

def validate_email_config():
    """Validate that email configuration is properly set"""
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        return False, "Email configuration missing. Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD environment variables."
    return True, "OK"

def send_email_smtp(receiver_email, subject, body_text):
    """
    Send email using Gmail SMTP
    Returns: (success: bool, message: str, email_id: str)
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body_text, 'plain'))
        
        # Create SMTP session
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Enable security
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            
            # Convert message to string and send
            text = msg.as_string()
            server.sendmail(GMAIL_EMAIL, receiver_email, text)
            
            # Generate unique email ID for tracking
            email_id = str(uuid.uuid4())
            return True, "Email sent successfully", email_id
            
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP Authentication failed. Check your Gmail credentials: {str(e)}", None
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"Invalid recipient email address: {str(e)}", None
    except smtplib.SMTPServerDisconnected as e:
        return False, f"SMTP server connection lost: {str(e)}", None
    except smtplib.SMTPException as e:
        return False, f"SMTP error occurred: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None

# Health check endpoint
@app.route('/')
def home():
    config_valid, config_msg = validate_email_config()
    return jsonify({
        "service": "Email Sending API",
        "version": "1.0.0",
        "status": "running",
        "email_config_valid": config_valid,
        "timestamp": datetime.utcnow().isoformat()
    })

# Email sending endpoint
@app.route('/send-email', methods=['POST'])
def send_email():
    """
    POST /send-email
    Send email to specified recipient
    Expected JSON body: {
        "receiver_email": "user@example.com",
        "subject": "Email Subject",
        "body_text": "Email content here"
    }
    """
    try:
        # Validate email configuration
        config_valid, config_msg = validate_email_config()
        if not config_valid:
            return jsonify({
                "error": "Server configuration error",
                "message": config_msg
            }), 500
        
        # Get JSON data from request
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "Request body is required"
            }), 400
        
        # Validate required fields
        required_fields = ['receiver_email', 'subject', 'body_text']
        missing_fields = []
        
        for field in required_fields:
            if not data.get(field) or not data.get(field).strip():
                missing_fields.append(field)
        
        if missing_fields:
            return jsonify({
                "error": "Missing required fields",
                "missing_fields": missing_fields,
                "required_fields": required_fields
            }), 400
        
        # Extract and clean data
        receiver_email = data['receiver_email'].strip()
        subject = data['subject'].strip()
        body_text = data['body_text'].strip()
        
        # Basic email validation
        if '@' not in receiver_email or '.' not in receiver_email:
            return jsonify({
                "error": "Invalid email format",
                "message": "Please provide a valid email address"
            }), 400
        
        # Attempt to send email
        success, message, email_id = send_email_smtp(receiver_email, subject, body_text)
        
        if success:
            return jsonify({
                "status": "success",
                "message": message,
                "email_id": email_id,
                "sent_to": receiver_email,
                "sent_from": GMAIL_EMAIL,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        else:
            # Determine appropriate HTTP status code based on error type
            if "Authentication" in message:
                return jsonify({
                    "error": "Authentication failed",
                    "message": message
                }), 401
            elif "recipient" in message.lower():
                return jsonify({
                    "error": "Invalid recipient",
                    "message": message
                }), 400
            else:
                return jsonify({
                    "error": "Email sending failed",
                    "message": message
                }), 502  # Bad Gateway - external service issue
    
    except Exception as e:
        # Log the full error for debugging
        error_details = traceback.format_exc()
        print(f"Unexpected error in send_email: {error_details}")
        
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred while processing your request"
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
