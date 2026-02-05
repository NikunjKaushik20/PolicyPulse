"""
Policy Application URLs - Official government portal links.

Centralized mapping of policy IDs to their official application websites.
"""

# Official application portals for all major government schemes
POLICY_APPLICATION_URLS = {
    # Core 10 policies
    "NREGA": "https://nrega.nic.in/",
    "RTI": "https://rtionline.gov.in/",
    "PM-KISAN": "https://pmkisan.gov.in/",
    "AYUSHMAN-BHARAT": "https://pmjay.gov.in/",
    "SWACHH-BHARAT": "https://swachhbharatmission.gov.in/",
    "DIGITAL-INDIA": "https://www.digitalindia.gov.in/",
    "SKILL-INDIA": "https://www.skillindia.gov.in/",
    "MAKE-IN-INDIA": "https://www.makeinindia.com/",
    "SMART-CITIES": "http://smartcities.gov.in/",
    "NEP": "https://www.education.gov.in/nep",
    
    # Batch 2: Financial inclusion & welfare
    "UJJWALA": "https://www.pmuy.gov.in/",
    "JAN-DHAN": "https://www.pmjdy.gov.in/",
    "MUDRA": "https://www.mudra.org.in/",
    "JAL-JEEVAN": "https://jjm.gov.in/",
    "STARTUP-INDIA": "https://www.startupindia.gov.in/",
    "FASAL-BIMA": "https://pmfby.gov.in/",
    "ATAL-PENSION": "https://www.npscra.nsdl.co.in/apy.php",
    "BETI-BACHAO": "https://wcd.nic.in/bbbp-schemes",
    "SAUBHAGYA": "https://saubhagya.gov.in/",
    "PMAY": "https://pmaymis.gov.in/",
    
    # Batch 3: Additional welfare
    "STANDUP-INDIA": "https://www.standupmitra.in/",
    "SUKANYA": "https://www.nsiindia.gov.in/InternalPage.aspx?Id_Pk=69",
    "KCC": "https://www.india.gov.in/spotlight/kisan-credit-card-kcc-scheme",
    "GRAM-SADAK": "https://omms.nic.in/",
    "POSHAN": "https://poshanabhiyaan.gov.in/",
    "AMRUT": "https://amrut.gov.in/",
    "SVANIDHI": "https://pmsvanidhi.mohua.gov.in/",
    "INDRADHANUSH": "https://www.nhp.gov.in/mission-indradhanush",
    "ONORC": "https://www.nfsa.gov.in/portal/onorc-section",
    "VISHWAKARMA": "https://pmvishwakarma.gov.in/",
    
    # Batch 4: Infrastructure & energy
    "KUSUM": "https://pmkusum.mnre.gov.in/",
    "PM-EGPS": "https://www.kviconline.gov.in/pmegpeportal/",
    "NHM": "https://nhm.gov.in/",
    "SAMAGRA-SHIKSHA": "https://samagra.education.gov.in/",
    "ENAM": "https://www.enam.gov.in/",
    "MATSYA": "https://dof.gov.in/pmmsy",
    "UDAY": "https://www.uday.gov.in/",
    "NULM": "https://mohua.gov.in/cms/national-urban-livelihood-mission.php",
    "DDUGKY": "https://ddugky.gov.in/",
    "DEVINE": "https://tribal.nic.in/",
    
    # Agriculture schemes
    "RKVY": "https://rkvy.nic.in/",
    "PARAMPARAGAT": "https://pgsindia-ncof.gov.in/",
    "RASHTRIYA-GOKUL": "https://dahd.nic.in/schemes/programmes/rashtriya-gokul-mission",
    "NFSM": "https://nfsm.gov.in/",
    "HORTI": "https://midh.gov.in/",
    "SOIL-HEALTH": "https://soilhealth.dac.gov.in/",
    "KRISHI": "https://www.india.gov.in/",
    "KISAN-RATH": "https://www.india.gov.in/",
    "NMOOP": "https://nmoop.gov.in/",
    "SMAM": "https://agrimachinery.nic.in/",
    "SOIL-HEALTH-CARD": "https://soilhealth.dac.gov.in/",
    "RAD": "https://rkvy.nic.in/",
    "FPO-10000": "https://www.nafed-india.com/",
    "NAMO-DRONE-DIDI": "https://www.india.gov.in/",
    "AGRI-INFRA-FUND": "https://www.agriinfra.dac.gov.in/",
    
    # Health schemes
    "JAN-AUSHADHI": "https://janaushadhi.gov.in/",
    "RBSK": "https://nhm.gov.in/index1.php?lang=1&level=2&sublinkid=969&lid=557",
    "NMHP": "https://nhm.gov.in/",
    "NTEP": "https://tbcindia.gov.in/",
    "ASHA": "https://nhm.gov.in/index1.php?lang=1&level=1&sublinkid=150&lid=226",
    "JSY": "https://nhm.gov.in/index1.php?lang=1&level=3&sublinkid=841&lid=309",
    "PMSMA": "https://nhm.gov.in/",
    
    # Education schemes
    "RUSA": "https://rusa.nic.in/",
    "SWAYAM": "https://swayam.gov.in/",
    "NSS": "https://nss.gov.in/",
    "NMMS": "https://scholarships.gov.in/",
    "KHELO": "https://yas.nic.in/sports/khelo-india-programme",
    "DIKSHA": "https://diksha.gov.in/",
    "PM-SHRI": "https://www.education.gov.in/",
    
    # Infrastructure schemes
    "BHARATMALA": "https://www.india.gov.in/",
    "SAGARMALA": "http://sagarmala.gov.in/",
    "NAMAMI-GANGE": "https://nmcg.nic.in/",
    "AMRUT-2": "https://amrut.gov.in/",
    "BHARATNET": "https://www.bbnl.nic.in/",
    "UDAN": "https://www.udan.gov.in/",
    "GATI-SHAKTI": "https://www.pmindia.gov.in/en/major_initiatives/pm-gati-shakti/",
    
    # Energy schemes
    "SOLAR-PARK": "https://solarparks.gov.in/",
    "UJALA": "https://www.ujala.gov.in/",
    "FAME": "https://fame2.heavyindustries.gov.in/",
    "SURYA-GHAR": "https://www.india.gov.in/",
    
    # Finance schemes
    "PMJJBY": "https://www.jansuraksha.gov.in/",
    "PMSBY": "https://www.jansuraksha.gov.in/",
    "PM-SYM": "https://maandhan.in/",
    "PM-VVY": "https://www.licindia.in/Products/Pension-Plans/Varishtha-Pension-Bima-Yojana",
    "PM-FME": "https://www.pmfme.mofpi.gov.in/",
    
    # Welfare schemes
    "NSAP": "https://nsap.nic.in/",
    "SABLA": "https://wcd.nic.in/schemes/rajiv-gandhi-scheme-empowerment-adolescent-girls-sabla",
    "VATSALYA": "https://wcd.nic.in/",
    "NAMASTE": "https://www.india.gov.in/",
    "PM-JAY-70PLUS": "https://pmjay.gov.in/",
    
    # Skill schemes
    "APPRENTICE": "https://apprenticeshipindia.gov.in/",
    "YASASVI": "https://www.nta.ac.in/",
}


def get_application_url(policy_id: str) -> str:
    """
    Get the official application URL for a policy.
    
    Args:
        policy_id: Policy identifier (e.g., 'NREGA', 'PM-KISAN')
    
    Returns:
        Official application URL or generic government portal if not found
    """
    return POLICY_APPLICATION_URLS.get(
        policy_id,
        "https://www.india.gov.in/"  # Fallback to India.gov.in
    )


def get_policy_info_with_url(policy_id: str) -> dict:
    """
    Get policy information including application URL.
    
    Args:
        policy_id: Policy identifier
    
    Returns:
        Dict with policy_id and application_url
    """
    return {
        "policy_id": policy_id,
        "application_url": get_application_url(policy_id)
    }
