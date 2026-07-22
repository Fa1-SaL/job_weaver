"""
Formatters for the 8 Domain Pages.
Each formatter subclasses MercorFormatter and implements both `format_jd` and `format_email`
to produce the exact structure and formatting shown in the LinkedIn JD and InMail Draft specifications,
fully sanitized of geographical locations, deadlines, and improper sentences.
"""

import re
from formatters.mercorFormatter import MercorFormatter


def sanitize_inline_geography(text: str) -> str:
    if not text:
        return ""
    # Remove geographical terms case-insensitively
    text = re.sub(r'(?i)\b(?:UK[- ]Based|US[- ]Based|U\.S\.[- ]Based|Canada[- ]Based|Canadian|United States|Canada|London|United Kingdom|Britain|America|American|US Based|US-Based)\b', '', text)
    text = re.sub(r'\bUS\b', '', text)
    # Remove deadlines or turnaround phrases
    text = re.sub(r'(?i)\b(?:within \d+ to \d+ days|turnaround|turnaround time|completion date|deadline)\b.*', '', text)
    
    # Remove trailing or leading commas, pipes, spaces that might remain
    text = re.sub(r'\s*,\s*$', '', text) # trailing comma
    text = re.sub(r'^\s*,\s*', '', text) # leading comma
    text = re.sub(r'\s*\|\s*$', '', text) # trailing pipe
    text = re.sub(r'^\s*\|\s*', '', text) # leading pipe
    
    # Cleanup extra spaces/delimiters
    text = re.sub(r'\s*\|\s*Remote\b', ' Remote', text)
    text = re.sub(r'\bRemote\s*\|\s*', 'Remote ', text)
    text = re.sub(r'\s*\|\s*\s*', ' ', text)
    
    # If it was comma separated like "Remote, " (after stripping United States), remove trailing comma
    text = re.sub(r',\s*$', '', text)
    text = re.sub(r'^\s*,', '', text)
    
    return re.sub(r'\s+', ' ', text).strip()


def clean_bullets(bullets) -> list:
    if not bullets:
        return []
    cleaned = []
    for bullet in bullets:
        bullet_str = str(bullet).strip()
        bullet_lower = bullet_str.lower()
        
        # Turnaround / deadline filter
        if any(word in bullet_lower for word in ["turnaround", "deadline", "days of applying", "time limit"]):
            continue
            
        # Age requirement filter/completion
        has_age = any(term in bullet_lower for term in ["at least old", "years old", "age of", "at least 18", "at least 21"])
        has_location = any(term in bullet_lower for term in ["united states", "canada", "uk", "london", "europe", "located in", "residing in", "resident", "us based", "u.s. based", "residents of"])
        
        if has_age:
            cleaned.append("Candidates must be at least 21 years old.")
            continue
            
        if has_location:
            # If it only mentions location requirement, omit it
            continue
            
        cleaned_bullet = sanitize_inline_geography(bullet_str)
        if cleaned_bullet:
            cleaned.append(cleaned_bullet)
    return cleaned


def sanitize_format_data(data: dict) -> dict:
    clean_data = dict(data)
    
    # Sanitize all string fields
    string_fields = ["role", "type", "pay", "location", "commitment", "role_overview", "who_this_is_for", "client_desc"]
    for field in string_fields:
        if field in clean_data:
            clean_data[field] = sanitize_inline_geography(clean_data[field])
            
    # Specially handle location fallback to Remote
    loc = clean_data.get("location", "Remote")
    if not loc or loc.lower().strip() in ["", "remote"]:
        clean_data["location"] = "Remote"
    else:
        clean_data["location"] = loc
        
    # Sanitize responsibilities and requirements
    clean_data["role_responsibilities"] = clean_bullets(clean_data.get("role_responsibilities", []))
    clean_data["requirements"] = clean_bullets(clean_data.get("requirements", []))
    
    return clean_data


