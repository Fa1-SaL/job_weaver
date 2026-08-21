# -*- coding: utf-8 -*-
"""
Verification script to validate:
1. Turing formatting (email & JD/InMail) against PDF specifications
2. Hyperlink blue styling (color: #0066cc) across formatters and CSS rules
3. Domain Pages negative prompt & organization scrubbing:
   - ZERO occurrence of Mercor/Cincinnatus/URLs in JDs (format_jd)
   - Mercor CAN be mentioned on InMails (format_email)
   - Crossing Hurdles is ONLY mentioned on Crossing Hurdles domain page itself
"""

import os
import json
import re
import sys
from pathlib import Path

# Set standard output to UTF-8 for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from formatters import get_formatter
from formatters.domainPagesFormatter import scrub_all_client_orgs_from_jd
from clients import DOMAIN_PAGE_KEYS, SUPPORTED_CLIENTS
import llm_jd_parser as parser
from llm_jd_parser import (
    VALID_JOB_FUNCTIONS,
    clean_category_list,
    clean_experience_phrases,
    clean_titles,
    extract_raw_role,
    normalize_compensation,
    normalize_data,
    normalize_requirements,
    validate_raw_schema,
)
from policy_utils import is_age_eligibility, is_geography_constraint

def test_turing_formatter():
    fmt = get_formatter("turing")
    data = {
        "role": "LLM - Business Analyst",
        "type": "Short-Term Contract (3-4 Weeks)",
        "pay": "$17 per hour",
        "location": "Remote",
        "commitment": "Flexible 40 hrs/week with a minimum 4-hour overlap with PST",
        "start_date": "Immediate",
        "link": "https://example.com/apply",
        "where_you_will": "help train and evaluate cutting-edge AI systems using board game, strategy, and game mechanics reasoning tasks",
        "client": "Turing",
        "client_desc": "Turing is the world's leading research accelerator for frontier AI labs and a trusted partner for global enterprises deploying advanced AI systems.",
        "role_overview": "We are seeking detail-oriented Business Analysts to help train and evaluate next-generation AI models.",
        "role_responsibilities": [
            "Review, classify, label, and validate data according to detailed project guidelines.",
            "Evaluate AI-generated outputs for accuracy, consistency, completeness, and adherence to project standards."
        ],
        "requirements": [
            "Professionals with 2+ years of experience in Business Analysis, Data Analysis, Quality Assurance, Data Annotation, Content Review, Operations, or related fields.",
            "Strong analytical and problem-solving skills with excellent attention to detail."
        ],
        "preferred_qualifications": [
            "Prior experience in data annotation, content moderation, content review, quality assurance, or AI data labeling."
        ]
    }
    
    email = fmt.format_email(data)
    jd = fmt.format_jd(data)
    
    assert "Referral Partner:" in email and "Crossing Hurdles" in email
    assert "Work Schedule:" in email
    assert "Start Date:" in email and "Immediate" in email
    assert "What You'll Work On:" in email
    assert "Who This Is For:" in email
    assert "Preferred Qualifications:" in email
    assert "Assessment Process" in email
    assert 'style="color: #0066cc;' in email
    assert 'Take Steps to Boost Your Profile:' in email
    
    assert "Position:" in jd and "LLM - Business Analyst" in jd
    assert "Role Responsibilities:" in jd
    assert "#LI-CH" in jd
    
    print("[SUCCESS] Turing Formatter verification passed!")

