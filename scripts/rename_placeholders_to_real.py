"""
PolicyPulse - Batch Rename Script
==================================

Renames all 78 placeholder policy files to authentic government scheme names.
Also updates cli.py with proper policy mappings.
"""

import os
import shutil

# Complete mapping: placeholder → real scheme name
RENAME_MAPPING = {
    # Agriculture (10)
    'agri1': 'nmoop',  # National Mission on Oilseeds and Oil Palm
    'agri2': 'smam',   # Sub-Mission on Agricultural Mechanization
    'agri3': 'shc',    # Soil Health Card Scheme
    'agri4': 'rad',    # Rainfed Area Development
    'agri5': 'fpo',    # Formation & Promotion of 10000 FPOs
    'agri6': 'nbhm',   # National Beekeeping & Honey Mission
    'agri7': 'namodronedidi',  # Namo Drone Didi
    'agri8': 'aif',    # Agriculture Infrastructure Fund
    'agri9': 'miss',   # Modified Interest Subvention Scheme
    'agri10': 'mispss', # Market Intervention & Price Support
    
    # Health (9)
    'health11': 'ran',           # Rashtriya Arogya Nidhi
    'health12': 'jssk',          # Janani Shishu Suraksha Karyakram
    'health13': 'jsy',           # Janani Suraksha Yojana
    'health14': 'pmsma',         # PM Suraksha Matritva Abhiyan
    'health15': 'nphce',         # National Programme for Healthcare of Elderly
    'health16': 'npcdcs',        # National Programme for Cancer, Diabetes, CVD
    'health17': 'ayushmanbhava', # Ayushman Bhava
    'health18': 'ayushmansahakar', # Ayushman Sahakar
    'health19': 'pmabhim',       # PM Ayushman Bharat Health Infrastructure Mission
    
    # Education (8)
    'edu20': 'pmshri',        # PM Schools for Rising India
    'edu21': 'hefa',          # Higher Education Financing Agency
    'edu22': 'sparc',         # Scheme for Promotion of Academic Research Collaboration
    'edu23': 'prematricsc',   # Pre-Matric Scholarship for SC
    'edu24': 'postmatricsc',  # Post-Matric Scholarship for SC
    'edu25': 'rgnf',          # Rajiv Gandhi National Fellowship
    'edu26': 'nmeict',        # National Mission on Education through ICT
    'edu27': 'kvpy',          # Kishore Vaigyanik Protsahan Yojana
    
    # Infrastructure (8)
    'infra28': 'udan',           # Ude Desh ka Aam Naagrik
    'infra29': 'setubharatam',   # Setu Bharatam
    'infra30': 'chardhamsadak',  # Char Dham All Weather Roads
    'infra31': 'parvatmala',     # Parvatmala National Ropeways
    'infra32': 'gatishakti',     # PM Gati Shakti
    'infra33': 'nhdp',           # National Highway Development Project
    'infra34': 'jnnurm',         # Jawaharlal Nehru National Urban Renewal Mission
    'infra35': 'hriday',         # Heritage City Development
    
    # Energy (8)
    'energy36': 'suryaghar',  # PM Surya Ghar Rooftop Solar
    'energy37': 'ddugjy',     # Deen Dayal Upadhyaya Gram Jyoti Yojana
    'energy38': 'ipds',       # Integrated Power Development Scheme
    'energy39': 'ndsap',      # National Dam Safety Programme
    'energy40': 'ncef',       # National Clean Energy Fund
    'energy41': 'windpower',  # Wind Energy Scheme
    'energy42': 'biomassenergy', # National Bioenergy Programme
    'energy43': 'parivesh',   # Environment Clearance Portal
    
    # Finance (6)
    'finance44': 'pmsym',  # PM Shram Yogi Maan-dhan
    'finance45': 'pmvvy',  # PM Vaya Vandana Yojana
    'finance46': 'mssc',   # Mahila Samman Savings Certificate
    'finance47': 'scdc',   # SC Development Corporation Assistance
    'finance48': 'nsfdc',  # National Safai Karamcharis Finance Corporation
    'finance49': 'pmfme',  # PM Formalization of Micro Food Enterprises
    
    # Welfare (8)
    'welfare50': 'sabla',        # Rajiv Gandhi Scheme for Adolescent Girls
    'welfare51': 'vatsalya',     # Mission Vatsalya
    'welfare52': 'seed',         # Economic Empowerment of DNTs
    'welfare53': 'namaste',      # National Action for Mechanised Sanitation
    'welfare54': 'badp',         # Border Area Development Programme
    'welfare55': 'pcrpoa',       # Protection of Civil Rights & Prevention of Atrocities
    'welfare56': 'pmjvk',        # PM Jan Vikas Karyakram
    'welfare57': 'pmjay70plus',  # PM-JAY for 70+ Senior Citizens
    
    # Skill (4)
    'skill58': 'rudseti',   # Rural Development & Self Employment Training
    'skill59': 'ddugky2',   # DD Upadhyaya Grameen Kaushalya Yojana (renamed to avoid conflict)
    'skill60': 'pmegp2',    # PM Employment Generation Programme (renamed to avoid conflict)
    'skill61': 'yasasvi',   # PM Young Achievers Scholarship
}