class CrossingHurdlesFormatter(MercorFormatter):
    """Page 1: Crossing Hurdles JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Video Game Annotator") or "Video Game Annotator"
        role_type = data.get("type", "Hourly contract") or "Hourly contract"
        pay = data.get("pay", "$16-$17 per hour") or "$16-$17 per hour"
        location = data.get("location", "Remote") or "Remote"
        commitment = data.get("commitment", "10–40 hours/week") or "10–40 hours/week"

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Annotate assigned games (e.g., Minecraft, open-world or exploration-based games) for structured sessions (typically 15–60 minutes)",
                "Follow simple annotation instructions (e.g., exploration, basic interactions, task-based play)",
                "Ensure recordings meet quality requirements (no lag, stable FPS, correct settings)"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Access to a personal Windows computer",
                "Comfortable installing recording software for gameplay and input capture",
                "Reliable internet connection for uploading large video files",
                "Attention to detail and willingness to follow setup guidelines"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        return f"""<b>Position:</b> {role}<br>
<b>Type:</b> {role_type}<br>
<b>Compensation:</b> {pay}<br>
<b>Location:</b> {location}<br>
<b>Commitment:</b> {commitment}<br><br>

<b>Role Responsibilities:</b>
<ul>
{resp_bullets}
</ul><br>

<b>Requirements:</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Apply using the Easy Apply button and submit your application.</li>
<li>Applications will be reviewed based on the role requirements.</li>
<li>Eligible candidates will receive a message in their LinkedIn inbox with instructions to continue the application process.</li>
<li>Follow the instructions in the message to complete the remaining application steps.</li>
</ul><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Role")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "")
        role_type = data.get("type", "Contract")
        location = data.get("location", "Remote")

        pay_display = f" – {pay}" if pay else ""
        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""

        return f"""Hi {{firstName}},<br><br>

I'm from <b>Crossing Hurdles</b>, Based on your profile, we think you could be a strong fit for the <a href="{link}"><b>{role}</b></a> position at <b>Mercor</b>.<br><br>

<b>Organization:</b> Mercor<br>
<b>Referral by:</b> Crossing Hurdles<br>
<b>Role:</b> {role}<br>
<b>Type:</b> {role_type}<br>
{pay_row}<b>Location:</b> {location}<br><br>

<b>Application Process</b>
<ul>
<li>Click the Mercor application link provided in this message.</li>
<li>Create a Mercor account if you are a new user, or sign in to your existing account.</li>
<li>Once signed in, submit your application for the role to complete the application process.</li>
</ul><br>

<b>Apply here (reviewed on a rolling basis):</b><br>
<a href="{link}"><b>{role}</b></a>{pay_display}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<b>Take Steps to Boost Your Profile:</b>
<ul>
<li>Need tips to improve your chances of selection? Check out the <a href="https://docs.google.com/document/d/1xYe9X4t2Bv6BEScXwwvix35Kmlc92xiulEpBDLcCZb8/edit?usp=sharing">Interview Preparation Playbook</a></li>
<li>You can strengthen your profile through the <a href="https://work.mercor.com/home?tab=assessments&referralCode=c88e7e37-c849-4793-a401-f58c8615e4c7">Assessment tab</a> in your dashboard. Completing skill based assessments can help unlock future opportunities, including roles you have not applied to or roles that may not be publicly listed.</li>
</ul><br>

<i>P.S. For immediate support, contact support@mercor.com</i>""".strip()


class CodeGeniusRecruitFormatter(MercorFormatter):
    """Page 2: CodeGeniusRecruit JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role_type = data.get("type", "Hourly Contract") or "Hourly Contract"
        location = data.get("location", "Remote") or "Remote"
        commitment = data.get("commitment", "Flexible Schedule") or "Flexible Schedule"
        pay = data.get("pay", "$40–$50 per hour") or "$40–$50 per hour"

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Build and deploy MCP servers using Python and FastMCP",
                "Integrate web and desktop applications into sandbox environments",
                "Work with APIs, Docker, Linux, and service configurations",
                "Implement application state management and deployment workflows",
                "Test, debug, and validate applications for production readiness"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Strong experience in Python development",
                "Strong experience in APIs, backend systems, and debugging",
                "Strong experience in Docker, Linux, and local testing workflows",
                "Strong experience in configuration management and deployment pipelines",
                "Strong problem-solving skills with attention to technical detail"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        return f"""<b>Work Snapshot</b><br>
