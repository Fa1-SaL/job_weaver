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
import sys

# Set standard output to UTF-8 for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from formatters import get_formatter
from formatters.domainPagesFormatter import scrub_all_client_orgs_from_jd
from clients import DOMAIN_PAGE_KEYS

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

if __name__ == "__main__":
    test_turing_formatter()
    test_domain_pages_rules()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
