"""
WhatsApp/SMS Bot using Twilio API.

Provides low-bandwidth interface for policy queries via SMS/WhatsApp.
Requires Twilio account (free trial: $15 credit, ~100 messages).
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Check if Twilio credentials are configured
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        TWILIO_ENABLED = True
        logger.info("Twilio client initialized (WhatsApp/SMS enabled)")
    except ImportError:
        TWILIO_ENABLED = False
        logger.warning("Twilio library not installed")
else:
    TWILIO_ENABLED = False
    logger.info("Twilio not configured (WhatsApp/SMS disabled)")


def parse_sms_query(message_body: str) -> Dict[str, str]:
    """
    Parse incoming SMS/WhatsApp message.
    
    Supported formats:
    - "NREGA eligibility" → check eligibility
    - "PM-KISAN details" → get policy details
    - "What is RTI" → general query
    
    Args:
        message_body: Incoming message text
    
    Returns:
        Dict with parsed intent and parameters
    """
    message = message_body.strip().lower()
    
    # Check for eligibility query
    if "eligibility" in message or "eligible" in message or "पात्र" in message:
        # Extract policy name
        for policy in ["nrega", "pm-kisan", "ayushman", "rti", "swachh"]:
            if policy in message:
                return {
                    "intent": "eligibility",
                    "policy": policy.upper()
                }
        return {
            "intent": "eligibility",
            "policy": None
        }
    
    # Check for details query
    if "details" in message or "info" in message or "about" in message or "बारे" in message:
        for policy in ["nrega", "pm-kisan", "ayushman", "rti", "swachh", "digital", "skill", "nep"]:
            if policy in message:
                return {
                    "intent": "details",
                    "policy": policy.upper()
                }
        return {
            "intent": "unknown",
            "query": message_body
        }
    
    # General query
    return {
        "intent": "query",
        "question": message_body
    }


def format_sms_response(response_data: Dict[str, Any], max_length: int = 1600) -> str:
    """
    Format API response for SMS (plain text, concise).
    
    SMS has 1600 char limit for long messages (multi-part).
    
    Args:
        response_data: API response dict
        max_length: Maximum response length
    
    Returns:
        Plain text response for SMS
    """
    try:
        # Handle eligibility response
        if "eligible_schemes" in response_data:
            schemes = response_data["eligible_schemes"]
            if not schemes:
                return "You are not currently eligible for any schemes based on your profile. Reply with 'HELP' for more info."
            
            response = f"You are eligible for {len(schemes)} scheme(s):\n\n"
            for i, scheme in enumerate(schemes[:3], 1):  # Limit to 3
                response += f"{i}. {scheme['policy_name']}\n"
                response += f"   Benefits: {scheme['benefits']}\n"
                response += f"   Apply: {scheme['application_link']}\n\n"
            
            if len(schemes) > 3:
                response += f"+ {len(schemes)-3} more schemes. Visit website for full list."
            
            return response[:max_length]
        
        # Handle policy details response
        if "policy_name" in response_data:
            response = f"{response_data['policy_name']}\n\n"
            response += f"{response_data.get('description', '')}\n\n"
            response += f"Benefits: {response_data.get('benefits', 'N/A')}\n\n"
            response += f"Apply: {response_data.get('application_link', 'N/A')}"
            return response[:max_length]
        
        # Handle query response
        if "final_answer" in response_data:
            answer = response_data["final_answer"]
            
            # Truncate and add "..." if too long
            if len(answer) > max_length - 50:
                answer = answer[:max_length-50] + "...\n\nFor full answer, visit: policypulse.com"
            
            return answer
        
        # Fallback
        return "Sorry, I couldn't process your request. Reply 'HELP' for usage instructions."
        
    except Exception as e:
        logger.error(f"SMS formatting error: {e}")
        return "Error processing response. Please try again later."


def send_sms(to_number: str, message: str) -> bool:
    """
    Send SMS via Twilio.
    
    Args:
        to_number: Recipient phone number (E.164 format, e.g., +919876543210)
        message: Message text
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not TWILIO_ENABLED:
        logger.warning("Twilio not enabled, cannot send SMS")
        return False
    
    try:
        message_obj = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        logger.info(f"SMS sent to {to_number}, SID: {message_obj.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False


def send_whatsapp(to_number: str, message: str) -> bool:
    """
    Send WhatsApp message via Twilio.
    
    Args:
        to_number: Recipient WhatsApp number (E.164 format)
        message: Message text
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not TWILIO_ENABLED:
        logger.warning("Twilio not enabled, cannot send WhatsApp")
        return False
    
    try:
        # WhatsApp numbers must be prefixed with 'whatsapp:'
        message_obj = twilio_client.messages.create(
            body=message,
            from_=f'whatsapp:{TWILIO_PHONE_NUMBER}',
            to=f'whatsapp:{to_number}'
        )
        logger.info(f"WhatsApp sent to {to_number}, SID: {message_obj.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send WhatsApp: {e}")
        return False


# Help message for users
HELP_MESSAGE = """PolicyPulse - Your Civic Assistant

COMMANDS:
• [POLICY] eligibility - Check if you're eligible
• [POLICY] details - Get policy info
• What is [POLICY] - General query

POLICIES:
NREGA, PM-KISAN, AYUSHMAN, RTI, SWACHH, NEP, DIGITAL-INDIA, SKILL-INDIA

EXAMPLE:
"NREGA eligibility"
"What is PM-KISAN"

Website: policypulse.com
"""


def get_help_message() -> str:
    """Get formatted help message."""
    return HELP_MESSAGE