<b>Type:</b> {role_type}<br>
<b>Location:</b> {location}<br>
<b>Commitment:</b> {commitment}<br>
<b>Commission:</b> {pay}<br><br>

<b>What You’ll Be Doing</b>
<ul>
{resp_bullets}
</ul><br>

<b>What We’re Looking For</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Submit your application through the Easy Apply button.</li>
<li>Each application will be reviewed against the role requirements.</li>
<li>Candidates who meet the requirements will receive an email with the next steps.</li>
<li>Follow the instructions provided in the email to complete the remainder of the application process.</li>
</ul><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Software Engineer Expert")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "$40-$50 per hour")
        role_type = data.get("type", "Hourly contract")
        location = data.get("location", "Remote")
        overview = data.get("role_overview") or data.get("where_you_will") or (
            "The role requires candidates who have strong technical skills and experience building backend applications, "
            "working with APIs, and debugging production-ready software."
        )

        highlights = f"Mercor | {location} | {role_type} | {pay}" if pay else f"Mercor | {location} | {role_type}"

        return f"""Hi {{firstName}},<br><br>

I'm from <b>CodeGeniusRecruit</b>. Based on your profile, we think you could be a strong fit for the <a href="{link}"><b>{role}</b></a> position at <b>Mercor</b>.<br><br>

<b>Role highlights:</b> {highlights}<br><br>

We’d like to refer you for this opportunity. {overview}<br><br>

<b>Application Process</b>
<ul>
<li>Open the Mercor application link included in this email.</li>
<li>Register for a Mercor account if you do not already have one, or log in to your existing account.</li>
<li>After signing in, submit your application for the role on Mercor.</li>
</ul><br>

<b>To apply, kindly use the link below:</b><br>
<a href="{link}"><b>{role}</b></a><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

Since applications are reviewed on a rolling basis, earlier submissions receive priority consideration.<br><br>

<i>P.S. For any queries or assistance, feel free to reach out at support@mercor.com</i><br><br>

Best Regards,<br>
CodeGeniusRecruit""".strip()


class CuraSenseAIFormatter(MercorFormatter):
    """Page 3 & 4: CuraSenseAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        overview = data.get("role_overview") or (
            "Join a high-impact healthcare project where your clinical expertise will be used to develop, "
            "evaluate, and refine complex medical reasoning across a wide range of internal medicine scenarios."
        )

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Develop realistic clinical cases covering diagnosis, treatment planning, risk assessment, and guideline-based care",
                "Produce high-quality reference solutions that reflect evidence-based medical practice",
                "Evaluate clinical responses using structured assessment criteria",
                "Provide detailed feedback to improve the quality and consistency of medical outputs",
                "Participate in onboarding and specialty calibration sessions"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Board-certified Internal Medicine physicians with an active, unrestricted medical license",
                "Final-year Internal Medicine residents who are board-eligible",
                "Internal Medicine fellows who are board-certified or board-eligible in their primary specialty with an active, unrestricted medical license",
                "Strong clinical reasoning skills with a commitment to evidence-based patient care",
                "Ability to communicate complex medical concepts clearly and accurately"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay = data.get("pay", "$130–$300 per hour") or "$130–$300 per hour"
        work_style = data.get("work_style", "Fully remote, flexible schedule") or "Fully remote, flexible schedule"
        duration = data.get("duration") or data.get("type", "Ongoing contract") or "Ongoing contract"

        return f"""<b>Role Overview</b><br>
{overview}<br><br>

<b>What You Will Be Doing</b>
<ul>
{resp_bullets}
</ul><br>

<b>Who We Are Looking For</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Use the Easy Apply button to submit your application.</li>
<li>All applications will be assessed based on the requirements of the role.</li>
<li>Eligible applicants will receive an email with further application instructions.</li>
<li>Complete the remaining application steps by following the instructions in the email.</li>
</ul><br>