def test_domain_pages_rules():
    dirty_data = {
        "role": "Internal Medicine Expert at Mercor",
        "type": "Contract at Mercor platform",
        "pay": "$130–$180 per hour",
        "location": "Remote",
        "commitment": "10-20 hrs/week",
        "link": "https://work.mercor.com/explore?listingId=12345",
        "role_overview": "Mercor is hiring experienced domain experts to contribute to Cincinnatus AI reasoning projects on Mercor's platform. Posted by Mercor. mercor.com.",
        "role_responsibilities": [
            "Design realistic prompts for Mercor's AI projects",
            "Evaluate AI-generated responses for Mercor client"
        ],
        "requirements": [
            "Prior experience working on Mercor tasks",
            "Strong clinical reasoning background"
        ]
    }
    
    for dp_key in DOMAIN_PAGE_KEYS:
        fmt = get_formatter(dp_key)
        email = fmt.format_email(dirty_data)
        raw_jd = fmt.format_jd(dirty_data)
        jd = scrub_all_client_orgs_from_jd(raw_jd)
        
        # 1. Hyperlink blue styling
        assert 'color: #0066cc' in email, f"[{dp_key}] Email links must be styled in blue (#0066cc)"
        
        # 2. Mercor MUST NOT be in JD (format_jd) under any circumstance
        assert "Mercor" not in jd, f"[{dp_key}] JD contains 'Mercor':\n{jd}"
        assert "mercor" not in jd.lower(), f"[{dp_key}] JD lower contains 'mercor':\n{jd}"
        assert "Cincinnatus" not in jd, f"[{dp_key}] JD contains 'Cincinnatus':\n{jd}"
        
        # Mercor CAN be in InMail (format_email)
        assert "Mercor" in email, f"[{dp_key}] InMail can mention 'Mercor'!"
        
        # 3. Crossing Hurdles MUST NOT be mentioned on non-Crossing Hurdles domain pages
        if dp_key != "crossing_hurdles":
            assert "Crossing Hurdles" not in email, f"[{dp_key}] Email must NOT mention Crossing Hurdles!"
            assert "Crossing Hurdles" not in jd, f"[{dp_key}] JD must NOT mention Crossing Hurdles!"
            assert "crossinghurdles" not in email.lower(), f"[{dp_key}] Email must NOT mention crossinghurdles!"
            assert "crossinghurdles" not in jd.lower(), f"[{dp_key}] JD must NOT mention crossinghurdles!"
        else:
            assert "Crossing Hurdles" in email, "[crossing_hurdles] Email should mention Crossing Hurdles!"

    print("[SUCCESS] All 8 Domain Pages rule verification passed!")

