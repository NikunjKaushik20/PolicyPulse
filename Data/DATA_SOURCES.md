# PolicyPulse Data Sources
    
## Official Government Data Sources

All policy data in PolicyPulse is sourced from official Indian government portals and databases. This document provides full attribution and source URLs for transparency.

---

## Primary Data Sources

### 1. Open Government Data Platform India (data.gov.in)
- **URL**: https://data.gov.in
- **License**: Open Government License - India
- **Maintained by**: National Informatics Centre (NIC), Ministry of Electronics & IT
- **Datasets Used**:
  - Scheme-wise Budget Allocation and Expenditure (2021-2025)
  - District-wise MGNREGA Data
  - Ministry-wise Annual Reports

### 2. MGNREGA MIS (nrega.nic.in)
- **URL**: https://nrega.nic.in
- **License**: Government of India
- **Maintained by**: Ministry of Rural Development
- **Data Points**:
  - Registered workers (28.10 crore as of 2025)
  - Active workers (12.23 crore)
  - Person-days generated annually
  - Budget allocation and expenditure

### 3. Union Budget Documents (indiabudget.gov.in)
- **URL**: https://www.indiabudget.gov.in
- **License**: Government of India
- **Maintained by**: Ministry of Finance
- **Documents**:
  - Expenditure Budget Volumes
  - Scheme-wise allocations
  - Ministry-wise grants

### 4. Press Information Bureau (pib.gov.in)
- **URL**: https://pib.gov.in
- **License**: Government of India
- **Maintained by**: Ministry of Information & Broadcasting
- **Content**: Official press releases and scheme announcements

### 5. Open Budgets India (openbudgetsindia.org)
- **URL**: https://openbudgetsindia.org
- **Maintained by**: Centre for Budget and Governance Accountability
- **Data**: 20,000+ datasets on government budgets

---

## Data Verification

Each data file in the `/data` directory includes:
1. Source URL or database reference
2. Date of data extraction
3. Official government citation

## API Access

Where API access is available, we use:
- data.gov.in API (requires API key for some datasets)
- Direct CSV/Excel downloads from ministry websites

## Data Update Frequency

- Budget data: Updated annually post-Union Budget
- Scheme statistics: Updated quarterly from ministry MIS
- News data: Updated weekly from PIB releases

---

## Citation Format

When citing PolicyPulse data, please use:
```
Source: [Ministry Name], Government of India
Retrieved from: [Official Portal URL]
Date: [Extraction Date]
```

## Contact

For data verification queries:
- data.gov.in: support@data.gov.in
- Ministry portals: Respective ministry websites

---

*Last Updated: 2026-02-05*
*PolicyPulse - AI for Community Impact*