<b>Role Details</b><br>
<b>Compensation:</b> {pay}<br>
<b>Work style:</b> {work_style}<br>
<b>Duration:</b> {duration}<br><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Internal Medicine Expert")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "$130–$180 per hour")
        role_type = data.get("type", "Contract")
        location = data.get("location", "Remote")
        overview = data.get("role_overview") or (
            "Mercor is hiring experienced domain experts to contribute to reasoning projects by creating realistic scenarios, "
            "evaluating model outputs, and providing evidence-based feedback. This opportunity supports the development "
            "of advanced reasoning systems."
        )

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Design realistic prompts and scenarios based on professional practice",
                "Write expert-level reference responses",
                "Grade AI-generated responses using structured rubrics",
                "Provide written feedback to improve model behavior"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Experienced attending professionals or specialists with verifiable credentials and active certification",
                "Final-year residents or recent graduates who are board-eligible",
                "Fellows or advanced practitioners in their primary domain with strong analytical skills"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""

        return f"""Hi {{firstName}},<br><br>

I’m reaching out from <b>CuraSenseAI</b> to refer you for the role of <a href="{link}"><b>{role}</b></a> at <b>Mercor</b>.<br><br>

<b>About the Role</b><br>
{overview}<br><br>

<b>Organization:</b> Mercor<br>
<b>Referred by:</b> CuraSenseAI<br>
<b>Nature:</b> {location}<br>
<b>Engagement Type:</b> {role_type}<br>
{pay_row}<b>Location:</b> {location}<br><br>

<b>Key Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Candidate Profile</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Access the role using the Mercor application link below.</li>
<li>Create a Mercor account or sign in to your existing account.</li>
<li>Complete your application by submitting it for the role on Mercor.</li>
</ul><br>

<b>Click below to apply and continue your application process:</b><br>
<a href="{link}"><b>{role}</b></a><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For any queries or assistance, feel free to reach out at support@mercor.com</i><br><br>

Best Regards,<br>
CuraSenseAI""".strip()


class LegalTrustAIFormatter(MercorFormatter):
    """Page 5: LegalTrustAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "UK-Based Legal Experts: Magic Circle") or "UK-Based Legal Experts: Magic Circle"
        role_type = data.get("type", "Contract") or "Contract"
        location = data.get("location", "Remote") or "Remote"
        pay = data.get("pay", "$130–$170/hour") or "$130–$170/hour"
        commitment = data.get("commitment", "40 hours/week") or "40 hours/week"
        overview = data.get("role_overview") or (
            "Support the development of advanced legal reasoning systems by creating and evaluating "
            "realistic corporate law scenarios based on modern law firm workflows."
        )

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Create and review realistic legal scenarios covering contract drafting, due diligence, regulatory analysis, and dispute resolution",
                "Develop client advisory and deal structuring scenarios reflecting real-world corporate legal practice",
                "Contribute high-quality legal content to improve model performance and reasoning capabilities",
                "Apply knowledge of Partner-led law firm engagements across transactional and advisory matters",
                "Collaborate with legal subject matter experts to maintain consistency and quality across datasets"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Strong experience in corporate law, particularly within Magic Circle or comparable firms",
                "Deep understanding of Partner-led matter structures and legal workflows",
                "Expertise in transactional, regulatory, and advisory legal work",
                "Ability to work independently and deliver high-quality legal analysis"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        return f"""<b>{role}</b><br>
{role_type} | {location}<br><br>
<b>Pay:</b> {pay}<br>
<b>Time Commitment:</b> {commitment}<br><br>

<b>Role Snapshot</b><br>
{overview}<br><br>