def test_reported_regressions():
    reported_requirement = (
        "Currently pursuing or recently completed Masters studies, or have "
        "2-3 years of relevant experience."
    )
    expected_requirement = (
        "Currently pursuing or recently completed Masters studies, and have "
        "strong relevant experience."
    )

    assert clean_experience_phrases(reported_requirement) == expected_requirement
    assert normalize_requirements([reported_requirement]) == [expected_requirement]

    experience_variants = [
        "Candidates need 2+ years of professional experience.",
        "Candidates need 2–3 years of industry experience.",
        "Candidates need 2—3 yrs. of hands-on experience.",
        "Candidates need 2 yrs. experience.",
        "Candidates need 2 years of hands-on machine learning experience.",
        "Candidates need between 2 and 3 years of relevant experience.",
        "Candidates need at least 2 years of work experience.",
        "Candidates need two years of relevant experience.",
        "Candidates need a minimum of three yrs. professional experience.",
        "Candidates need 2-year relevant experience.",
        "Candidates need a 3-year professional background.",
    ]
    for requirement in experience_variants:
        cleaned = clean_experience_phrases(requirement)
        assert cleaned == "Candidates need strong relevant experience.", cleaned

    age_requirement = "Candidates must be at least 21 years old."
    assert clean_experience_phrases(age_requirement) == age_requirement

    unrelated_sentences = "The degree takes 4 years. Prior research experience is preferred."
    assert clean_experience_phrases(unrelated_sentences) == unrelated_sentences

    age_with_experience = "Candidates must be at least 21 years of age and have relevant work experience."
    assert clean_experience_phrases(age_with_experience) == age_with_experience

    education_with_experience = "Requires 4 years of college or equivalent work experience."
    assert clean_experience_phrases(education_with_experience) == education_with_experience

    training_with_experience = "Requires 4 years of supervised training with practical work experience."
    assert clean_experience_phrases(training_with_experience) == training_with_experience

    residency_with_experience = "Candidates need 3 years of residency with clinical experience."
    assert clean_experience_phrases(residency_with_experience) == residency_with_experience

    contract_duration = "The contract lasts two years."
    assert clean_experience_phrases(contract_duration) == contract_duration

    assert clean_experience_phrases("At least 3 years working with Python.") == (
        "Strong relevant experience working with Python."
    )
    assert clean_experience_phrases("Minimum experience of 2 years in Python.") == (
        "Strong relevant experience in Python."
    )
    assert clean_experience_phrases("Experience: 2+ years.") == "Strong relevant experience."
    assert clean_experience_phrases("Experience required: 3 years.") == "Strong relevant experience."
    assert clean_experience_phrases("Professional experience of no less than 3 years.") == (
        "Strong relevant experience."
    )
    assert clean_experience_phrases("Worked in finance for 2 years.") == (
        "Strong relevant experience in finance."
    )
    assert clean_experience_phrases("Candidates must have worked in finance for two years.") == (
        "Candidates must have strong relevant experience in finance."
    )
    assert clean_experience_phrases("Must have been an analyst for 2 years.") == (
        "Must have strong relevant experience."
    )
    assert clean_experience_phrases("Two years of professional background.") == (
        "Strong relevant experience."
    )
    assert clean_experience_phrases("At least 2 years of industry expertise.") == (
        "Strong relevant experience."
    )
    assert clean_experience_phrases("Two years of hands-on work in Python.") == (
        "Strong relevant experience in Python."
    )
    assert clean_experience_phrases("2-year relevant experience.") == "Strong relevant experience."
    assert clean_experience_phrases("three-year professional background.") == "Strong relevant experience."

    alternative_requirement = "Candidates may hold a degree, or have 2 years of relevant experience."
    assert clean_experience_phrases(alternative_requirement) == (
        "Candidates may hold a degree, or have strong relevant experience."
    )

    duration_non_requirements = [
        "We spent 2 years developing the platform.",
        "The product remained 4 years in development.",
        "The project ran for 2 years with a global team.",
        "We have worked on the product for 2 years.",
    ]
    for statement in duration_non_requirements:
        assert clean_experience_phrases(statement) == statement

    stemsync_jd = get_formatter("stemsyncai").format_jd({
        "role": "Physics Researcher",
        "type": "Hourly Contract",
        "pay": "$25 per hour",
        "location": "Remote",
        "commitment": "10 hours/week",
        "requirements": [
            expected_requirement,
            "Candidates must be located in Canada.",
            "Strong scientific writing skills."
        ]
    })
    assert "$25 per hour" in stemsync_jd
    assert "$80–$135" not in stemsync_jd
    assert "Stripe" not in stemsync_jd and "Wise" not in stemsync_jd
    assert expected_requirement in stemsync_jd
    assert "Canada" not in stemsync_jd

    print("[SUCCESS] Reported STEMSyncAI regressions passed!")


def _base_formatter_data(**overrides):
    data = {
        "role": "Data Analyst",
        "type": "Contract",
        "pay": "",
        "location": "Onsite",
        "commitment": "",
        "link": "",
        "role_overview": "Review analytical work accurately.",
        "where_you_will": "evaluate analytical outputs",
        "who_this_is_for": "Professionals with strong analytical skills.",
        "client": "Example Client",
        "client_desc": "An example organization.",
        "role_responsibilities": ["Review analytical outputs."],
        "requirements": ["Strong analytical skills."],
        "preferred_qualifications": [],
        "start_date": "",
    }
    data.update(overrides)
    return data


