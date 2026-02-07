"""
Eligibility Checker - Rule-based matching for government schemes.

Determines user eligibility for various policies based on profile.
Now includes:
- "Why Not" analysis (detailed exclusion reasons)
- Official metadata (Gazette notifications, circular numbers)
- Status tracking (Draft vs Final)
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Enhanced Eligibility Rules with Metadata & Exclusion Logic
# Total: 50 schemes with gazette notifications, authority metadata, and eligibility rules
ELIGIBILITY_RULES = {
    # ============ SCHEME 1-11: Original schemes ============
    "NREGA": {
        "name": "Mahatma Gandhi National Rural Employment Guarantee Act",
        "description": "100 days of guaranteed wage employment for rural households",
        "metadata": {
            "authority": "Ministry of Rural Development",
            "notification_number": "S.O. 323(E)",
            "gazette_url": "https://egazette.nic.in/WriteReadData/2005/E_53_2011_079.pdf",
            "status": "Final",
            "effective_date": "2006-02-02",
            "last_updated": "2024-04-01"
        },
        "rules": {
            "age_min": 18,
            "location_type": ["rural"],
            "willingness_manual_work": True
        },
        "documents_required": ["Job Card", "Aadhaar Card", "Bank Account Details"],
        "application_link": "https://nrega.nic.in/",
        "benefits": "Guaranteed 100 days of wage employment per financial year"
    },
    "PM-KISAN": {
        "name": "Pradhan Mantri Kisan Samman Nidhi",
        "description": "Income support for land-holding farmers",
        "metadata": {
            "authority": "Ministry of Agriculture & Farmers Welfare",
            "notification_number": "No. 1-1/2019-Credit-I",
            "gazette_url": "https://pmkisan.gov.in/Documents/pmkisan_Guidelines.pdf",
            "status": "Final",
            "effective_date": "2019-02-24",
            "last_updated": "2024-02-01"
        },
        "rules": {
            "occupation": ["farmer"],
            "land_ownership": True,
            "category_exclusion": ["institutional_landholder", "incometax_payer", "govt_employee"],
            "exclude_tax_payers": True
        },
        "documents_required": ["Land Ownership Documents (Khasra/Khatauni)", "Aadhaar Card", "Bank Account Details"],
        "application_link": "https://pmkisan.gov.in/",
        "benefits": "₹6000 per year in 3 installments of ₹2000 each"
    },
    "AYUSHMAN-BHARAT": {
        "name": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana",
        "description": "₹5 lakh health insurance coverage per family per year",
        "metadata": {
            "authority": "National Health Authority",
            "notification_number": "S.O. 2070(E)",
            "gazette_url": "https://pmjay.gov.in/sites/default/files/2019-09/Final%20AB-PMJAY%20Operational%20Guidelines.pdf",
            "status": "Final",
            "effective_date": "2018-09-23",
            "last_updated": "2023-10-15"
        },
        "rules": {
            "income_max": 250000,
            "exclude_govt_employee": True
        },
        "documents_required": ["Ration Card", "Aadhaar Card", "Income Certificate (for some states)"],
        "application_link": "https://pmjay.gov.in/",
        "benefits": "Cashless health cover up to ₹5 lakh per family per year"
    },
    "SWACHH-BHARAT": {
        "name": "Swachh Bharat Mission (Gramin)",
        "description": "Incentive for toilet construction",
        "metadata": {
            "authority": "Ministry of Jal Shakti",
            "notification_number": "S.O. 3067(E)",
            "gazette_url": "https://swachhbharatmission.gov.in/sbmcms/writereaddata/images/pdf/Guidelines/Complete-set-guidelines.pdf",
            "status": "Final",
            "effective_date": "2014-10-02",
            "last_updated": "2020-02-01"
        },
        "rules": {
            "has_toilet": False,
            "location_type": ["rural"],
            "category": ["sc", "st", "small_marginal_farmer", "landless_laborer", "physically_handicapped", "women_headed"]
        },
        "documents_required": ["Aadhaar Card", "Bank Account Passbook", "Photograph"],
        "application_link": "https://swachhbharatmission.gov.in/",
        "benefits": "₹12,000 incentive for toilet construction"
    },
    "MAKE-IN-INDIA": {
        "name": "Make in India",
        "description": "Manufacturing and business support initiative",
        "metadata": {
            "authority": "DPIIT, Ministry of Commerce",
            "notification_number": "Press Note No. 2 (2020 Series)",
            "gazette_url": "https://dpiit.gov.in/sites/default/files/pn2_2020.pdf",
            "status": "Active Policy Framework",
            "effective_date": "2014-09-25",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["entrepreneur", "business owner", "manufacturer", "farmer"]
        },
        "documents_required": ["Business Registration", "PAN Card", "GST Registration"],
        "application_link": "https://www.makeinindia.com/",
        "benefits": "Investment facilitation, PLI schemes, ease of doing business"
    },
    "NEP": {
        "name": "National Education Policy 2020",
        "description": "Education reforms and student benefits",
        "metadata": {
            "authority": "Ministry of Education",
            "notification_number": "No. 1-1/2020-IS-3",
            "gazette_url": "https://www.education.gov.in/sites/upload_files/mhrd/files/NEP_Final_English_0.pdf",
            "status": "Final",
            "effective_date": "2020-07-29",
            "last_updated": "2020-07-29"
        },
        "rules": {
            "occupation": ["student", "teacher", "researcher"]
        },
        "documents_required": [],
        "application_link": "https://www.education.gov.in/nep/about-nep",
        "benefits": "Holistic education, credit bank, multiple entry/exit options"
    },
    "SUKANYA": {
        "name": "Sukanya Samriddhi Yojana",
        "description": "Small deposit scheme for the girl child",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "G.S.R. 914(E)",
            "gazette_url": "https://dea.gov.in/sites/default/files/Sukanya%20Samriddhi%20Account%20Scheme%202019.pdf",
            "status": "Final",
            "effective_date": "2015-01-22",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "gender": ["female"],
            "age_max": 10
        },
        "documents_required": ["Birth Certificate of Girl Child", "Identity/Address Proof of Guardian", "Photos"],
        "application_link": "https://www.indiapost.gov.in/Financial/Pages/Content/Sukanya-Samriddhi-Account.aspx",
        "benefits": "High interest rate (approx 8%), tax benefits under 80C"
    },
    "MAHILA-SAMMAN": {
        "name": "Mahila Samman Savings Certificate",
        "description": "Small savings scheme for women and girls",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "G.S.R. 237(E)",
            "gazette_url": "https://egazette.nic.in/WriteReadData/2023/244837.pdf",
            "status": "Final",
            "effective_date": "2023-04-01",
            "last_updated": "2023-03-31"
        },
        "rules": {
            "gender": ["female"]
        },
        "documents_required": ["Aadhaar Card", "PAN Card", "Application Form"],
        "application_link": "https://www.indiapost.gov.in/",
        "benefits": "7.5% fixed interest rate for 2 years"
    },
    "RTI": {
        "name": "Right to Information Act",
        "description": "Right to access information held by public authorities",
        "metadata": {
            "authority": "Ministry of Personnel, Public Grievances and Pensions",
            "notification_number": "Act No. 22 of 2005",
            "gazette_url": "https://rti.gov.in/rti-act.pdf",
            "status": "Final (Amended 2019)",
            "effective_date": "2005-10-12",
            "last_updated": "2019-10-24"
        },
        "rules": {
            "citizenship": "Indian"
        },
        "documents_required": ["Citizenship Proof (optional)", "Application Fee (₹10)"],
        "application_link": "https://rtionline.gov.in/",
        "benefits": "Transparency and accountability in government functioning"
    },
    "DIGITAL-INDIA": {
        "name": "Digital India",
        "description": "Flagship programme to transform India into a digitally empowered society",
        "metadata": {
            "authority": "MeitY",
            "notification_number": "Cabinet Approval 2015",
            "gazette_url": "https://digitalindia.gov.in/",
            "status": "Active Mission",
            "effective_date": "2015-07-01",
            "last_updated": "2024-01-01"
        },
        "rules": {},
        "documents_required": ["Aadhaar"],
        "application_link": "https://digitalindia.gov.in/",
        "benefits": "Digital services, broadband highways, e-governance"
    },
    "SKILL-INDIA": {
        "name": "Skill India (Pradhan Mantri Kaushal Vikas Yojana)",
        "description": "Skill development initiative for youth",
        "metadata": {
            "authority": "MSDE",
            "notification_number": "PMKVY Guidelines 4.0",
            "gazette_url": "https://www.msde.gov.in/sites/default/files/2023-01/PMKVY%204.0%20Guidelines.pdf",
            "status": "Final",
            "effective_date": "2015-07-15",
            "last_updated": "2023-01-01"
        },
        "rules": {
            "age_min": 15,
            "age_max": 45,
            "occupation": ["unemployed", "student", "dropout"]
        },
        "documents_required": ["Aadhaar", "Bank Account"],
        "application_link": "https://www.pmkvyofficial.org/",
        "benefits": "Free short-term training, certification, placement assistance"
    },
    # ============ SCHEME 12-20: Financial Inclusion ============
    "JAN-DHAN": {
        "name": "Pradhan Mantri Jan Dhan Yojana",
        "description": "Financial inclusion program with zero-balance bank accounts",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "F.No. 8/1/2014-BOA",
            "gazette_url": "https://pmjdy.gov.in/files/Guidelines/PMJDY-GuidlinesMar2015.pdf",
            "status": "Final",
            "effective_date": "2014-08-28",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 10
        },
        "documents_required": ["Aadhaar Card", "Passport Size Photo"],
        "application_link": "https://pmjdy.gov.in/",
        "benefits": "Zero-balance account, RuPay debit card, ₹2 lakh accident insurance"
    },
    "MUDRA": {
        "name": "Pradhan Mantri MUDRA Yojana",
        "description": "Micro-enterprise loans up to ₹10 lakh",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "F.No. 2/1/2015-LO",
            "gazette_url": "https://www.mudra.org.in/HomeNew/Files/pdf/MUDRA-YojanaBrochure.pdf",
            "status": "Final",
            "effective_date": "2015-04-08",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["entrepreneur", "business owner", "self-employed", "farmer"],
            "age_min": 18
        },
        "documents_required": ["Aadhaar Card", "PAN Card", "Business Plan", "Address Proof"],
        "application_link": "https://www.mudra.org.in/",
        "benefits": "Collateral-free loans: Shishu (₹50K), Kishore (₹5L), Tarun (₹10L)"
    },
    "STAND-UP-INDIA": {
        "name": "Stand Up India",
        "description": "Loans for SC/ST and women entrepreneurs",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "F.No. 6/2/2016-SCT-II",
            "gazette_url": "https://www.standupmitra.in/Home/SUISchemes",
            "status": "Final",
            "effective_date": "2016-04-05",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 18,
            "occupation": ["entrepreneur", "business owner"],
            "category": ["sc", "st", "female"]
        },
        "documents_required": ["Aadhaar Card", "Caste Certificate/Gender Proof", "Business Plan", "Property Papers"],
        "application_link": "https://www.standupmitra.in/",
        "benefits": "Loans from ₹10 lakh to ₹1 crore for greenfield enterprises"
    },
    "APY": {
        "name": "Atal Pension Yojana",
        "description": "Guaranteed pension scheme for unorganized sector",
        "metadata": {
            "authority": "PFRDA",
            "notification_number": "PFRDA/2015/14/APY",
            "gazette_url": "https://npscra.nsdl.co.in/download/pdf/APY-Scheme-Details.pdf",
            "status": "Final",
            "effective_date": "2015-06-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 18,
            "age_max": 40,
            "exclude_tax_payers": True
        },
        "documents_required": ["Aadhaar Card", "Bank Account"],
        "application_link": "https://npscra.nsdl.co.in/scheme-details.php",
        "benefits": "Guaranteed pension of ₹1000-5000/month after age 60"
    },
    "PMSBY": {
        "name": "Pradhan Mantri Suraksha Bima Yojana",
        "description": "Accidental death and disability insurance",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "F.No. 16/1/2015-INS",
            "gazette_url": "https://financialservices.gov.in/insurance-divisions/Government-Sponsored-Socially-Oriented-Insurance-Schemes/Pradhan-Mantri-Suraksha-Bima-Yojana(PMSBY)",
            "status": "Final",
            "effective_date": "2015-05-09",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 18,
            "age_max": 70
        },
        "documents_required": ["Aadhaar Card", "Bank Account"],
        "application_link": "https://www.jansuraksha.gov.in/",
        "benefits": "₹2 lakh accidental death cover at ₹20/year premium"
    },
    "PMJJBY": {
        "name": "Pradhan Mantri Jeevan Jyoti Bima Yojana",
        "description": "Life insurance coverage for all citizens",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "F.No. 16/2/2015-INS",
            "gazette_url": "https://financialservices.gov.in/insurance-divisions/Government-Sponsored-Socially-Oriented-Insurance-Schemes/Pradhan-Mantri-Jeevan-Jyoti-Bima-Yojana(PMJJBY)",
            "status": "Final",
            "effective_date": "2015-05-09",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 18,
            "age_max": 50
        },
        "documents_required": ["Aadhaar Card", "Bank Account"],
        "application_link": "https://www.jansuraksha.gov.in/",
        "benefits": "₹2 lakh life cover at ₹436/year premium"
    },
    "PPF": {
        "name": "Public Provident Fund",
        "description": "Long-term savings with tax benefits",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "G.S.R. 1136(E)",
            "gazette_url": "https://www.nsiindia.gov.in/InternalPage.aspx?Id_Pk=89",
            "status": "Final",
            "effective_date": "1968-07-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "citizenship": "Indian"
        },
        "documents_required": ["Aadhaar Card", "PAN Card", "Address Proof"],
        "application_link": "https://www.indiapost.gov.in/Financial/Pages/Content/Post-Office-Saving-Schemes.aspx",
        "benefits": "7.1% interest, 15-year lock-in, tax-free returns under 80C"
    },
    "NPS": {
        "name": "National Pension System",
        "description": "Voluntary pension scheme for all citizens",
        "metadata": {
            "authority": "PFRDA",
            "notification_number": "PFRDA/12/RGL/139/9",
            "gazette_url": "https://npscra.nsdl.co.in/scheme-details.php",
            "status": "Final",
            "effective_date": "2009-05-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 18,
            "age_max": 65,
            "citizenship": "Indian"
        },
        "documents_required": ["Aadhaar Card", "PAN Card", "Bank Account"],
        "application_link": "https://npscra.nsdl.co.in/",
        "benefits": "Market-linked pension, tax benefits under 80CCD"
    },
    "SENIOR-CITIZEN-SAVINGS": {
        "name": "Senior Citizens Savings Scheme",
        "description": "High-interest savings for senior citizens",
        "metadata": {
            "authority": "Ministry of Finance",
            "notification_number": "G.S.R. 1136(E)",
            "gazette_url": "https://www.nsiindia.gov.in/InternalPage.aspx?Id_Pk=55",
            "status": "Final",
            "effective_date": "2004-08-02",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 60
        },
        "documents_required": ["Age Proof", "Aadhaar Card", "PAN Card"],
        "application_link": "https://www.indiapost.gov.in/Financial/Pages/Content/Post-Office-Saving-Schemes.aspx",
        "benefits": "8.2% interest, 5-year tenure, tax benefits"
    },
    # ============ SCHEME 21-30: Agriculture ============
    "FASAL-BIMA": {
        "name": "Pradhan Mantri Fasal Bima Yojana",
        "description": "Crop insurance scheme for farmers",
        "metadata": {
            "authority": "Ministry of Agriculture & Farmers Welfare",
            "notification_number": "No. 13015/04/2016-Credit-II",
            "gazette_url": "https://pmfby.gov.in/pdf/Revised_Operational_Guidelines.pdf",
            "status": "Final",
            "effective_date": "2016-02-18",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer"],
            "land_ownership": True
        },
        "documents_required": ["Land Records", "Aadhaar Card", "Bank Account", "Sowing Certificate"],
        "application_link": "https://pmfby.gov.in/",
        "benefits": "Crop insurance with 2% premium for Kharif, 1.5% for Rabi"
    },
    "KCC": {
        "name": "Kisan Credit Card",
        "description": "Credit facility for farmers",
        "metadata": {
            "authority": "NABARD/RBI",
            "notification_number": "RPCD.No.PLFS.BC.28/05.05.09/98-99",
            "gazette_url": "https://www.nabard.org/content1.aspx?id=485&catid=23&mid=530",
            "status": "Final",
            "effective_date": "1998-08-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer"],
            "age_min": 18,
            "age_max": 75
        },
        "documents_required": ["Land Records", "Aadhaar Card", "Passport Photo", "Identity Proof"],
        "application_link": "https://pmkisan.gov.in/",
        "benefits": "Credit up to ₹3 lakh at 4% interest (with subvention)"
    },
    "KUSUM": {
        "name": "PM-KUSUM (Kisan Urja Suraksha evam Utthan Mahabhiyaan)",
        "description": "Solar power for farmers",
        "metadata": {
            "authority": "MNRE",
            "notification_number": "No. 32/6/2017-SPV",
            "gazette_url": "https://mnre.gov.in/img/documents/uploads/file_f-1585710569877.pdf",
            "status": "Final",
            "effective_date": "2019-02-19",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer"],
            "land_ownership": True
        },
        "documents_required": ["Land Records", "Aadhaar Card", "Bank Account"],
        "application_link": "https://pmkusum.mnre.gov.in/",
        "benefits": "60% subsidy on solar pumps, land lease income from solar plants"
    },
    "ENAM": {
        "name": "e-National Agriculture Market",
        "description": "Online trading platform for agricultural commodities",
        "metadata": {
            "authority": "Ministry of Agriculture",
            "notification_number": "No. 1-12/2015-M-III",
            "gazette_url": "https://enam.gov.in/web/stakeholders-Ede/guidelines",
            "status": "Final",
            "effective_date": "2016-04-14",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer", "trader", "business owner"]
        },
        "documents_required": ["Aadhaar Card", "Bank Account", "Mandi License (for traders)"],
        "application_link": "https://enam.gov.in/",
        "benefits": "Pan-India market access, transparent pricing, reduced intermediaries"
    },
    "SOIL-HEALTH-CARD": {
        "name": "Soil Health Card Scheme",
        "description": "Soil testing and health monitoring for farmers",
        "metadata": {
            "authority": "Ministry of Agriculture",
            "notification_number": "No. 9-1/2014-INM",
            "gazette_url": "https://soilhealth.dac.gov.in/",
            "status": "Final",
            "effective_date": "2015-02-19",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer"]
        },
        "documents_required": ["Land Records", "Aadhaar Card"],
        "application_link": "https://soilhealth.dac.gov.in/",
        "benefits": "Free soil testing, fertilizer recommendations, increased yield"
    },
    "PMKSY": {
        "name": "Pradhan Mantri Krishi Sinchayee Yojana",
        "description": "Per drop more crop - irrigation infrastructure",
        "metadata": {
            "authority": "Ministry of Agriculture",
            "notification_number": "No. 1-5/2015-RFS-I",
            "gazette_url": "https://pmksy.gov.in/Guidelines.aspx",
            "status": "Final",
            "effective_date": "2015-07-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer"],
            "land_ownership": True
        },
        "documents_required": ["Land Records", "Aadhaar Card", "Bank Account"],
        "application_link": "https://pmksy.gov.in/",
        "benefits": "Subsidy on micro-irrigation, water harvesting structures"
    },
    "PARAMPARAGAT-KRISHI": {
        "name": "Paramparagat Krishi Vikas Yojana",
        "description": "Organic farming promotion scheme",
        "metadata": {
            "authority": "Ministry of Agriculture",
            "notification_number": "No. 9-7/2015-INM",
            "gazette_url": "https://pgsindia-ncof.gov.in/pkvy/Index.aspx",
            "status": "Final",
            "effective_date": "2015-04-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer"]
        },
        "documents_required": ["Land Records", "Aadhaar Card", "Cluster Registration"],
        "application_link": "https://pgsindia-ncof.gov.in/",
        "benefits": "₹50,000/hectare for 3 years for organic farming adoption"
    },
    "AGRI-CLINICS": {
        "name": "Agri-Clinics and Agri-Business Centres",
        "description": "Entrepreneurship in agriculture",
        "metadata": {
            "authority": "Ministry of Agriculture",
            "notification_number": "No. 11-4/2002-ACD",
            "gazette_url": "https://www.agriclinics.net/",
            "status": "Final",
            "effective_date": "2002-04-09",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["graduate", "student"],
            "age_min": 18
        },
        "documents_required": ["Degree Certificate", "Aadhaar Card", "Business Plan"],
        "application_link": "https://www.agriclinics.net/",
        "benefits": "Training + credit-linked subsidy (44% for general, 36% for others)"
    },
    "KISAN-MAAN-DHAN": {
        "name": "PM Kisan Maan-Dhan Yojana",
        "description": "Pension scheme for small and marginal farmers",
        "metadata": {
            "authority": "Ministry of Agriculture",
            "notification_number": "No. 1-3/2019-P&C",
            "gazette_url": "https://pmkmy.gov.in/",
            "status": "Final",
            "effective_date": "2019-09-12",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["farmer"],
            "age_min": 18,
            "age_max": 40,
            "land_max_hectares": 2
        },
        "documents_required": ["Land Records", "Aadhaar Card", "Bank Account"],
        "application_link": "https://pmkmy.gov.in/",
        "benefits": "₹3000/month pension after age 60"
    },
    # ============ SCHEME 31-40: Housing & Urban ============
    "PMAY-GRAMIN": {
        "name": "Pradhan Mantri Awas Yojana - Gramin",
        "description": "Housing for rural poor",
        "metadata": {
            "authority": "Ministry of Rural Development",
            "notification_number": "No. J-11015/1/2016-RH",
            "gazette_url": "https://pmayg.nic.in/netiayHome/Aborad_eng.aspx",
            "status": "Final",
            "effective_date": "2016-04-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["rural"],
            "income_max": 300000,
            "has_pucca_house": False
        },
        "documents_required": ["Aadhaar Card", "SECC Data Verification", "Bank Account", "Land Documents"],
        "application_link": "https://pmayg.nic.in/",
        "benefits": "₹1.20 lakh (plains), ₹1.30 lakh (hilly) for house construction"
    },
    "PMAY-URBAN": {
        "name": "Pradhan Mantri Awas Yojana - Urban",
        "description": "Affordable housing in urban areas",
        "metadata": {
            "authority": "Ministry of Housing & Urban Affairs",
            "notification_number": "K-14011/04/2015-USAH",
            "gazette_url": "https://pmaymis.gov.in/",
            "status": "Final",
            "effective_date": "2015-06-25",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["urban"],
            "income_max": 1800000,
            "has_pucca_house": False
        },
        "documents_required": ["Aadhaar Card", "Income Certificate", "Bank Account"],
        "application_link": "https://pmaymis.gov.in/",
        "benefits": "Interest subsidy of 3-6.5% on home loans"
    },
    "AMRUT": {
        "name": "Atal Mission for Rejuvenation and Urban Transformation",
        "description": "Urban infrastructure development",
        "metadata": {
            "authority": "Ministry of Housing & Urban Affairs",
            "notification_number": "K-14011/33/2015-AMRUT",
            "gazette_url": "https://amrut.gov.in/",
            "status": "Final",
            "effective_date": "2015-06-25",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["urban"]
        },
        "documents_required": [],
        "application_link": "https://amrut.gov.in/",
        "benefits": "Improved water supply, sewerage, urban transport"
    },
    "SMART-CITIES": {
        "name": "Smart Cities Mission",
        "description": "Urban development through technology",
        "metadata": {
            "authority": "Ministry of Housing & Urban Affairs",
            "notification_number": "K-14011/05/2015-Smart Cities",
            "gazette_url": "https://smartcities.gov.in/",
            "status": "Final",
            "effective_date": "2015-06-25",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["urban"]
        },
        "documents_required": [],
        "application_link": "https://smartcities.gov.in/",
        "benefits": "Smart solutions for urban infrastructure and governance"
    },
    "DAY-NULM": {
        "name": "Deendayal Antyodaya Yojana - National Urban Livelihoods Mission",
        "description": "Urban poverty alleviation and livelihoods",
        "metadata": {
            "authority": "Ministry of Housing & Urban Affairs",
            "notification_number": "K-14012/1/2014-NULM",
            "gazette_url": "https://nulm.gov.in/",
            "status": "Final",
            "effective_date": "2014-09-24",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["urban"],
            "income_max": 300000
        },
        "documents_required": ["Aadhaar Card", "Address Proof", "Bank Account"],
        "application_link": "https://nulm.gov.in/",
        "benefits": "Skill training, self-employment, SHG support"
    },
    "DAY-NRLM": {
        "name": "Deendayal Antyodaya Yojana - National Rural Livelihoods Mission",
        "description": "Rural poverty alleviation through SHGs",
        "metadata": {
            "authority": "Ministry of Rural Development",
            "notification_number": "J-11017/3/2010-NRLM",
            "gazette_url": "https://aajeevika.gov.in/",
            "status": "Final",
            "effective_date": "2011-06-03",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["rural"],
            "gender": ["female"]
        },
        "documents_required": ["Aadhaar Card", "SHG Membership", "Bank Account"],
        "application_link": "https://aajeevika.gov.in/",
        "benefits": "SHG formation support, revolving fund, credit linkage"
    },
    "PMGSY": {
        "name": "Pradhan Mantri Gram Sadak Yojana",
        "description": "Rural road connectivity",
        "metadata": {
            "authority": "Ministry of Rural Development",
            "notification_number": "J-11015/1/2000-RC",
            "gazette_url": "https://pmgsy.nic.in/",
            "status": "Final",
            "effective_date": "2000-12-25",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["rural"]
        },
        "documents_required": [],
        "application_link": "https://pmgsy.nic.in/",
        "benefits": "All-weather road connectivity to unconnected habitations"
    },
    "JJM": {
        "name": "Jal Jeevan Mission",
        "description": "Tap water to every rural household",
        "metadata": {
            "authority": "Ministry of Jal Shakti",
            "notification_number": "W-11011/1/2019-DDWS",
            "gazette_url": "https://jaljeevanmission.gov.in/",
            "status": "Final",
            "effective_date": "2019-08-15",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["rural"]
        },
        "documents_required": [],
        "application_link": "https://jaljeevanmission.gov.in/",
        "benefits": "Functional tap water connection to every rural household"
    },
    "SVAMITVA": {
        "name": "Survey of Villages and Mapping with Improvised Technology",
        "description": "Property cards for rural households",
        "metadata": {
            "authority": "Ministry of Panchayati Raj",
            "notification_number": "N-11012/9/2020-GP-I",
            "gazette_url": "https://svamitva.nic.in/",
            "status": "Final",
            "effective_date": "2020-04-24",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["rural"]
        },
        "documents_required": ["Aadhaar Card", "Existing Property Documents (if any)"],
        "application_link": "https://svamitva.nic.in/",
        "benefits": "Legal property cards enabling bank loans against property"
    },
    "SAUBHAGYA": {
        "name": "Pradhan Mantri Sahaj Bijli Har Ghar Yojana",
        "description": "Universal household electrification",
        "metadata": {
            "authority": "Ministry of Power",
            "notification_number": "No. 46/19/2017-APDRP",
            "gazette_url": "https://saubhagya.gov.in/",
            "status": "Final",
            "effective_date": "2017-09-25",
            "last_updated": "2024-01-01"
        },
        "rules": {},
        "documents_required": ["Aadhaar Card", "Identity Proof"],
        "application_link": "https://saubhagya.gov.in/",
        "benefits": "Free electricity connection (or ₹500 in 10 installments)"
    },
    # ============ SCHEME 41-50: Health, Welfare & Others ============
    "UJJWALA": {
        "name": "Pradhan Mantri Ujjwala Yojana",
        "description": "LPG connections for BPL households",
        "metadata": {
            "authority": "Ministry of Petroleum & Natural Gas",
            "notification_number": "P-24012/4/2016-PP-II",
            "gazette_url": "https://pmuy.gov.in/",
            "status": "Final",
            "effective_date": "2016-05-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "income_max": 200000,
            "gender": ["female"]
        },
        "documents_required": ["Aadhaar Card", "BPL Card/Ration Card", "Bank Account"],
        "application_link": "https://pmuy.gov.in/",
        "benefits": "Free LPG connection with ₹1600 subsidy"
    },
    "PMMVY": {
        "name": "Pradhan Mantri Matru Vandana Yojana",
        "description": "Maternity benefit for pregnant women",
        "metadata": {
            "authority": "Ministry of Women & Child Development",
            "notification_number": "No. 13-4/2017-NM",
            "gazette_url": "https://pmmvy.wcd.gov.in/",
            "status": "Final",
            "effective_date": "2017-01-01",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "gender": ["female"],
            "age_min": 19
        },
        "documents_required": ["Aadhaar Card", "Bank Account", "MCP Card", "Pregnancy Registration"],
        "application_link": "https://pmmvy.wcd.gov.in/",
        "benefits": "₹5000 in 3 installments for first live birth"
    },
    "BETI-BACHAO": {
        "name": "Beti Bachao Beti Padhao",
        "description": "Girl child welfare and education",
        "metadata": {
            "authority": "Ministry of Women & Child Development",
            "notification_number": "No. WD-14/4/2014-WG",
            "gazette_url": "https://wcd.nic.in/bbbp-schemes",
            "status": "Final",
            "effective_date": "2015-01-22",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "gender": ["female"],
            "age_max": 18
        },
        "documents_required": [],
        "application_link": "https://wcd.nic.in/bbbp-schemes",
        "benefits": "Awareness, education support, survival and protection"
    },
    "POSHAN-ABHIYAAN": {
        "name": "POSHAN Abhiyaan (National Nutrition Mission)",
        "description": "Nutrition for children and pregnant women",
        "metadata": {
            "authority": "Ministry of Women & Child Development",
            "notification_number": "No. 5-1/2018-CD-I",
            "gazette_url": "https://poshanabhiyaan.gov.in/",
            "status": "Final",
            "effective_date": "2018-03-08",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_max": 6
        },
        "documents_required": ["Aadhaar Card", "Birth Certificate"],
        "application_link": "https://poshanabhiyaan.gov.in/",
        "benefits": "Supplementary nutrition, growth monitoring, counseling"
    },
    "MISSION-INDRADHANUSH": {
        "name": "Mission Indradhanush",
        "description": "Full immunization for children",
        "metadata": {
            "authority": "Ministry of Health & Family Welfare",
            "notification_number": "Z-28015/153/2014-IMM",
            "gazette_url": "https://main.mohfw.gov.in/sites/default/files/245453521061489663873.pdf",
            "status": "Final",
            "effective_date": "2014-12-25",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_max": 2
        },
        "documents_required": ["Birth Certificate", "Immunization Card"],
        "application_link": "https://main.mohfw.gov.in/",
        "benefits": "Free vaccination against 12 diseases"
    },
    "NSAP": {
        "name": "National Social Assistance Programme",
        "description": "Pensions for elderly, widows, disabled",
        "metadata": {
            "authority": "Ministry of Rural Development",
            "notification_number": "J-11011/5/2007-NSAP",
            "gazette_url": "https://nsap.nic.in/",
            "status": "Final",
            "effective_date": "1995-08-15",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "income_max": 200000,
            "age_min": 60
        },
        "documents_required": ["Aadhaar Card", "Age Proof", "BPL Certificate", "Bank Account"],
        "application_link": "https://nsap.nic.in/",
        "benefits": "₹200-500/month pension (IGNOAPS, IGNWPS, IGNDPS)"
    },
    "STARTUP-INDIA": {
        "name": "Startup India",
        "description": "Support for startups and entrepreneurs",
        "metadata": {
            "authority": "DPIIT",
            "notification_number": "G.S.R. 127(E)",
            "gazette_url": "https://www.startupindia.gov.in/content/dam/invest-india/Templates/public/gazette%20notification.pdf",
            "status": "Final",
            "effective_date": "2016-01-16",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "occupation": ["entrepreneur", "business owner"],
            "age_min": 18
        },
        "documents_required": ["DPIIT Recognition", "PAN Card", "Business Registration"],
        "application_link": "https://www.startupindia.gov.in/",
        "benefits": "Tax exemption, self-certification, fund of funds"
    },
    "PMEGP": {
        "name": "Prime Minister's Employment Generation Programme",
        "description": "Micro-enterprise support with subsidy",
        "metadata": {
            "authority": "KVIC",
            "notification_number": "No. 11/1(2)/2008-PMEGP",
            "gazette_url": "https://www.kviconline.gov.in/pmegp/pmegpweb/index.jsp",
            "status": "Final",
            "effective_date": "2008-08-15",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 18,
            "occupation": ["unemployed", "student"]
        },
        "documents_required": ["Aadhaar Card", "Project Report", "EDP Training Certificate"],
        "application_link": "https://www.kviconline.gov.in/pmegp/pmegpweb/",
        "benefits": "15-35% subsidy on projects up to ₹50 lakh"
    },
    "DDU-GKY": {
        "name": "Deen Dayal Upadhyaya Grameen Kaushalya Yojana",
        "description": "Skill training for rural youth with placement",
        "metadata": {
            "authority": "Ministry of Rural Development",
            "notification_number": "J-11013/4/2014-SGSY",
            "gazette_url": "https://ddugky.gov.in/content/scheme-guidelines",
            "status": "Final",
            "effective_date": "2014-09-25",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "location_type": ["rural"],
            "age_min": 15,
            "age_max": 35,
            "income_max": 300000
        },
        "documents_required": ["Aadhaar Card", "Address Proof", "Bank Account"],
        "application_link": "https://ddugky.gov.in/",
        "benefits": "Free skill training with guaranteed placement (min ₹6000/month)"
    },
    "ONE-NATION-ONE-RATION": {
        "name": "One Nation One Ration Card",
        "description": "Portability of ration card benefits across states",
        "metadata": {
            "authority": "Ministry of Consumer Affairs",
            "notification_number": "No. F.1-19/2019-BP",
            "gazette_url": "https://nfsa.gov.in/portal/onorc",
            "status": "Final",
            "effective_date": "2019-08-09",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "has_ration_card": True
        },
        "documents_required": ["Ration Card", "Aadhaar Card"],
        "application_link": "https://nfsa.gov.in/",
        "benefits": "Access PDS rations from any FPS across India"
    },
    "AGNIVEER": {
        "name": "Agnipath Scheme (Agniveer)",
        "description": "Short-term recruitment in Armed Forces",
        "metadata": {
            "authority": "Ministry of Defence",
            "notification_number": "No. 12(1)/2022/D(GS-II)",
            "gazette_url": "https://agnipathyojna.in/",
            "status": "Final",
            "effective_date": "2022-06-14",
            "last_updated": "2024-01-01"
        },
        "rules": {
            "age_min": 17.5,
            "age_max": 21,
            "citizenship": "Indian"
        },
        "documents_required": ["Aadhaar Card", "10th/12th Marksheet", "Medical Certificate", "Domicile Certificate"],
        "application_link": "https://joinindianarmy.nic.in/",
        "benefits": "4-year service, Seva Nidhi package of ₹11.71 lakh on completion"
    }
}


def check_eligibility(user_profile: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Check which schemes a user is eligible for AND why they are excluded from others.
    
    Args:
        user_profile: Dict with user information.
    
    Returns:
        Dict with 'eligible' and 'excluded' lists, containing policy details and reasons.
    """
    eligible_schemes = []
    excluded_schemes = []
    missing_info = [] # TODO: implement detection of critical missing fields
    
    for policy_id, policy_data in ELIGIBILITY_RULES.items():
        is_eligible = True
        reasons = [] # Reasons for exclusion
        rules = policy_data.get("rules", {})
        
        # --- Check Age ---
        if "age_min" in rules:
            if user_profile.get("age"):
                 if user_profile["age"] < rules["age_min"]:
                    is_eligible = False
                    reasons.append(f"Age {user_profile['age']} is below minimum {rules['age_min']}")
            else:
                # Age not provided, assuming eligible but maybe flag for missing info?
                pass 
                
        if "age_max" in rules:
            if user_profile.get("age"):
                if user_profile["age"] > rules["age_max"]:
                    is_eligible = False
                    reasons.append(f"Age {user_profile['age']} is above maximum {rules['age_max']}")

        # --- Check Gender ---
        if "gender" in rules:
            # If rules['gender'] is a list of allowed genders
            # e.g. ["female"]
            allowed_genders = [g.lower() for g in rules["gender"]]
            user_gender = str(user_profile.get("gender", "")).lower()
            
            if user_gender and user_gender not in allowed_genders:
                is_eligible = False
                reasons.append(f"Scheme is restricted to {', '.join(rules['gender'])} applicants")

        # --- Check Occupation ---
        if "occupation" in rules:
            allowed_occupations = [o.lower() for o in rules["occupation"]]
            user_occupation = str(user_profile.get("occupation", "")).lower()
            
            # Simple keyword matching
            match = False
            if not user_occupation:
                # If user occupation not specified, we can't exclude definitively
                # But strict check would fail. Let's be lenient for demo? 
                # Or excluded with "Occupation verification needed"
                pass 
            else:
                for allowed in allowed_occupations:
                    if allowed in user_occupation:
                        match = True
                        break
                if not match:
                    is_eligible = False
                    reasons.append(f"Occupation '{user_profile.get('occupation')}' not in eligible list: {', '.join(rules['occupation'])}")
        
        # --- Check Location ---
        if "location_type" in rules:
            allowed_locs = [l.lower() for l in rules["location_type"]]
            user_loc = str(user_profile.get("location_type", "")).lower()
            if user_loc and user_loc not in allowed_locs:
                is_eligible = False
                reasons.append(f"Scheme valid for {', '.join(rules['location_type'])} areas only (you are in {user_loc})")

        # --- Check Income ---
        if "income_max" in rules:
            limit = rules["income_max"]
            user_income = user_profile.get("income", 0)
            # 0 might mean "not provided", assume provided for now or default to 0
            if user_income > limit:
                is_eligible = False
                reasons.append(f"Annual income ₹{user_income} exceeds limit of ₹{limit}")
        
        # --- Check Specific Boolean Rules ---
        if "has_toilet" in rules:
            required_state = rules["has_toilet"] # e.g. False (must NOT have toilet)
            user_state = user_profile.get("has_toilet")
            if user_state is not None and user_state != required_state:
                is_eligible = False
                condition = "Must not own a toilet" if not required_state else "Must own a toilet"
                reasons.append(f"Eligibility verification failed: {condition}")

        if "land_ownership" in rules:
            required = rules["land_ownership"]
            user_owns = user_profile.get("land_ownership")
            if user_owns is not None and user_owns != required:
                is_eligible = False
                condition = "Must own land" if required else "Must be landless"
                reasons.append(f"Land ownership criteria not met: {condition}")

        # --- Check Category (Caste/Group) ---
        if "category" in rules:
            # simple allow list
            allowed_cats = [c.lower() for c in rules["category"]]
            user_cat = str(user_profile.get("category", "")).lower()
            if user_cat and user_cat not in allowed_cats:
                 # Check if 'general' is allowed implicitly? usually explicit list means restriction
                 is_eligible = False
                 reasons.append(f"Category '{user_profile.get('category')}' not eligible. Open to: {', '.join(rules['category'])}")
        
        if "category_exclusion" in rules:
             # e.g. exclude 'institutional_landholder'
             # Assuming user profile might have tags or derived attributes
             pass

        # --- Check Tax Payer Status (Proxy for Income sometimes) ---
        if "exclude_tax_payers" in rules and rules["exclude_tax_payers"]:
            # If we knew user was tax payer. 
            # For now, let's assume income > 5L implies tax payer roughly?
            if user_profile.get("income", 0) > 700000: # New regime rebate limit
                 is_eligible = False
                 reasons.append("Income Tax payers are excluded from this scheme")


        result_obj = {
            "id": policy_id,
            "name": policy_data["name"],
            "description": policy_data["description"],
            "metadata": policy_data.get("metadata", {}),
            "benefits": policy_data.get("benefits"),
            "application_link": policy_data.get("application_link"),
            "documents_required": policy_data.get("documents_required", []),
            "reasons": reasons
        }

        if is_eligible:
            eligible_schemes.append(result_obj)
        else:
            excluded_schemes.append(result_obj)
            
    # Sort eligible by priority? (Optional)
    
    return {
        "eligible": eligible_schemes,
        "excluded": excluded_schemes,
        "missing_info": missing_info
    }


def get_next_steps(policy_id: str) -> Dict[str, Any]:
    """
    Get detailed application steps for a specific policy.
    
    Args:
        policy_id: Policy identifier
    
    Returns:
        Dict with application steps and timeline
    """
    policy = ELIGIBILITY_RULES.get(policy_id)
    if not policy:
        return {}
        
    return {
        "policy_name": policy["name"],
        "steps": [
            "Check eligibility criteria (Age, Income, Category)",
            "Gather required documents: " + ", ".join(policy.get("documents_required", [])),
            f"Visit official portal: {policy.get('application_link')}",
            "Fill application form",
            "Submit to local authority or online"
        ],
        "timeline": "Processing typically takes 15-30 days",
        "documents": policy.get("documents_required", [])
    }

def get_policy_details(policy_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full details of a policy.
    
    Args:
        policy_id: Policy identifier
    
    Returns:
        Policy details or None if not found
    """
    return ELIGIBILITY_RULES.get(policy_id)