<b>Core Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Ideal Candidate Profile</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Submit your details using the Easy Apply button.</li>
<li>Our team will review applications against the specified role requirements.</li>
<li>Candidates who are eligible to move forward will receive an email with further guidance.</li>
<li>Follow the instructions provided to complete the rest of the application process.</li>
</ul><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "UK-Based Legal Experts: Magic Circle")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "$200-$250 per hour")
        location = data.get("location", "Remote")

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Create, review, and simulate realistic legal scenarios.",
                "Draft contracts, perform due diligence, and conduct regulatory analysis.",
                "Provide client advisory support across transactional and advisory matters.",
                "Contribute to deal structuring and dispute resolution workflows.",
                "Help develop high-quality training data for frontier AI systems."
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        pay_row = f"<b>Compensation:</b> {pay}<br>\n" if pay else ""

        return f"""Hi {{firstName}},<br><br>

I’m reaching out from <b>LegalTrustAI</b> to refer you for a remote opportunity at <b>Mercor</b>.<br><br>

<b>Position Details</b><br>
<a href="{link}"><b>{role}</b></a><br>
<b>Organisation:</b> Mercor<br>
<b>Referred by:</b> LegalTrustAI<br>
{pay_row}<b>Location:</b> {location}<br><br>

<b>Key Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Visit the Mercor application page using the link provided.</li>
<li>Sign up for a Mercor account if you are a new user, or sign in if you already have one.</li>
<li>Once logged in, submit your application to complete the process.</li>
</ul><br>

<b>Apply Here:</b> <a href="{link}"><b>{role}</b></a><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For any queries or assistance, feel free to reach out at support@mercor.com</i><br><br>

Best Regards,<br>
LegalTrustAI""".strip()


class CapitexAIFormatter(MercorFormatter):
    """Page 6: CapitexAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Real Estate Broker") or "Real Estate Broker"
        overview = data.get("role_overview") or (
            "Support a leading AI lab by applying your professional expertise to create and evaluate "
            "domain-specific deliverables that improve AI systems."
        )
        pay = data.get("pay", "$90–$110 per hour") or "$90–$110 per hour"
        commitment = data.get("commitment", "30–40 hours/week") or "30–40 hours/week"
        location = data.get("location", "Remote") or "Remote"
        highlights = f"{pay} | {commitment} | {location}"

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Create realistic brokerage deliverables reflecting common real estate transactions and client scenarios.",
                "Review and evaluate peer-produced work for accuracy, quality, and professional standards.",
                "Identify domain-specific issues and recommend practical, well-supported solutions.",
                "Produce clear, structured documentation aligned with real estate industry practices.",
                "Maintain consistent quality across assigned project deliverables."
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Demonstrated expertise in residential and/or commercial real estate brokerage.",
                "Strong written communication with exception grammar and attention to detail.",
                "Ability to evaluate complex real estate scenarios with sound professional judgment.",
                "Proven capability to produce accurate, client-ready documentation independently.",
                "Commitment to delivering high-quality work within project timelines."
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        strengths = data.get("additional_strengths", [])
        if not strengths:
            strengths = [
                "Strong analytical approach to reviewing and improving professional content.",
                "High level of consistency when assessing technical and transactional accuracy.",
                "Comfortable managing deliverables with minimal supervision."
            ]
        strength_bullets = "\n".join([f"<li>{s}</li>" for s in strengths if s and s.strip()])

        return f"""<b>{role}</b><br><br>
<b>Role Overview</b><br>
{overview}<br><br>
<b>{highlights}</b><br><br>

<b>Key Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Core Requirements</b>
<ul>
{req_bullets}
</ul><br>