def test_policy_enforcement_and_preservation():
    age_constraints = [
        "Applicants must be 18+.",
        "Candidates must be at least 21 years old.",
        "Applicants must be over 18.",
        "Applicants 18+.",
        "Applicants must be between 18 and 65 years old.",
        "Minimum age: 18.",
        "Applicants must be 18 or above.",
        "Applicants must be 21 and older.",
        "You must be over the age of 18.",
        "Age requirement: 18+.",
        "Applicants under 65 only.",
        "Applicants must be 18 or over.",
        "Candidates 21 and over only.",
        "Adults only.",
        "Applicants must be adults.",
        "Must be of legal age.",
    ]
    geography_constraints = [
        "Candidates must be located in India.",
        "Applicants must currently be based in Australia.",
        "Only candidates from New York may apply.",
        "Open to applicants from the US.",
        "Candidates must reside in Canada.",
        "Applicants based in the UK only.",
        "Must work from India.",
        "Required to work from Australia.",
        "Candidates need to be in India.",
        "Remote within the US.",
        "This role is open only in Germany.",
        "Work must be performed in India.",
        "Must be in the PST time zone.",
        "Applicants must have a work permit.",
    ]
    preserved_requirements = [
        "Candidates need at least 3 years of relevant experience.",
        "Strong knowledge of US GAAP.",
        "Experience integrating Visa APIs.",
        "Build SDKs native to iOS.",
        "We invite you to join us.",
    ]
    preserved_domain_content = [
        "The product is 20 years old.",
        "Analyze outcomes for patients aged 18+.",
        "Support users aged 21 and older.",
        "Candidates must analyze patients aged 65 or older.",
        "Advise clients on citizenship and H-1B petitions.",
        "Review work permit applications for clients.",
        "Analyze visa sponsorship policies for employers.",
        "Analyze outcomes among US residents.",
        "Study residents of long-term care facilities.",
        "Compare citizens of India and Canada in the dataset.",
    ]

    assert all(is_age_eligibility(item) for item in age_constraints)
    assert all(is_geography_constraint(item) for item in geography_constraints)
    assert not any(is_age_eligibility(item) for item in preserved_requirements)
    assert not any(is_geography_constraint(item) for item in preserved_requirements)
    assert not any(is_age_eligibility(item) for item in preserved_domain_content)
    assert not any(is_geography_constraint(item) for item in preserved_domain_content)

    normalized = normalize_data(
        _base_formatter_data(
            commitment="40 hours/week",
            requirements=(
                age_constraints
                + geography_constraints
                + preserved_requirements
                + preserved_domain_content
            ),
            preferred_qualifications=[
                "Must be located in India.",
                "Experience integrating Visa APIs.",
            ],
            role_overview=(
                "This role requires 7 years of relevant experience. "
                "Join us to apply US GAAP when reviewing records. "
                "Candidates must be based in Australia."
            ),
            who_this_is_for=(
                "Professionals who can analyze complex financial records accurately. "
                "Applicants must reside in Canada."
            ),
        ),
        "mercor",
    )

    joined_requirements = " ".join(normalized["requirements"])
    assert normalized["location"] == "Remote"
    assert normalized["commitment"] == "10-40 hrs/week"
    assert "strong relevant experience" in joined_requirements.lower()
    assert "US GAAP" in joined_requirements
    assert "Visa APIs" in joined_requirements
    assert "native to iOS" in joined_requirements
    assert "join us" in joined_requirements
    for preserved_phrase in (
        "product is 20 years old",
        "patients aged 18+",
        "users aged 21 and older",
        "patients aged 65 or older",
        "citizenship and H-1B petitions",
        "work permit applications",
        "visa sponsorship policies",
        "US residents",
        "residents of long-term care facilities",
        "citizens of India and Canada",
    ):
        assert preserved_phrase.lower() in joined_requirements.lower()
    for prohibited_fragment in (
        "located in India",
        "based in Australia",
        "candidates from New York",
        "applicants from the US",
        "reside in Canada",
        "based in the UK only",
        "work from India",
        "work from Australia",
        "open only in Germany",
        "PST time zone",
    ):
        assert prohibited_fragment.lower() not in joined_requirements.lower()
    for prohibited_age_fragment in (
        "Applicants must be 18+",
        "Candidates must be at least 21 years old",
        "Applicants must be over 18",
        "Candidates 21 and over only",
        "Adults only",
        "legal age",
    ):
        assert prohibited_age_fragment.lower() not in joined_requirements.lower()
    assert normalized["preferred_qualifications"] == ["Experience integrating Visa APIs."]
    assert "US GAAP" in normalized["role_overview"]
    assert "7 years" not in normalized["role_overview"]
    assert "strong relevant experience" in normalized["role_overview"].lower()
    assert "Australia" not in normalized["role_overview"]
    assert "Canada" not in normalized["who_this_is_for"]

    normalized_where = normalize_data(
        _base_formatter_data(
            where_you_will=(
                "Candidates must be located in India. "
                "Use two years of relevant experience to evaluate records."
            )
        ),
        "mercor",
    )["where_you_will"]
    assert "India" not in normalized_where
    assert "two years" not in normalized_where.lower()
    assert "strong relevant experience" in normalized_where.lower()

    responsibility_policy = normalize_data(
        _base_formatter_data(
            role_responsibilities=[
                "Use 5 years of professional experience to evaluate records."
            ]
        ),
        "mercor",
    )["role_responsibilities"]
    assert responsibility_policy == [
        "Use strong relevant experience to evaluate records."
    ]

    print("[SUCCESS] Age, geography, and experience policies passed!")


