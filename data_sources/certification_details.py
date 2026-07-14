"""
Mock certification process data: cost, timeline, validity, and
application steps per certification. Stand-in for real data (issuing
body websites, accreditation directories) until integrated.

Distinct in purpose from capability_requirements.py: that file answers
"which certifications does this market require" (used by the
Capability Gap Agent to assess readiness gaps). This file answers "how
does an SME actually obtain a given certification" (cost/timeline/
process) -- a different question, owned by the Certification Agent.
"""

_CERTIFICATION_DETAILS = {
    "ISO 9001 (quality management)": {
        "issuing_body": "Accredited certification bodies (e.g. BSI, SGS, TUV)",
        "typical_cost_usd": (1500, 4000),
        "typical_timeline_weeks": (8, 16),
        "validity_years": 3,
        "application_steps": [
            "Gap analysis against ISO 9001 requirements",
            "Implement/document quality management system",
            "Internal audit",
            "Stage 1 certification audit (documentation review)",
            "Stage 2 certification audit (implementation review)",
            "Certification issued, subject to annual surveillance audits",
        ],
    },
    "OEKO-TEX Standard 100": {
        "issuing_body": "OEKO-TEX accredited test institutes",
        "typical_cost_usd": (800, 2500),
        "typical_timeline_weeks": (4, 8),
        "validity_years": 1,
        "application_steps": [
            "Submit product samples for lab testing",
            "Testing for restricted substances per OEKO-TEX limits",
            "Certificate issued if all tests pass",
            "Annual renewal with re-testing",
        ],
    },
    "BSCI Social Compliance": {
        "issuing_body": "amfori (BSCI program owner) via accredited auditors",
        "typical_cost_usd": (1000, 3000),
        "typical_timeline_weeks": (6, 12),
        "validity_years": 2,
        "application_steps": [
            "Register on amfori platform",
            "Schedule on-site social compliance audit",
            "Address any non-conformities identified",
            "Follow-up audit if required",
            "Rating issued (A-E scale)",
        ],
    },
    "EU REACH chemical compliance": {
        "issuing_body": "Self-declared, verified via testing labs; enforced by EU authorities",
        "typical_cost_usd": (500, 2000),
        "typical_timeline_weeks": (2, 6),
        "validity_years": None,
        "application_steps": [
            "Identify substances of concern in the product",
            "Lab testing to confirm compliance with REACH restricted substance limits",
            "Prepare technical documentation for EU customs/buyers on request",
        ],
    },
    "Udyam Registration": {
        "issuing_body": "Ministry of MSME, Government of India",
        "typical_cost_usd": (0, 0),
        "typical_timeline_weeks": (0, 1),
        "validity_years": None,
        "application_steps": [
            "Register online via the Udyam Registration portal (free, self-certified)",
            "Provide Aadhaar and business PAN details",
            "Registration certificate issued immediately upon submission",
        ],
    },
}

_DEFAULT_DETAIL = {
    "issuing_body": "Varies by certification -- verify with the relevant standards body",
    "typical_cost_usd": (500, 3000),
    "typical_timeline_weeks": (4, 12),
    "validity_years": None,
    "application_steps": [
        "No detailed process data on file for this certification",
        "Contact the issuing body or an accredited consultant for exact steps",
    ],
}


def get_certification_details(name: str) -> dict:
    return _CERTIFICATION_DETAILS.get(name, _DEFAULT_DETAIL)
