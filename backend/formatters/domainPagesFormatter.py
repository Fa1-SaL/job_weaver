"""
Formatters for the 8 Domain Pages.
Each formatter subclasses MercorFormatter and implements both `format_jd` and `format_email`
to produce the exact structure and formatting shown in the LinkedIn JD and InMail Draft specifications.

Rules:
1. Hyperlinks are explicitly styled in blue (#0066cc) on both <a> and inner elements with !important.
2. Mercor CAN be mentioned on InMails (format_email), but MUST NOT be mentioned on JDs (format_jd).
3. Crossing Hurdles is ONLY mentioned on Crossing Hurdles domain page itself. All other 7 domain pages avoid mentioning Crossing Hurdles completely.
"""

import re
try:
    from .mercorFormatter import MercorFormatter
    from .base import escape_html, omit_empty_html_sections, prepare_html_data, safe_href
    from ..policy_utils import is_prohibited_eligibility, remove_prohibited_sentences
except ImportError:
    from formatters.mercorFormatter import MercorFormatter
    from formatters.base import escape_html, omit_empty_html_sections, prepare_html_data, safe_href
    from policy_utils import is_prohibited_eligibility, remove_prohibited_sentences


def scrub_all_client_orgs_from_jd(text: str) -> str:
    """
    Guarantees ABSOLUTELY ZERO occurrence of Mercor, Cincinnatus, or client platform names in JDs (format_jd).
    Removes/replaces all variations, URLs, possessives, and brand references without adding explicit confidentiality notes.
    """
    if not text:
        return ""
    
    # 1. URLs and email replacements
    text = re.sub(r'(?i)https?://[^\s<"]*mercor[^\s<"]*', '#', text)
    text = re.sub(r'(?i)\b[A-Za-z0-9._%+-]+@mercor\.com\b', 'support@jobweaver.com', text)
    text = re.sub(r'(?i)\bwork\.mercor\.com\b', 'app.jobweaver.com', text)
    text = re.sub(r'(?i)\bmercor\.com\b', 'jobweaver.com', text)
    
    # 2. Specific phrases
    text = re.sub(r'(?i)\bMercor[\'’]?s?\s+projects?\b', 'AI projects', text)
    text = re.sub(r'(?i)\bMercor[\'’]?s?\s+platform\b', 'AI platform', text)
    text = re.sub(r'(?i)\bMercor[\'’]?s?\s+account\b', 'account', text)
    text = re.sub(r'(?i)\bMercor[\'’]?s?\s+application\b', 'application', text)
    text = re.sub(r'(?i)\bMercor[\'’]?s?\s+dashboard\b', 'dashboard', text)
    text = re.sub(r'(?i)\bMercor[\'’]?s?\s+team\b', 'team', text)
    text = re.sub(r'(?i)\bMercor[\'’]?s?\s+client\b', 'client', text)
    text = re.sub(r'(?i)\bposted\s+by\s+mercor\b', '', text)
    text = re.sub(r'(?i)\bmercor\s+logo\b', '', text)

    # Repair common sentence structures before the final bare-name scrub.
    # This keeps confidentiality enforcement from leaving fragments such as
    # "is seeking" or "Work at on ...".
    org_name = r"(?:Mercor['’]?s?|Cincinnatus['’]?s?(?:\s*AI)?)"
    text = re.sub(
        rf"(?i)\b{org_name}\s+(is|are|was|were|has|have|seeks?|offers?)\b",
        r"The hiring team \1",
        text,
    )
    text = re.sub(
        rf"(?i)\b(?:at|with|for|by)\s+{org_name}\b\s*",
        "",
        text,
    )
    
    # 3. Direct word/possessive removal for Mercor and Cincinnatus
    text = re.sub(r'(?i)\bMercor[\'’]?s?\b', '', text)
    text = re.sub(r'(?i)\bCincinnatus[\'’]?s?(?:\s*AI)?\b', '', text)
    
    # 4. Clean up trailing/leading spaces, double spaces, orphaned prepositions
    text = re.sub(r'(?i)\b(?:at|on|with|by|for)\s+(?=\s*[\.,<\?!]|$)', '', text)
    text = re.sub(r'\s*,\s*,', ',', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return omit_empty_html_sections(text)


def sanitize_inline_geography(text: str, is_jd: bool = False) -> str:
    if not text:
        return ""
    # Remove eligibility sentences, not bare terms such as "US" in "US GAAP"
    # or the pronoun "us" in ordinary prose.
    text = remove_prohibited_sentences(text)
    # Remove deadlines or turnaround phrases
    text = re.sub(r'(?i)\b(?:within \d+ to \d+ days|turnaround|turnaround time|completion date|deadline)\b.*', '', text)
    
    # Remove trailing or leading commas, pipes, spaces that might remain
    text = re.sub(r'\s*,\s*$', '', text)
    text = re.sub(r'^\s*,\s*', '', text)
    text = re.sub(r'\s*\|\s*$', '', text)
    text = re.sub(r'^\s*\|\s*', '', text)
    
    # Cleanup extra spaces/delimiters
    text = re.sub(r'\s*\|\s*Remote\b', ' Remote', text)
    text = re.sub(r'\bRemote\s*\|\s*', 'Remote ', text)
    text = re.sub(r'\s*\|\s*\s*', ' ', text)
    
    text = re.sub(r',\s*$', '', text)
    text = re.sub(r'^\s*,', '', text)
    
    text = re.sub(r'\s+', ' ', text).strip()
    if is_jd:
        return scrub_all_client_orgs_from_jd(text)
    return text


def clean_bullets(bullets, is_jd: bool = False) -> list:
    if not bullets:
        return []
    cleaned = []
    for bullet in bullets:
        bullet_str = str(bullet).strip()
        bullet_lower = bullet_str.lower()
        
        # Turnaround / deadline filter
        if any(word in bullet_lower for word in ["turnaround", "deadline", "days of applying", "time limit"]):
            continue
            
        if is_prohibited_eligibility(bullet_str):
            continue
            
        cleaned_bullet = sanitize_inline_geography(bullet_str, is_jd=is_jd)
        if cleaned_bullet:
            cleaned.append(cleaned_bullet)
    return cleaned


def sanitize_format_data(data: dict, is_jd: bool = False) -> dict:
    clean_data = dict(data)
    
    # Sanitize all string fields
    string_fields = ["role", "type", "pay", "commitment", "role_overview", "who_this_is_for", "client_desc", "where_you_will"]
    for field in string_fields:
        if field in clean_data and isinstance(clean_data[field], str):
            clean_data[field] = sanitize_inline_geography(clean_data[field], is_jd=is_jd)
            
    clean_data["location"] = "Remote"
        
    # Sanitize responsibilities and requirements
    clean_data["role_responsibilities"] = clean_bullets(clean_data.get("role_responsibilities", []), is_jd=is_jd)
    clean_data["requirements"] = clean_bullets(clean_data.get("requirements", []), is_jd=is_jd)
    
    return prepare_html_data(clean_data)


def make_blue_link(url: str, text: str) -> str:
    """Helper to render a 100% blue hyperlink with style on <a> and inner <span> element."""
    safe_url = safe_href(url)
    safe_text = escape_html(text)
    if not safe_url:
        return f'<span style="color: #0066cc !important; font-weight: bold;">{safe_text}</span>'
    return f'<a href="{safe_url}" style="color: #0066cc !important; text-decoration: underline;"><span style="color: #0066cc !important; text-decoration: underline; font-weight: bold;">{safe_text}</span></a>'


class CrossingHurdlesFormatter(MercorFormatter):
    """Page 1: Crossing Hurdles JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        role = data.get("role", "")
        role_type = data.get("type", "")
        pay = data.get("pay", "")
        location = "Remote"
        commitment = data.get("commitment", "")
        pay_row = f"<b>Compensation:</b> {pay}<br>\n" if pay else ""
        commitment_row = f"<b>Commitment:</b> {commitment}<br>\n" if commitment else ""

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        jd_text = f"""<b>Position:</b> {role}<br>
<b>Type:</b> {role_type}<br>
{pay_row}
<b>Location:</b> {location}<br>
{commitment_row}<br>

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
<li>Eligible candidates will receive a message in their LinkedIn or email inbox with instructions to continue the application process.</li>
<li>Follow the instructions in the message to complete the remaining application steps.</li>
</ul><br>

#LI-CH""".strip()
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        role_type = data.get("type", "")
        location = "Remote"

        pay_display = f" – {pay}" if pay else ""
        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""

        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I'm from <b>Crossing Hurdles</b>, Based on your profile, we think you could be a strong fit for the {link_html} position at <b>Mercor</b>.<br><br>

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
{link_html}{pay_display}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<b>Take Steps to Boost Your Profile:</b>
<ul>
<li>Need tips to improve your chances of selection? Check out the {make_blue_link("https://docs.google.com/document/d/1xYe9X4t2Bv6BEScXwwvix35Kmlc92xiulEpBDLcCZb8/edit?usp=sharing", "Interview Preparation Playbook")}</li>
<li>You can strengthen your profile through the {make_blue_link("https://work.mercor.com/home?tab=assessments&referralCode=c88e7e37-c849-4793-a401-f58c8615e4c7", "Assessment tab")} in your dashboard. Completing skill based assessments can help unlock future opportunities, including roles you have not applied to or roles that may not be publicly listed.</li>
</ul><br>

<i>P.S. For immediate support, contact support@mercor.com</i>""".strip()
        return omit_empty_html_sections(email)


class CodeGeniusRecruitFormatter(MercorFormatter):
    """Page 2: CodeGeniusRecruit JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        role_type = data.get("type", "")
        location = "Remote"
        commitment = data.get("commitment", "")
        pay = data.get("pay", "")
        commitment_row = f"<b>Commitment:</b> {commitment}<br>\n" if commitment else ""
        pay_row = f"<b>Compensation:</b> {pay}<br>\n" if pay else ""

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        jd_text = f"""<b>Work Snapshot</b><br>
<b>Type:</b> {role_type}<br>
<b>Location:</b> {location}<br>
{commitment_row}{pay_row}<br>

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
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        role_type = data.get("type", "")
        location = "Remote"
        overview = data.get("role_overview") or data.get("where_you_will") or ""

        highlights = " | ".join(part for part in ["Mercor", location, role_type, pay] if part)
        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I'm from <b>CodeGeniusRecruit</b>. Based on your profile, we think you could be a strong fit for the {link_html} position at <b>Mercor</b>.<br><br>

<b>Role highlights:</b> {highlights}<br><br>

We’d like to refer you for this opportunity. {overview}<br><br>

<b>Application Process</b>
<ul>
<li>Open the Mercor application link included in this email.</li>
<li>Register for a Mercor account if you do not already have one, or log in to your existing account.</li>
<li>After signing in, submit your application for the role on Mercor.</li>
</ul><br>

<b>To apply, kindly use the link below:</b><br>
{link_html}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

Since applications are reviewed on a rolling basis, earlier submissions receive priority consideration.<br><br>

<i>P.S. For any queries or assistance, feel free to reach out at support@mercor.com</i><br><br>

Best Regards,<br>
CodeGeniusRecruit""".strip()
        return omit_empty_html_sections(email)


class CuraSenseAIFormatter(MercorFormatter):
    """Page 3 & 4: CuraSenseAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        overview = data.get("role_overview", "")

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay = data.get("pay", "")
        role_type = data.get("type", "")
        pay_row = f"<b>Compensation:</b> {pay}<br>\n" if pay else ""
        type_row = f"<b>Engagement:</b> {role_type}<br>\n" if role_type else ""

        jd_text = f"""<b>Role Overview</b><br>
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
{pay_row}<b>Location:</b> Remote<br>
{type_row}<br>

#LI-CH""".strip()
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        role_type = data.get("type", "")
        location = "Remote"
        overview = data.get("role_overview", "")

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""
        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I’m reaching out from <b>CuraSenseAI</b> to refer you for the role of {link_html} at <b>Mercor</b>.<br><br>

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
{link_html}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For any queries or assistance, feel free to reach out at support@mercor.com</i><br><br>

Best Regards,<br>
CuraSenseAI""".strip()
        return omit_empty_html_sections(email)


class LegalTrustAIFormatter(MercorFormatter):
    """Page 5: LegalTrustAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        role = data.get("role", "")
        role_type = data.get("type", "")
        location = "Remote"
        pay = data.get("pay", "")
        commitment = data.get("commitment", "")
        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""
        commitment_row = f"<b>Time Commitment:</b> {commitment}<br>\n" if commitment else ""
        overview = data.get("role_overview", "")

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        jd_text = f"""<b>{role}</b><br>
{" | ".join(part for part in [role_type, location] if part)}<br><br>
{pay_row}{commitment_row}<br>

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
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        location = "Remote"

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        pay_row = f"<b>Compensation:</b> {pay}<br>\n" if pay else ""
        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I’m reaching out from <b>LegalTrustAI</b> to refer you for a remote opportunity at <b>Mercor</b>.<br><br>

<b>Position Details</b><br>
{link_html}<br>
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

<b>Apply Here:</b> {link_html}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For any queries or assistance, feel free to reach out at support@mercor.com</i><br><br>

Best Regards,<br>
LegalTrustAI""".strip()
        return omit_empty_html_sections(email)


class CapitexAIFormatter(MercorFormatter):
    """Page 6: CapitexAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        role = data.get("role", "")
        overview = data.get("role_overview", "")
        pay = data.get("pay", "")
        commitment = data.get("commitment", "")
        location = "Remote"
        highlights = " | ".join(part for part in [pay, commitment, location] if part)
        highlights_section = f"<b>{highlights}</b><br><br>" if highlights else ""

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        jd_text = f"""<b>{role}</b><br><br>
<b>Role Overview</b><br>
{overview}<br><br>
{highlights_section}

<b>Key Responsibilities</b>
<ul>
{resp_bullets}
</ul><br>

<b>Core Requirements</b>
<ul>
{req_bullets}
</ul><br>

<b>Application Process</b>
<ul>
<li>Apply through the Easy Apply button to submit your application.</li>
<li>Applications will be carefully reviewed in line with the role requirements.</li>
<li>Eligible applicants will be contacted via email with instructions for the next stage.</li>
<li>Follow the instructions in the email to complete the remaining application requirements.</li>
</ul><br>

#LI-CH""".strip()
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        commitment = data.get("commitment", "")
        location = "Remote"
        overview = data.get("role_overview", "")

        scope = data.get("where_you_will", "")
        if scope and len(scope) > 0:
            scope = scope[0].upper() + scope[1:]

        highlights_parts = [p for p in [pay, commitment, location] if p]
        highlights = " | ".join(highlights_parts)
        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I’m reaching out from <b>Capitex AI</b> to refer you for the role of {link_html} at <b>Mercor</b>.<br><br>

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

<b>Apply Here:</b> {link_html}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For immediate support, contact support@mercor.com</i><br><br>

Best Regards,<br>
CapitexAI""".strip()
        return omit_empty_html_sections(email)


class STEMSyncAIFormatter(MercorFormatter):
    """Page 7: STEMSyncAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        role = data.get("role", "")
        location = "Remote"
        role_type = data.get("type", "")
        pay = data.get("pay", "")
        commitment = data.get("commitment", "")
        detail_parts = [part for part in [location, role_type, pay, commitment] if part]
        details = " | ".join(detail_parts)
        highlights = f"{role} — {details}" if role and details else role or details

        snapshots = data.get("role_responsibilities", [])
        snapshot_bullets = "\n".join([f"<li>{s}</li>" for s in snapshots if s and s.strip()])
        snapshot_section = (
            f"<b>Quick Snapshot</b>\n<ul>\n{snapshot_bullets}\n</ul><br>"
            if snapshot_bullets else ""
        )

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])
        requirements_section = (
            f"<b>Requirements</b>\n<ul>\n{req_bullets}\n</ul><br>"
            if req_bullets else ""
        )

        jd_text = f"""<b>{highlights}</b><br><br>

{snapshot_section}

{requirements_section}

<b>Application Process</b>
<ul>
<li>Apply for the opportunity using the Easy Apply button.</li>
<li>Applications will be evaluated based on the requirements of the opportunity.</li>
<li>Candidates selected to proceed will receive an email with additional instructions.</li>
<li>Use the instructions in the email to complete the remaining application steps.</li>
</ul><br>

#LI-CH""".strip()
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        role_type = data.get("type", "")
        location = "Remote"

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        highlights = " | ".join(part for part in [location, role_type, pay] if part)
        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I'm from <b>STEMSyncAI</b> and would like to refer you for the role of {link_html} at <b>Mercor</b>.<br><br>

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
{link_html}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. Incase of any queries please reach out to Mercor support at support@mercor.com.</i><br><br>