def test_missing_fields_and_location_output():
    missing_data = _base_formatter_data(
        type="",
        pay="",
        commitment="",
        location="Hybrid in New York",
        role_overview="",
        where_you_will="",
        who_this_is_for="",
        role_responsibilities=[],
        requirements=[],
    )

    for client_id in SUPPORTED_CLIENTS:
        formatter = get_formatter(client_id)
        output = formatter.format_jd(missing_data) + "\n" + formatter.format_email(missing_data)
        assert "Remote" in output, client_id
        assert "Hybrid in New York" not in output, client_id
        assert "To be discussed" not in output, client_id
        assert "<b>Compensation:</b>" not in output, client_id
        assert "<b>Pay:</b>" not in output, client_id
        assert "$80–$135" not in output and "$80—$135" not in output, client_id
        assert "Stripe" not in output and "Wise" not in output, client_id
        assert not re.search(r"<ul>\s*</ul>", output, flags=re.IGNORECASE), client_id

        fabricated_phrases = [
            "Build and deploy MCP servers",
            "Board-certified Internal Medicine",
            "Create realistic brokerage deliverables",
            "Fluency in Assamese",
            "document and deck production quality assurance",
        ]
        assert not any(phrase.lower() in output.lower() for phrase in fabricated_phrases), client_id

    turing_output = get_formatter("turing").format_jd(missing_data)
    assert "<b>Commitment:</b> 10-40 hrs/week" in turing_output

    stem_output = get_formatter("stemsyncai").format_jd(missing_data)
    assert "research-grade physics" not in stem_output.lower()
    assert "latex" not in stem_output.lower()
    assert "Quick Snapshot" not in stem_output

    cura_output = (
        get_formatter("curasenseai").format_jd(missing_data)
        + get_formatter("curasenseai").format_email(missing_data)
    )
    assert "What You Will Be Doing" not in cura_output
    assert "Who We Are Looking For" not in cura_output
    assert "Key Responsibilities" not in cura_output
    assert "Candidate Profile" not in cura_output

    for client_id in ("mercor", "micro1", "turing"):
        jd_output = get_formatter(client_id).format_jd(missing_data)
        assert "Role Responsibilities" not in jd_output, client_id
        assert "<b>Requirements" not in jd_output, client_id

    turing_email = get_formatter("turing").format_email(missing_data)
    assert "Application Form Link" not in turing_email
    assert "clicking here" not in turing_email

    cta_expectations = {
        "crossing_hurdles": "Apply here (reviewed on a rolling basis):",
        "codegeniusrecruit": "To apply, kindly use the link below:",
        "curasenseai": "Click below to apply and continue your application process:",
        "stemsyncai": "If interested, kindly apply on the link below:",
    }
    linked_data = _base_formatter_data(link="https://example.test/apply")
    for client_id, expected_cta in cta_expectations.items():
        assert expected_cta in get_formatter(client_id).format_email(linked_data), client_id

    single_real_data = normalize_data(
        _base_formatter_data(
            role_responsibilities=["Validate the supplied dataset."],
            requirements=["Strong Python skills."],
            who_this_is_for="Python analysts.",
        ),
        "mercor",
    )
    assert single_real_data["role_responsibilities"] == ["Validate the supplied dataset."]
    assert single_real_data["requirements"] == ["Strong Python skills."]
    assert single_real_data["who_this_is_for"] == "Python analysts."

    empty_real_data = normalize_data(
        _base_formatter_data(role_responsibilities=[], requirements=[]),
        "mercor",
    )
    assert empty_real_data["role_responsibilities"] == []
    assert empty_real_data["requirements"] == []

    print("[SUCCESS] Missing fields are omitted and location is Remote!")


