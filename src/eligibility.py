"""
Eligibility Checker - Rule-based matching for government schemes.

Determines user eligibility for various policies based on profile.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# hard-coded for now - ideally would pull from a config DB
# talked to ministry folks, these rules don't change often anyway


# Eligibility rules for each policy
ELIGIBILITY_RULES = {
    "NREGA": {
        "name": "Mahatma Gandhi National Rural Employment Guarantee Act",
        "description": "100 days of guaranteed wage employment",
        "rules": {
            "location_type": ["rural"],  # Must be in rural area
            "age_min": 18,
            "willingness_manual_work": True
        },
        "documents_required": [
            "Job card",
            "Aadhar card",
            "Bank account details",
            "Address proof"
        ],
        "application_link": "https://nrega.nic.in/",
        "benefits": "₹209-318 per day wage, 100 days guaranteed employment per year"
        # NOTE: wage rates vary by state, this is the central avg
    },
    
    "PM-KISAN": {
        "name": "Pradhan Mantri Kisan Samman Nidhi",
        "description": "₹6000 annual income support for farmers",
        "rules": {
            "occupation": ["farmer", "agricultural worker"],
            "land_ownership": True,  # Must own agricultural land
            "income_max": None  # removed income limit in 2019 amendment
        },
        "documents_required": [
            "Land ownership documents",
            "Aadhar card",
            "Bank account details"
        ],
        "application_link": "https://pmkisan.gov.in/",
        "benefits": "₹6000 per year in 3 installments of ₹2000 each"
    },
    
    "AYUSHMAN-BHARAT": {
        "name": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana",
        "description": "₹5 lakh health insurance coverage",
        "rules": {
            "income_max": 100000,  # Annual income < ₹1 lakh
            "location_type": ["rural", "urban"]
        },
        "documents_required": [
            "Aadhar card",
            "Ration card",
            "Income certificate"
        ],
        "application_link": "https://pmjay.gov.in/",
        "benefits": "₹5 lakh health insurance per family per year"
    },
    
    "RTI": {
        "name": "Right to Information",
        "description": "Access to government information",
        "rules": {
            "location_type": ["rural", "urban"],  # All citizens
            "age_min": 18
        },
        "documents_required": [
            "Application form",
            "Fee payment (₹10)"
        ],
        "application_link": "https://rtionline.gov.in/",
        "benefits": "Access to government documents and information within 30 days"
    },
    
    "SWACHH-BHARAT": {
        "name": "Swachh Bharat Mission",
        "description": "Toilet construction subsidy",
        "rules": {
            "has_toilet": False,  # Must not have toilet
            "income_max": 100000,
            "location_type": ["rural", "urban"]
        },
        "documents_required": [
            "Aadhar card",
            "Income certificate",
            "Address proof"
        ],
        "application_link": "https://swachhbharatmission.gov.in/",
        "benefits": "₹12,000 subsidy for toilet construction"
    },
    
    "DIGITAL-INDIA": {
        "name": "Digital India Initiative",
        "description": "Digital literacy and services",
        "rules": {
            "location_type": ["rural", "urban"]  # Open to all
        },
        "documents_required": [],
        "application_link": "https://www.digitalindia.gov.in/",
        "benefits": "Free digital literacy training, online government services"
    },
    
    "SKILL-INDIA": {
        "name": "Skill India Mission",
        "description": "Vocational training programs",
        "rules": {
            "age_min": 15,
            "age_max": 45,
            "location_type": ["rural", "urban"]
        },
        "documents_required": [
            "Aadhar card",
            "Educational certificates"
        ],
        "application_link": "https://www.skillindia.gov.in/",
        "benefits": "Free vocational training, certification, placement assistance"
    },
    
    "MAKE-IN-INDIA": {
        "name": "Make in India",
        "description": "Manufacturing and business support",
        "rules": {
            "occupation": ["entrepreneur", "business owner", "manufacturer"],
            "location_type": ["rural", "urban"]
        },
        "documents_required": [
            "Business registration",
            "GST registration",
            "Project report"
        ],
        "application_link": "https://www.makeinindia.com/",
        "benefits": "Business incentives, subsidies, ease of doing business"
    },
    
    "SMART-CITIES": {
        "name": "Smart Cities Mission",
        "description": "Urban infrastructure development",
        "rules": {
            "location_type": ["urban"],  # Only urban areas
            "in_smart_city": True  # Must be in designated smart city
        },
        "documents_required": [],
        "application_link": "http://smartcities.gov.in/",
        "benefits": "Improved urban infrastructure, digital services, quality of life"
    },
    
    "NEP": {
        "name": "National Education Policy",
        "description": "Education reforms and benefits",
        "rules": {
            "age_min": 3,
            "age_max": 25,  # Students
            "location_type": ["rural", "urban"]
        },
        "documents_required": [
            "School/college enrollment proof",
            "Aadhar card"
        ],
        "application_link": "https://www.education.gov.in/nep",
        "benefits": "Improved education quality, scholarships, vocational training"
    }
}


def check_eligibility(user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check which schemes a user is eligible for.
    
    Args:
        user_profile: Dict with user information:
            - age: int
            - occupation: str (e.g., 'farmer', 'student', 'entrepreneur')
            - location_type: str ('rural' or 'urban')
            - income: int (annual income in rupees)
            - land_ownership: bool
            - has_toilet: bool
            - willingness_manual_work: bool
            - in_smart_city: bool
            - category: str ('general', 'sc', 'st', 'obc')
    
    Returns:
        List of eligible schemes with details and application steps
    """
    eligible_schemes = []
    
    for policy_id, policy_data in ELIGIBILITY_RULES.items():
        rules = policy_data["rules"]
        is_eligible = True
        reasons = []
        
        # Check each rule
        
        # Age check
        if "age_min" in rules:
            if user_profile.get("age", 0) < rules["age_min"]:
                is_eligible = False
                reasons.append(f"Minimum age {rules['age_min']} required")

        if "age_max" in rules:
            # 100 is a safe default - basically "no max age check fails"
            if user_profile.get("age", 100) > rules["age_max"]:
                is_eligible = False
                reasons.append(f"Maximum age {rules['age_max']}")
        
        # Income check
        if "income_max" in rules and rules["income_max"] is not None:
            if user_profile.get("income", 0) > rules["income_max"]:
                is_eligible = False
                reasons.append(f"Income must be below ₹{rules['income_max']}")
        
        # Location check
        if "location_type" in rules:
            user_location = user_profile.get("location_type", "urban")
            if user_location not in rules["location_type"]:
                is_eligible = False
                reasons.append(f"Only for {'/'.join(rules['location_type'])} areas")
        
        # Occupation check
        if "occupation" in rules:
            user_occupation = user_profile.get("occupation", "").lower()
            if user_occupation not in rules["occupation"]:
                is_eligible = False
                reasons.append(f"Only for: {', '.join(rules['occupation'])}")
        
        # Boolean field checks
        bool_fields = ["land_ownership", "has_toilet", "willingness_manual_work", "in_smart_city"]
        for field in bool_fields:
            if field in rules:
                if user_profile.get(field, False) != rules[field]:
                    is_eligible = False
                    if rules[field]:
                        reasons.append(f"{field.replace('_', ' ').title()} required")
                    else:
                        reasons.append(f"Must not have {field.replace('_', ' ')}")
        
        # Add to results
        if is_eligible:
            eligible_schemes.append({
                "policy_id": policy_id,
                "policy_name": policy_data["name"],
                "description": policy_data["description"],
                "benefits": policy_data["benefits"],
                "documents_required": policy_data["documents_required"],
                "application_link": policy_data["application_link"],
                "priority": "HIGH" if policy_id in ["PM-KISAN", "AYUSHMAN-BHARAT", "NREGA"] else "MEDIUM"
            })
        else:
            # TODO: return ineligible list for UI feedback
            # punted for v1 launch, users just want matches
            pass
    
    # Sort by priority
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    eligible_schemes.sort(key=lambda x: priority_order.get(x["priority"], 2))
    
    return eligible_schemes