<b>Additional Strengths</b>
<ul>
{strength_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Apply through the Easy Apply button to submit your application.</li>
<li>Applications will be carefully reviewed in line with the role requirements.</li>
<li>Eligible applicants will be contacted via email with instructions for the next stage.</li>
<li>Follow the instructions in the email to complete the remaining application requirements.</li>
</ul><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Real Estate Broker")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "$90–$110/hr")
        commitment = data.get("commitment", "~30 Hours/Week")
        location = data.get("location", "Remote")
        overview = data.get("role_overview") or (
            "Support a leading AI lab by applying your professional expertise to create and evaluate "
            "domain-specific deliverables that improve AI systems."
        )

        scope = data.get("where_you_will") or (
            "Develop solutions for common domain scenarios, review peer submissions, and provide "
            "expert feedback to enhance research quality."
        )
        if scope and len(scope) > 0:
            scope = scope[0].upper() + scope[1:]

        highlights_parts = [p for p in [pay, commitment, location] if p]
        highlights = " | ".join(highlights_parts)

        return f"""Hi {{firstName}},<br><br>

I’m reaching out from <b>Capitex AI</b> to refer you for the role of <a href="{link}"><b>{role}</b></a> at <b>Mercor</b>.<br><br>

<b>{highlights}</b><br><br>

<b>About the Role</b><br>
{overview}<br><br>

<b>Scope of Work</b><br>
{scope}<br><br>

<b>Application Process</b>
<ul>
<li>Open the Mercor application link provided in this email.</li>
<li>Create your Mercor account if needed, or sign in to your existing account.</li>
<li>After signing in, submit your application for the role on Mercor to complete your application.</li>
</ul><br>

<b>Apply Here:</b> <a href="{link}"><b>{role}</b></a><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For immediate support, contact support@mercor.com</i><br><br>

Best Regards,<br>
CapitexAI""".strip()


class STEMSyncAIFormatter(MercorFormatter):
    """Page 7: STEMSyncAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Research Physics Expert") or "Research Physics Expert"
        location = data.get("location", "Remote") or "Remote"
        role_type = data.get("type", "Hourly Contract") or "Hourly Contract"
        pay = data.get("pay", "$80–$135/hour") or "$80–$135/hour"
        commitment = data.get("commitment", "~10 hours/week") or "~10 hours/week"
        highlights = f"{role} — {location} | {role_type} | {pay} | {commitment}"

        snapshots = data.get("quick_snapshot", [])
        if not snapshots:
            snapshots = [
                "Contribute to research-grade physics benchmarks used to evaluate advanced language models.",
                "Solve, review, and validate complex physics problems across multiple specialized subfields.",
                "Work asynchronously with a fully remote, flexible schedule.",
                "Earn $80–$135 per hour, with weekly payouts via Stripe or Wise.",
                "Typical commitment of ~10 hours per week over an 8–10 week project window.",
                "Independent contractor engagement with opportunities for project extensions.",
                "Help produce fully human-verified reference solutions for frontier physics reasoning."
            ]
        snapshot_bullets = "\n".join([f"<li>{s}</li>" for s in snapshots if s and s.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Solve research-level physics problems with rigorous derivations, supporting code, and literature-backed references.",
                "Break complex problems into structured reasoning checkpoints and develop Python-based answer templates with automated grading.",
                "Review and validate submitted solutions, providing detailed feedback on correctness, methodology, and completeness.",
                "Evaluate parallel solution approaches and determine the highest-quality reference solution.",
                "Document symbolic equivalence, verification cases, acceptable tolerances, and reasoning methodology.",
                "Hold advanced academic or research credentials in a relevant physics discipline with demonstrated publication record.",
                "Be proficient with LaTeX, Python, Jupyter, SymPy, and technical scientific writing in English."
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        return f"""<b>{highlights}</b><br><br>

<b>Quick Snapshot</b>
<ul>
{snapshot_bullets}
</ul><br>

<b>Requirements</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Apply for the opportunity using the Easy Apply button.</li>
<li>Applications will be evaluated based on the requirements of the opportunity.</li>
<li>Candidates selected to proceed will receive an email with additional instructions.</li>
<li>Use the instructions in the email to complete the remaining application steps.</li>
</ul><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Research Physics Expert")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "$80–$135/hour")
        role_type = data.get("type", "Hourly Contract")
        location = data.get("location", "Remote")

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Solve research-level problems end-to-end with verifiable derivations, code, and peer-reviewed references.",
                "Break down complex challenges into standalone checkpoint problems and develop answer templates with auto-grading functions.",
                "Audit submitted solutions for correctness, methodological soundness, and completeness, providing structured feedback across iterations.",
                "Adjudicate between parallel solution attempts to determine the golden reference solution for benchmark datasets.",
                "Document verification criteria, error tolerances, equivalent symbolic forms, and validation test cases."
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        highlights = f"{location} | {role_type} | {pay}" if pay else f"{location} | {role_type}"

        return f"""Hi {{firstName}},<br><br>

I'm from <b>STEMSyncAI</b> and would like to refer you for the role of <a href="{link}"><b>{role}</b></a> at <b>Mercor</b>.<br><br>

<b>About the Role:</b>
<ul>
<li><b>{highlights}</b></li>
{resp_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Use the Mercor application link provided below.</li>
<li>Create a Mercor account or sign in with your existing account.</li>
<li>Complete the application process by submitting your application on Mercor.</li>
</ul><br>

<b>If interested, kindly apply on the link below:</b><br>
<a href="{link}"><b>{role}</b></a><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. Incase of any queries please reach out to Mercor support at support@mercor.com.</i><br><br>

Best Regards,<br>
STEMSyncAI""".strip()


class LinguaSenseAIFormatter(MercorFormatter):
    """Page 8 & 9: LinguaSenseAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        overview = data.get("role_overview") or (
            "Evaluate Assamese AI-generated responses for factual accuracy, reasoning quality, and "
            "language effectiveness to produce high-quality evaluation data that improves model "
            "performance."
        )
        role_type = data.get("type", "Part-time position; Contract Work; Independent Contractor; Flexible Schedule") or "Part-time position; Contract Work; Independent Contractor; Flexible Schedule"
        pay = data.get("pay", "$15–$20 per hour") or "$15–$20 per hour"
        location = data.get("location", "Remote") or "Remote"

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Evaluate AI-generated responses for factual accuracy, reasoning quality, clarity, tone, and completeness",
                "Conduct fact-checking using reliable public sources and external verification tools",
                "Identify response strengths, inaccuracies, and areas requiring improvement",
                "Produce structured evaluation data and written feedback in English",
                "Verify that responses comply with expected conversational behavior and system guidelines"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Bachelor's degree",
                "Fluency in Assamese and strong proficiency in English",
                "Ability to complete the bilingual competency interview in Assamese",
                "Experience using large language models (LLMs) and understanding of their practical applications",
                "Ability to write clear evaluation feedback in English",
                "Background in research, policy, analytics, linguistics, engineering, or another analytical discipline"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        return f"""<b>Objective</b><br>
{overview}<br><br>

<b>Opportunity Details</b><br>
<b>Job Format:</b> {role_type}<br>
<b>Pay:</b> {pay}<br>
<b>Location:</b> {location}<br><br>

<b>Primary Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Role Requirements</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Submit your application using the Easy Apply button.</li>
<li>Applications will be reviewed to determine alignment with the role requirements.</li>
<li>Applicants who are eligible to continue will receive an email with further instructions.</li>
<li>Follow the instructions provided in the email to complete the remaining application process.</li>
</ul><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Generalist - English & Assamese")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "$15-$20 per hour")
        role_type = data.get("type", "Part-time position")
        location = data.get("location", "Remote")
        overview = data.get("role_overview") or (
            "Help evaluate AI-generated responses by identifying factual issues, reasoning gaps, and areas for improvement. "
            "Your evaluations will support the development of higher-quality AI responses, with all analysis completed in English."
        )

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Conduct fact-checking using trusted public sources and external tools",
                "Evaluate AI responses for factual accuracy, reasoning, clarity, tone, and completeness",
                "Identify strengths, weaknesses, and areas for improvement in model outputs",
                "Ensure responses align with expected conversational behavior and system guidelines"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Bachelor's degree or higher",
                "Native or bilingual fluency in target languages and English",
                "Experience using large language models (LLMs)",
                "Strong English writing and analytical skills"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""

        return f"""Hi {{firstName}},<br><br>

I'm from <b>LinguaSenseAI</b> and reaching out to refer you for a <a href="{link}"><b>{role}</b></a> opportunity at <b>Mercor</b>.<br><br>

<b>Role Overview</b><br>
{overview}<br><br>

<b>Opportunity Details</b><br>
<b>Job Format:</b> {role_type}<br>
{pay_row}<b>Location:</b> {location}<br><br>

<b>Primary Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Role Requirements</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Open the Mercor application link provided in this email.</li>
<li>Create a Mercor account if required, or sign in to your existing account.</li>
<li>Follow the instructions on Mercor and submit your application for the role to complete the application process.</li>
</ul><br>

<b>Click here to complete your application for: <a href="{link}"><b>{role}</b></a></b><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. If you have any queries, you can contact Mercor support at support@mercor.com.</i><br><br>

Best Regards,<br>
LinguaSenseAI""".strip()


class DesignMeshAIFormatter(MercorFormatter):
    """Page 10 & 11: DesignMeshAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Document/Deck Production QA Evaluator") or "Document/Deck Production QA Evaluator"
        overview = data.get("role_overview") or (
            "Review and assess document, spreadsheet, and presentation deliverables for quality, accuracy, "
            "and overall presentation standards, providing structured evaluations and actionable feedback."
        )

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Evaluate documents, spreadsheets, and slide decks against established quality standards.",
                "Identify factual, formatting, visual, and presentation issues across work products.",
                "Assess deliverables for accuracy, consistency, and overall quality.",
                "Provide clear, structured written evaluations with actionable feedback.",
                "Ensure outputs meet defined quality and presentation expectations."
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Professional fluency in English.",
                "Strong expertise in document and deck production quality assurance.",
                "Highly proficient in Microsoft Office and Google Workspace.",
                "Advanced proficiency with Google Slides and Microsoft PowerPoint.",
                "Ability to evaluate presentation quality using structured assessment criteria."
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        role_type = data.get("type", "Hourly contract") or "Hourly contract"
        pay = data.get("pay", "$80–$120 per hour") or "$80–$120 per hour"
        location = data.get("location", "Remote") or "Remote"

        return f"""<b>{role}</b><br><br>
<b>Role Summary</b><br>
{overview}<br><br>

<b>Deliverables</b>
<ul>
{resp_bullets}
</ul><br>

<b>Requirements</b>
<ul>
{req_bullets}
</ul><br>

<b>Details</b><br>
<b>Job Type:</b> {role_type}<br>
<b>Compensation:</b> {pay}<br>
<b>Work Setup:</b> {location}<br><br>

<b>Application Process</b>
<ul>
<li>Complete your application using the Easy Apply button.</li>
<li>Your application will be reviewed according to the role requirements.</li>
<li>Qualified candidates will receive an email outlining the next stage of the application process.</li>
<li>Follow the instructions in the email to proceed with the remaining steps.</li>
</ul><br>

#LI-CH""".strip()

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data)
        role = data.get("role", "Document/Deck Production QA Evaluator")
        link = data.get("link", "https://work.mercor.com/explore")
        pay = data.get("pay", "$80–$120/hour")
        role_type = data.get("type", "Hourly Contract")
        location = data.get("location", "Remote")
        overview = data.get("role_overview") or (
            "Mercor is hiring expert Evaluators to review and assess AI-generated documents, spreadsheets, "
            "and slide decks for accuracy, presentation quality, and domain rigor — contributing directly to the training "
            "of frontier AI models."
        )

        resps = data.get("role_responsibilities", [])
        if not resps:
            resps = [
                "Evaluate AI-generated documents, spreadsheets, and slide decks against domain-specific quality rubrics",
                "Identify factual, aesthetic, and presentation errors in AI outputs",
                "Provide clear, structured written feedback on assessed work products",
                "Apply deep subject-matter expertise to grade and improve AI-generated artifacts"
            ]
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        if not reqs:
            reqs = [
                "Strong professional background in document and deck production QA",
                "Highly proficient in Microsoft Office and Google Workspace, particularly PowerPoint and Google Slides",
                "Native or professional fluency in English",
                "Portfolio or demonstrable work in presentation design and production quality assessment expected"
            ]
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""

        return f"""Hi {{firstName}},<br><br>

I'm reaching out from <b>DesignMeshAI</b> to refer you for the role of <a href="{link}"><b>{role}</b></a> at <b>Mercor</b>.<br><br>

<b>About the Role</b><br>
{overview}<br><br>

<b>Organization:</b> Mercor<br>
<b>Referred by:</b> DesignMeshAI<br>
<b>Engagement:</b> {role_type}<br>
{pay_row}<b>Mode:</b> {location}<br><br>

<b>Key Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Who We're Looking For</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Click the Mercor application link shared in this email.</li>
<li>Sign up for a Mercor account if required, or log in to continue.</li>
<li>After accessing your account, submit your application to finalize the process.</li>
</ul><br>

<b>Apply here:</b> <a href="{link}"><b>{role}</b></a><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For immediate support, contact support@mercor.com</i><br><br>

Best Regards,<br>
DesignMeshAI""".strip()