Best Regards,<br>
STEMSyncAI""".strip()
        return omit_empty_html_sections(email)


class LinguaSenseAIFormatter(MercorFormatter):
    """Page 8 & 9: LinguaSenseAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        overview = data.get("role_overview", "")
        role_type = data.get("type", "")
        pay = data.get("pay", "")
        location = "Remote"
        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        jd_text = f"""<b>Objective</b><br>
{overview}<br><br>

<b>Opportunity Details</b><br>
<b>Job Format:</b> {role_type}<br>
{pay_row}
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
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        role_type = data.get("type", "")
        location = "Remote"
        overview = data.get("role_overview", "")

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""
        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I'm from <b>LinguaSenseAI</b> and reaching out to refer you for a {link_html} opportunity at <b>Mercor</b>.<br><br>

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

<b>Click here to complete your application for: {link_html}</b><br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. If you have any queries, you can contact Mercor support at support@mercor.com.</i><br><br>

Best Regards,<br>
LinguaSenseAI""".strip()
        return omit_empty_html_sections(email)


class DesignMeshAIFormatter(MercorFormatter):
    """Page 10 & 11: DesignMeshAI JD & InMail Draft"""
    def format_jd(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=True)
        role = data.get("role", "")
        overview = data.get("role_overview", "")

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        role_type = data.get("type", "")
        pay = data.get("pay", "")
        location = "Remote"
        pay_row = f"<b>Compensation:</b> {pay}<br>\n" if pay else ""

        jd_text = f"""<b>{role}</b><br><br>
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
{pay_row}
<b>Work Setup:</b> {location}<br><br>

<b>Application Process</b>
<ul>
<li>Complete your application using the Easy Apply button.</li>
<li>Your application will be reviewed according to the role requirements.</li>
<li>Qualified candidates will receive an email outlining the next stage of the application process.</li>
<li>Follow the instructions in the email to proceed with the remaining steps.</li>
</ul><br>

#LI-CH""".strip()
        return scrub_all_client_orgs_from_jd(jd_text)

    def format_email(self, data: dict) -> str:
        data = sanitize_format_data(data, is_jd=False)
        role = data.get("role", "")
        link = data.get("link", "")
        pay = data.get("pay", "")
        role_type = data.get("type", "")
        location = "Remote"
        overview = data.get("role_overview", "")

        resps = data.get("role_responsibilities", [])
        resp_bullets = "\n".join([f"<li>{r}</li>" for r in resps if r and r.strip()])

        reqs = data.get("requirements", [])
        req_bullets = "\n".join([f"<li>{r}</li>" for r in reqs if r and r.strip()])

        pay_row = f"<b>Pay:</b> {pay}<br>\n" if pay else ""
        link_html = make_blue_link(link, role)

        email = f"""Hi {{firstName}},<br><br>

I'm reaching out from <b>DesignMeshAI</b> to refer you for the role of {link_html} at <b>Mercor</b>.<br><br>

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

<b>Apply here:</b> {link_html}<br><br>

<b>You can also checkout these Opportunities as well:</b><br><br>

<i>P.S. For immediate support, contact support@mercor.com</i><br><br>

Best Regards,<br>
DesignMeshAI""".strip()
        return omit_empty_html_sections(email)
