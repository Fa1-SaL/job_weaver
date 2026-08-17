"""
Turing formatter — produces HTML job description (InMail) and outreach email.
Based on standard Turing recruitment structure.
"""

import re
try:
    from .base import ClientFormatter, prepare_html_data
except ImportError:
    from formatters.base import ClientFormatter, prepare_html_data


def clean_position(role: str) -> str:
    if not role:
        return ""
    # Remove leading ID pattern like "ID: 12345 |" or "ID: 12345 -"
    role = re.sub(r'^ID:\s*\d+\s*[|\-]\s*', '', role, flags=re.IGNORECASE)
    # Remove trailing parentheticals or bracketed expressions
    while True:
        cleaned = re.sub(r'\s*[\(\[][^\]\)]*[\)\]]\s*$', '', role)
        if cleaned == role:
            break
        role = cleaned
    return role.strip()


def get_article(role: str) -> str:
    if not role:
        return "a"
    first_word = role.split()[0].upper()
    if first_word[0] in "AEIOU":
        return "an"
    if len(first_word) > 1 and first_word[0] in "FHLMNRSX" and first_word.isupper():
        return "an"
    if first_word.startswith("MCP"):
        return "an"
    return "a"


class TuringFormatter(ClientFormatter):

    def format_jd(self, data: dict) -> str:
        """InMail / Formatted JD structure matching Turing specifications."""
        data = prepare_html_data(data)
        role = clean_position(data.get('role', ''))
        job_type = data.get('type', '').strip()
        location = "Remote"
        type_line = f"<b>Type:</b> {job_type}<br>\n" if job_type else ""

        commitment = data.get("commitment", "10-40 hrs/week").strip()
        if not commitment:
            commitment = "10-40 hrs/week"

        pay = data.get("pay", "").strip()
        pay_line = f"<b>Compensation:</b> {pay}<br>" if pay else ""

        resps = data.get("role_responsibilities", [])
        responsibilities = "\n".join(
            [f"<li>{r}</li>" for r in resps if r and str(r).strip()]
        )
        reqs = data.get("requirements", [])
        requirements = "\n".join(
            [f"<li>{r}</li>" for r in reqs if r and str(r).strip()]
        )
        responsibilities_section = (
            f"<b>Role Responsibilities:</b>\n<ul>\n{responsibilities}\n</ul>\n<br>\n"
            if responsibilities else ""
        )
        requirements_section = (
            f"<b>Requirements:</b>\n<ul>\n{requirements}\n</ul>\n<br>\n"
            if requirements else ""
        )

        app_process = """<b>Application Process</b>
<ul>
<li>Apply via Easy Apply</li>
<li>Check email for next steps</li>
</ul>"""

        jd_text = f"""<b>Position:</b> {role}<br>
{type_line}
{pay_line}<b>Location:</b> {location}<br>
<b>Commitment:</b> {commitment}<br>
<br>

{responsibilities_section}
{requirements_section}

{app_process}
<br>
#LI-CH"""
        return jd_text.strip()

    def format_email(self, data: dict) -> str:
        """Outreach Email structure matching Turing specifications."""
        data = prepare_html_data(data)
        link = data.get("link", "").strip()
        role = clean_position(data.get("role", ""))
        client_name = data.get("client", "Turing") or "Turing"
        about_desc = data.get("client_desc", "").strip()

        role_overview = data.get("role_overview", "").strip()
        who_this_is_for = data.get("who_this_is_for", "").strip()

        article = get_article(role)
        where_you_will = data.get("where_you_will", "").strip()
        work_clause = f", where you will {where_you_will}" if where_you_will else ""

        intro = (
            f"I’m from Crossing Hurdles, a global recruitment firm. We would like to refer you for an "
            f"exciting opportunity with Turing as {article} <b>{role}</b>{work_clause}."
        )

        location = "Remote"

        job_type = data.get("type", "").strip()
        pay = data.get("pay", "").strip()
        commitment = data.get("commitment", "").strip() or "10-40 hrs/week"
        start_date = data.get("start_date", "").strip()
        type_line = f"<b>Type:</b> {job_type}<br>\n" if job_type else ""
        start_line = f"<b>Start Date:</b> {start_date}<br>\n" if start_date else ""
        about_section = (
            f"<b>About {client_name}:</b><br>\n{about_desc}<br>\n<br>\n"
            if about_desc else ""
        )
        overview_section = (
            f"<b>Role Overview:</b><br>\n{role_overview}<br>\n<br>\n"
            if role_overview else ""
        )

        if link:
            apply_link_html = f'<a href="{link}" style="color: #0066cc;">Apply Here</a>'
            click_here_html = f'<a href="{link}" style="color: #0066cc;">clicking here</a>'
            application_link_line = f"<b>Application Form Link – {apply_link_html}</b><br>\n"
            application_action = f"Complete the application form by {click_here_html} to apply for the role."
        else:
            application_link_line = ""
            application_action = "Complete the application form to apply for the role."

        # Responsibilities bullets ("What You'll Work On:")
        resps = data.get("role_responsibilities", [])
        if resps:
            resps_html = "\n".join([f"<li>{r}</li>" for r in resps if r and str(r).strip()])
        else:
            resps_html = ""

        # Requirements bullets ("Who This Is For:")
        reqs = data.get("requirements", [])
        if reqs:
            reqs_html = "\n".join([f"<li>{r}</li>" for r in reqs if r and str(r).strip()])
        elif who_this_is_for and isinstance(who_this_is_for, list):
            reqs_html = "\n".join([f"<li>{r}</li>" for r in who_this_is_for if r and str(r).strip()])
        elif who_this_is_for and isinstance(who_this_is_for, str):
            reqs_html = f"<li>{who_this_is_for}</li>"
        else:
            reqs_html = ""
        resps_section = (
            f"<b>What You'll Work On:</b><br>\n<ul>\n{resps_html}\n</ul>\n<br>\n"
            if resps_html else ""
        )
        reqs_section = (
            f"<b>Who This Is For:</b><br>\n<ul>\n{reqs_html}\n</ul>\n<br>\n"
            if reqs_html else ""
        )

        # Preferred Qualifications section (if provided)
        pref_qual = [
            item for item in data.get("preferred_qualifications", [])
            if item and str(item).strip()
        ]
        pref_qual_html = ""
        if pref_qual and isinstance(pref_qual, list) and len(pref_qual) > 0:
            pref_bullets = "\n".join([f"<li>{q}</li>" for q in pref_qual if q and str(q).strip()])
            pref_qual_html = f"<b>Preferred Qualifications:</b><br>\n<ul>\n{pref_bullets}\n</ul><br>\n<br>\n"

        email_html = f"""{intro}<br>
<br>
<b>Organization:</b> {client_name}<br>
<b>Referral Partner:</b> Crossing Hurdles<br>
<b>Role:</b> {role}<br>
{type_line}
{f'<b>Compensation:</b> {pay}<br>' if pay else ''}
<b>Location:</b> {location}<br>
<b>Work Schedule:</b> {commitment}<br>
{start_line}
{application_link_line}
<br>
{about_section}{overview_section}{resps_section}{reqs_section}
{pref_qual_html}<b>Application Process:</b><br>
{application_action}<br>
<br>
<b>Assessment Process (After Shortlisting):</b><br>
Shortlisted candidates will receive a Take Home Assessment. Candidates who successfully clear the assessment will proceed to the Delivery Review stage. Successful candidates will then be contacted regarding onboarding.<br>
<br>
<b>Take Steps to Boost Your Profile:</b><br>
<ul>
<li>You may also explore additional opportunities with <a href="https://t.mercor.com/cU1Py" style="color: #0066cc;">Mercor</a> and <a href="https://refer.micro1.ai/referral/jobs?referralCode=463495f6-7cc6-49ed-8e8f-5ef2a1cc3fd7&utm_source=referral&utm_medium=share&utm_campaign=job_referral" style="color: #0066cc;">Micro1</a>, both platforms connecting skilled professionals to AI training projects.</li>
<li>For regular updates, you can follow our <a href="https://whatsapp.com/channel/0029Vb6eLrf23n3gz313El2h" style="color: #0066cc;">WhatsApp channel</a> for upcoming openings.</li>
</ul>
<br>
<i>P.S. We're committed to addressing your queries, though responses may take longer than usual. Meanwhile, for immediate assistance, please reach out to <a href="mailto:support@turing.com" style="color: #0066cc;">support@turing.com</a></i>"""

        return email_html.strip()