def get_next_steps(policy_id: str) -> Dict[str, Any]:
    """
    Get detailed application steps for a specific policy.
    
    Args:
        policy_id: Policy identifier
    
    Returns:
        Dict with application steps and timeline
    """
    if policy_id not in ELIGIBILITY_RULES:
        return {
            "error": "Policy not found"
        }
    
    policy_data = ELIGIBILITY_RULES[policy_id]
    
    return {
        "policy_id": policy_id,
        "policy_name": policy_data["name"],
        "documents_required": policy_data["documents_required"],
        "application_link": policy_data["application_link"],
        "steps": [
            f"1. Gather required documents: {', '.join(policy_data['documents_required'])}",
            f"2. Visit application portal: {policy_data['application_link']}",
            "3. Fill out the application form with accurate details",
            "4. Upload scanned copies of required documents",
            "5. Submit application and save acknowledgment number",
            "6. Track application status online using acknowledgment number"
        ],
        "timeline": "Application processing typically takes 15-30 days",
        "helpline": "For assistance, contact the policy helpline or visit nearest Jan Seva Kendra"
    }


def get_policy_details(policy_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full details of a policy.
    
    Args:
        policy_id: Policy identifier
    
    Returns:
        Policy details or None if not found
    """
    if policy_id not in ELIGIBILITY_RULES:
        return None
    
    return {
        "policy_id": policy_id,
        **ELIGIBILITY_RULES[policy_id]
    }