def test_html_escaping_and_link_validation():
    malicious = _base_formatter_data(
        role='<img src=x onerror="alert(1)">',
        type='<svg onload="alert(2)">',
        pay='$10</b><script>alert(3)</script>',
        location='<iframe src="javascript:alert(4)"></iframe>',
        link='https://example.test/" onmouseover="alert(5)',
        role_overview='<script>alert(6)</script>',
        where_you_will='evaluate </b><img src=x onerror="alert(7)">',
        who_this_is_for='<svg onload="alert(8)">',
        client='<img src=x onerror="alert(9)">',
        client_desc='<script>alert(10)</script>',
        role_responsibilities=['Review </li><script>alert(11)</script>'],
        requirements=['<img src=x onerror="alert(12)">'],
        preferred_qualifications=['<svg onload="alert(13)">'],
    )

    for client_id in SUPPORTED_CLIENTS:
        formatter = get_formatter(client_id)
        output = formatter.format_jd(malicious) + "\n" + formatter.format_email(malicious)
        lowered = output.lower()
        assert "<img" not in lowered, client_id
        assert "<script" not in lowered, client_id
        assert "<svg" not in lowered, client_id
        assert "<iframe" not in lowered, client_id
        assert 'href="javascript:' not in lowered, client_id
        assert ' onmouseover="' not in lowered, client_id
        assert "&lt;img" in lowered or "&lt;script" in lowered, client_id

        safe_output = formatter.format_email(
            _base_formatter_data(link="https://example.test/apply?a=1&b=2")
        )
        assert 'href="https://example.test/apply?a=1&amp;b=2"' in safe_output, client_id

    print("[SUCCESS] Formatter HTML and URL escaping passed!")


