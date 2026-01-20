# Test queries for evaluation

NREGA_TEST_QUERIES = [
    {
        "query": "What was the original intent of NREGA in 2005?",
        "expected_year": "2005",
        "expected_modality": "temporal",
        "category": "intent"
    },
    {
        "query": "How did MGNREGA change in 2009?",
        "expected_year": "2009", 
        "expected_modality": "temporal",
        "category": "evolution"
    },
    {
        "query": "What operational reforms happened in 2014?",
        "expected_year": "2014",
        "expected_modality": "temporal",
        "category": "reforms"
    },
    {
        "query": "What was NREGA budget allocation in 2020?",
        "expected_year": "2020",
        "expected_modality": "budget",
        "category": "budget"
    },
    {
        'query': 'How much did NREGA spend during COVID-19 in 2020?',
        'expected_year': '2020',
        'expected_modality': 'budget',
        'category': 'budget'
    },
    {
        "query": "What happened to NREGA budget in 2023?",
        "expected_year": "2023",
        "expected_modality": "budget",
        "category": "budget"
    },
    {
        "query": "What was public discourse about NREGA in 2023?",
        "expected_year": "2023",
        "expected_modality": "news",
        "category": "discourse"
    },
    {
        "query": "How did media cover NREGA during pandemic in 2020?",
        "expected_year": "2020",
        "expected_modality": "news",
        "category": "discourse"
    },
    {
        "query": "What was the focus on women participation in 2018?",
        "expected_year": "2018",
        "expected_modality": "temporal",
        "category": "focus"
    },
    {
        "query": "What budget constraints emerged in 2023?",
        "expected_year": "2023",
        "expected_modality": "temporal",
        "category": "constraints"
    }
]

RTI_TEST_QUERIES = [
    {
        "query": "What was the original intent of RTI Act in 2005?",
        "expected_year": "2005",
        "expected_modality": "temporal",
        "category": "intent"
    },
    {
        "query": "What happened to RTI autonomy in 2019?",
        "expected_year": "2019",
        "expected_modality": "temporal",
        "category": "autonomy"
    },
    {
        'query': 'How did Section 8 exemptions debate evolve in 2013?',
        'expected_year': '2013',
        'expected_modality': 'temporal',
        'category': 'exemptions'
    },
    {
        "query": "What was RTI budget allocation in 2019?",
        "expected_year": "2019",
        "expected_modality": "budget",
        "category": "budget"
    },
    {
        "query": "How did digital RTI portal launch in 2023?",
        "expected_year": "2023",
        "expected_modality": "temporal",
        "category": "digital"
    },
    {
        "query": "What was public reaction to 2019 RTI amendment?",
        "expected_year": "2019",
        "expected_modality": "news",
        "category": "discourse"
    },
    {
        "query": "What budget was allocated for digital portal in 2023?",
        "expected_year": "2023",
        "expected_modality": "budget",
        "category": "budget"
    },
    {
        'query': 'How did RTI applications surge in 2008?',
        'expected_year': '2008',
        'expected_modality': 'news',
        'category': 'usage'
    },
    {
        "query": "What was digital transformation push in 2024?",
        "expected_year": "2024",
        "expected_modality": "temporal",
        "category": "digital"
    },
    {
        "query": "How did pandemic affect RTI filings in 2020?",
        "expected_year": "2020",
        "expected_modality": "news",
        "category": "pandemic"
    }
]
DEMO_QUERIES = {
    "NREGA": [
        "What was the original intent of NREGA in 2005?",
        "How did budget change during COVID-19 in 2020?",
        "What happened in 2023?",
        "How has NREGA evolved from 2005 to 2023?",
        "What was public discourse about NREGA during pandemic?"
    ],
    "RTI": [
        "What was RTI Act's transparency vision in 2005?",
        "What happened to autonomy in 2019?",
        "How did digital portal transform RTI in 2023?",
        "What was Section 8 exemptions debate in 2013?",
        "How has RTI budget evolved?"
    ]
}