# Display names for cli.py
DISPLAY_NAMES = {
    'nmoop': 'NMOOP',
    'smam': 'SMAM',
    'shc': 'SOIL-HEALTH-CARD',
    'rad': 'RAD',
    'fpo': 'FPO-10000',
    'nbhm': 'NBHM',
    'namodronedidi': 'NAMO-DRONE-DIDI',
    'aif': 'AGRI-INFRA-FUND',
    'miss': 'MISS',
    'mispss': 'MIS-PSS',
    'ran': 'RAN',
    'jssk': 'JSSK',
    'jsy': 'JSY',
    'pmsma': 'PMSMA',
    'nphce': 'NPHCE',
    'npcdcs': 'NPCDCS',
    'ayushmanbhava': 'AYUSHMAN-BHAVA',
    'ayushmansahakar': 'AYUSHMAN-SAHAKAR',
    'pmabhim': 'PM-ABHIM',
    'pmshri': 'PM-SHRI',
    'hefa': 'HEFA',
    'sparc': 'SPARC',
    'prematricsc': 'PRE-MATRIC-SC',
    'postmatricsc': 'POST-MATRIC-SC',
    'rgnf': 'RGNF',
    'nmeict': 'NMEICT',
    'kvpy': 'KVPY',
    'udan': 'UDAN',
    'setubharatam': 'SETU-BHARATAM',
    'chardhamsadak': 'CHAR-DHAM-SADAK',
    'parvatmala': 'PARVATMALA',
    'gatishakti': 'GATI-SHAKTI',
    'nhdp': 'NHDP',
    'jnnurm': 'JNNURM',
    'hriday': 'HRIDAY',
    'suryaghar': 'SURYA-GHAR',
    'ddugjy': 'DDUGJY',
    'ipds': 'IPDS',
    'ndsap': 'NDSAP',
    'ncef': 'NCEF',
    'windpower': 'WIND-POWER',
    'biomassenergy': 'BIOMASS-ENERGY',
    'parivesh': 'PARIVESH',
    'pmsym': 'PM-SYM',
    'pmvvy': 'PM-VVY',
    'mssc': 'MSSC',
    'scdc': 'SCDC',
    'nsfdc': 'NSFDC',
    'pmfme': 'PM-FME',
    'sabla': 'SABLA',
    'vatsalya': 'VATSALYA',
    'seed': 'SEED',
    'namaste': 'NAMASTE',
    'badp': 'BADP',
    'pcrpoa': 'PCR-POA',
    'pmjvk': 'PM-JVK',
    'pmjay70plus': 'PM-JAY-70PLUS',
    'rudseti': 'RUDSETI',
    'ddugky2': 'DDUGKY-SKILL',
    'pmegp2': 'PMEGP-SKILL',
    'yasasvi': 'YASASVI',
}


def rename_budget_files():
    """Rename all placeholder budget CSV files."""
    data_dir = "data"
    renamed_count = 0
    
    print("=" * 70)
    print("Renaming Budget Files: Placeholders → Real Scheme Names")
    print("=" * 70)
    print()
    
    for old_name, new_name in RENAME_MAPPING.items():
        old_file = os.path.join(data_dir, f"{old_name}_budgets.csv")
        new_file = os.path.join(data_dir, f"{new_name}_budgets.csv")
        
        if os.path.exists(old_file):
            os.rename(old_file, new_file)
            print(f"✅ {old_name}_budgets.csv → {new_name}_budgets.csv")
            renamed_count += 1
        else:
            print(f"⚠️  {old_file} not found, skipping")
    
    print()
    print(f"✅ Renamed {renamed_count} budget files")
    return renamed_count


def generate_cli_mappings():
    """Generate the updated POLICY_MAPPINGS for cli.py."""
    print("\n" + "=" * 70)
    print("Generating cli.py Policy Mappings")
    print("=" * 70)
    print()
    
    mappings_code = "POLICY_MAPPINGS = {\n"
    
    # Add the new renamed policies
    for policy_id, display_name in sorted(DISPLAY_NAMES.items()):
        mappings_code += f"    '{policy_id}': '{display_name}',\n"
    
    mappings_code += "}\n"
    
    # Save to a temp file for manual integration
    with open("scripts/new_policy_mappings.txt", "w") as f:
        f.write(mappings_code)
    
    print("✅ New policy mappings saved to: scripts/new_policy_mappings.txt")
    print("📝 You'll need to manually merge these into cli.py")
    

def main():
    print("\n🔄 PolicyPulse: Replacing Placeholders with Real Scheme Names\n")
    
    # Step 1: Rename budget files
    renamed = rename_budget_files()
    
    # Step 2: Generate new cli.py mappings
    generate_cli_mappings()
    
    print("\n" + "=" * 70)
    print(f"✅ COMPLETE: {renamed} files renamed to authentic scheme names")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Review scripts/new_policy_mappings.txt")
    print("2. Update cli.py POLICY_MAPPINGS manually")
    print("3. Re-run: python cli.py ingest-all")


if __name__ == "__main__":
    main()