def test_schema_role_and_normalizer_regressions():
    assert parser._openai_client is None
    assert parser.OUTPUT_VERSION == "v4"
    assert validate_raw_schema({"requirements": "Python experience"}) == (
        False,
        "requirements must be a list",
    )
    assert validate_raw_schema({"requirements": ["Python", 3]}) == (
        False,
        "requirements must contain only strings",
    )

    assert extract_raw_role("Job Title:\nData Analyst") == "Data Analyst"
    assert extract_raw_role("Title: Senior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("Job Title - Senior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("Position Title — Senior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("Position | Senior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("Role：Senior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("JOB TITLE\tData Analyst\nDescription") == "Data Analyst"
    assert extract_raw_role("Job Title = Data Analyst\nDescription") == "Data Analyst"
    assert extract_raw_role("Position:\nSenior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("Job Title:\nQuantum Workflow Wizard\nDescription") == "Quantum Workflow Wizard"
    assert extract_raw_role("# Senior Data Analyst\nAbout the Role") == "Senior Data Analyst"
    assert extract_raw_role("**Job Title:** Senior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("## Job Title\nSenior Data Analyst\nDescription") == "Senior Data Analyst"
    assert extract_raw_role("Job Title: Quantum Workflow Wizard\nDescription") == "Quantum Workflow Wizard"
    assert extract_raw_role("Audio and Video Technicians\nPart-time position") == "Audio and Video Technicians"
    assert extract_raw_role("senior software engineer\nAbout the Role") == "senior software engineer"
    assert extract_raw_role("Chief of Staff\nAbout the Role") == "Chief of Staff"
    assert extract_raw_role("Product Owner\nAbout the Role") == "Product Owner"
    assert extract_raw_role("AI Training - Mathematics\nAbout the Role") == "AI Training - Mathematics"
    assert extract_raw_role("Customer Success\nAbout the Role") == "Customer Success"
    assert extract_raw_role("Machine Learning\nAbout the Role") == "Machine Learning"
    assert extract_raw_role("<h1>Job Title: Attacker</h1>\nDescription") == ""
    assert extract_raw_role("Job Title: javascript:alert(1)\nDescription") == ""
    assert extract_raw_role("Job Title:\nhttps://attacker.test/title\nDescription") == ""
    assert extract_raw_role("Job Title:\nDescription: Review candidate data.\nRequirements") == ""
    assert extract_raw_role("Arbitrary first line\nDescription") == ""
    assert extract_raw_role("Acme Corporation\nAbout the Role") == ""
    assert extract_raw_role("Terms And Conditions\nSenior Data Analyst") == ""
    assert extract_raw_role(
        "Role:\nYou will review AI responses\nJob Title: Data Analyst"
    ) == "Data Analyst"
    assert extract_raw_role(
        "Role:\nReviewers evaluate AI-generated responses\nJob Title: Data Analyst"
    ) == "Data Analyst"
    assert extract_raw_role(
        "Position:\nData Scientists transform complex research\nJob Title: Senior Data Analyst"
    ) == "Senior Data Analyst"
    for prose_role in (
        "Role:\nData Scientists will transform healthcare",
        "Role:\nReviewers routinely evaluate AI-generated responses",
        "Position:\nSenior engineers are building scalable systems",
        "Role:\nData Analysts who review model outputs",
        "Role:\nEngineers responsible for building reliable systems",
    ):
        assert extract_raw_role(prose_role) == ""
    assert extract_raw_role("Shape The Future\nAbout the Role") == ""
    assert extract_raw_role("Help Build Better AI\nAbout the Role") == ""
    assert extract_raw_role("Job Description\nSenior Data Analyst") == ""
    assert extract_raw_role("$30 per hour\nSenior Data Analyst") == ""
    assert extract_raw_role("Remote\nSenior Data Analyst") == ""
    assert extract_raw_role("Job Title: Senior Data Analyst\nDescription") == "Senior Data Analyst"
    assert parser.normalize_role("India-based Data Analyst") == "Data Analyst"
    assert parser.normalize_role("Data Analyst - Australia") == "Data Analyst"
    assert parser.normalize_role("US GAAP Analyst") == "US GAAP Analyst"
    assert parser.normalize_role("Berlin-based Data Analyst") == "Data Analyst"
    assert parser.normalize_role("Data Analyst - Berlin") == "Data Analyst"
    assert parser.normalize_role("Data Analyst | Bangalore") == "Data Analyst"
    assert parser.normalize_role("Evidence-based Researcher") == "Evidence-based Researcher"
    assert parser.normalize_role("Machine Learning-based Engineer") == "Machine Learning-based Engineer"

    scalar_policy = normalize_data(
        _base_formatter_data(
            role="18+ Berlin-based Data Analyst",
            type="Contract - US only",
            pay="$30/hour for US residents only",
        ),
        "mercor",
    )
    assert scalar_policy["role"] == "Data Analyst"
    assert scalar_policy["type"] == "Contract"
    assert scalar_policy["pay"] == "$30/hour"
    for standard_client in ("mercor", "micro1", "turing"):
        scalar_output = get_formatter(standard_client).format_jd(
            _base_formatter_data(
                role="18+ Data Analyst",
                type="Contract - US only",
                pay="$30/hour for US residents only",
            )
        )
        assert "18+" not in scalar_output and "US only" not in scalar_output
        assert "US residents" not in scalar_output and "$30/hour" in scalar_output

    assert scrub_all_client_orgs_from_jd("Mercor is seeking experienced analysts.") == (
        "The hiring team is seeking experienced analysts."
    )
    assert scrub_all_client_orgs_from_jd("Work at Mercor on AI systems.") == (
        "Work on AI systems."
    )
    assert scrub_all_client_orgs_from_jd("This role at Mercor involves evaluation.") == (
        "This role involves evaluation."
    )

    assert normalize_compensation("$0 - $120,000 per year") == "Up to $120,000 per year"
    assert normalize_compensation("$0–$75/hour") == "Up to $75/hour"
    assert clean_category_list([], VALID_JOB_FUNCTIONS) == []
    assert clean_titles(["Data Analyst"], "Business Analyst") == ["Data Analyst"]
    assert clean_titles(
        ["Retail Analyst", "Claims Analyst", "Maintenance Engineer"],
        "Operations Analyst",
    ) == ["Retail Analyst", "Claims Analyst", "Maintenance Engineer"]
    assert clean_titles(["AI Analyst"], "Operations Analyst") == ["Operations Analyst"]

    source_role_payload = {
        **_base_formatter_data(
            role="Data Annotation Specialist",
            pay="$30/hour",
            commitment="10-40 hrs/week",
        ),
        "suggested_titles": ["Data Annotation Specialist"],
        "skills": ["Data Annotation"],
        "job_functions": ["Analytics"],
        "industries": ["Technology, Information and Media"],
        "justifications": {},
    }
    original_generate = parser.generate_llm_output
    original_refine = parser.refine_classifications_with_higher_model
    try:
        parser.generate_llm_output = lambda *args, **kwargs: json.dumps(source_role_payload)
        parser.refine_classifications_with_higher_model = lambda *args, **kwargs: None
        source_role_result = parser.get_valid_llm_output(
            "18+ India-based AI Training - Data Annotator\nAbout the Role\nReview training data.",
            client="mercor",
        )
    finally:
        parser.generate_llm_output = original_generate
        parser.refine_classifications_with_higher_model = original_refine

    expected_source_role = "AI Training - Data Annotator"
    assert source_role_result["structured_data"]["role"] == expected_source_role
    assert source_role_result["subject"].startswith(f"{expected_source_role} |")
    assert source_role_result["linkedin_title"].startswith(f"{expected_source_role} |")
    assert f"<b>Position:</b> {expected_source_role}<br>" in source_role_result["jd"]
    assert f"<b>Role:</b> {expected_source_role}<br>" in source_role_result["email"]
    assert source_role_result["titles"] == ["Data Annotation Specialist"]
    for rendered_value in (
        source_role_result["jd"],
        source_role_result["email"],
        source_role_result["subject"],
        source_role_result["linkedin_title"],
    ):
        assert "18+" not in rendered_value
        assert "India-based" not in rendered_value

    calls = []
    original_generate = parser.generate_llm_output
    try:
        parser.generate_llm_output = lambda *args, **kwargs: calls.append(1) or "not-json"
        try:
            parser.get_valid_llm_output("Job Title: Data Analyst", client="mercor")
            raise AssertionError("Invalid JSON must not produce a successful placeholder result")
        except ValueError as exc:
            assert "valid structured output" in str(exc)
    finally:
        parser.generate_llm_output = original_generate
    assert len(calls) == 3

    parser_source = Path(parser.__file__).read_text(encoding="utf-8")
    assert "load_dotenv(dotenv_path=_env_path, override=False)" in parser_source
    scraper_source = (Path(__file__).parent / "misc" / "mercor_scraper_supabase.py").read_text(
        encoding="utf-8"
    )
    assert "if not dry_run and not SUPABASE_KEY:" in scraper_source
    assert "existing_record = None if dry_run else fetch_existing_job(listing_id)" in scraper_source

    print("[SUCCESS] Schema, title, compensation, and failure handling passed!")

if __name__ == "__main__":
    test_turing_formatter()
    test_domain_pages_rules()
    test_reported_regressions()
    test_policy_enforcement_and_preservation()
    test_missing_fields_and_location_output()
    test_html_escaping_and_link_validation()
    test_schema_role_and_normalizer_regressions()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
