"""
Turing formatter — produces HTML job description (InMail) and outreach email.
Based on standard Turing recruitment structure.
"""

import re
from formatters.base import ClientFormatter


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
        role = clean_position(data.get('role', ''))
        job_type = data.get('type', 'Short-Term Contract').strip() or 'Short-Term Contract'
        location = data.get('location', '').strip()
        loc_lower = location.lower()
        if not ("onsite" in loc_lower or "on-site" in loc_lower or "hybrid" in loc_lower):
            location = "Remote"

        commitment = data.get("commitment", "Flexible 40 hrs/week with a minimum 4-hour overlap with PST").strip()
        if not commitment:
            commitment = "Flexible 40 hrs/week with a minimum 4-hour overlap with PST"

        pay = data.get("pay", "").strip()
        pay_line = f"<b>Compensation:</b> {pay}<br>" if pay else "<b>Compensation:</b> To be discussed<br>"

        resps = data.get("role_responsibilities", [])
        responsibilities = "\n".join(
            [f"<li>{r}</li>" for r in resps if r and str(r).strip()]
        )
        reqs = data.get("requirements", [])
        requirements = "\n".join(
            [f"<li>{r}</li>" for r in reqs if r and str(r).strip()]
        )

        app_process = """<b>Application Process</b>
<ul>
<li>Apply via Easy Apply</li>
<li>Check email for next steps</li>
</ul>"""

        jd_text = f"""<b>Position:</b> {role}<br>
<b>Type:</b> {job_type}<br>
{pay_line}<b>Location:</b> {location}<br>
<b>Commitment:</b> {commitment}<br>
<br>

<b>Role Responsibilities:</b>
<ul>
{responsibilities}
</ul>
<br>

<b>Requirements:</b>
<ul>
{requirements}
</ul>
<br>

{app_process}
<br>
#LI-CH"""
        return jd_text.strip()

    def format_email(self, data: dict) -> str:
        """Outreach Email structure matching Turing specifications."""
        link = data.get("link", "").strip()
        role = clean_position(data.get("role", ""))
        client_name = data.get("client", "Turing") or "Turing"
        about_desc = data.get("client_desc", "").strip()
        if not about_desc or "talent solutions" in about_desc.lower():
            about_desc = (
                "Turing is the world’s leading research accelerator for frontier AI labs "
                "and a trusted partner for global enterprises deploying advanced AI systems. "
                "Turing supports organizations by accelerating frontier AI research through high-quality data, "
                "advanced training pipelines, and expert talent specializing in STEM, reasoning, multilinguality, "
                "multimodality, coding, and AI agents."
            )

        role_overview = data.get("role_overview", "").strip()
        who_this_is_for = data.get("who_this_is_for", "").strip()

        article = get_article(role)
        where_you_will = data.get("where_you_will", "").strip()
        if not where_you_will:
            where_you_will = "help train and evaluate cutting-edge AI systems using specialized reasoning tasks"

        intro = (
            f"I’m from Crossing Hurdles, a global recruitment firm. We would like to refer you for an "
            f"exciting short-term contract opportunity with Turing as {article} <b>{role}</b>, where you will {where_you_will}."
        )

        location = data.get("location", "").strip()
        loc_lower = location.lower()
        if not ("onsite" in loc_lower or "on-site" in loc_lower or "hybrid" in loc_lower):
            location = "Remote"

        job_type = data.get("type", "").strip() or "Short-Term Contract"
        pay = data.get("pay", "").strip() or "$17 per hour"
        commitment = data.get("commitment", "").strip() or "Flexible 40 hrs/week with a minimum 4-hour overlap with PST"
        start_date = data.get("start_date", "").strip() or "Immediate"

        if link:
            apply_link_html = f'<a href="{link}" style="color: #0066cc;">Apply Here</a>'
            click_here_html = f'<a href="{link}" style="color: #0066cc;">clicking here</a>'
        else:
            apply_link_html = 'Apply Here'
            click_here_html = 'clicking here'

        # Responsibilities bullets ("What You'll Work On:")
        resps = data.get("role_responsibilities", [])
        if resps:
            resps_html = "\n".join([f"<li>{r}</li>" for r in resps if r and str(r).strip()])
        else:
            resps_html = "<li>Review, classify, label, and validate data according to detailed project guidelines.</li>"

        # Requirements bullets ("Who This Is For:")
        reqs = data.get("requirements", [])
        if reqs:
            reqs_html = "\n".join([f"<li>{r}</li>" for r in reqs if r and str(r).strip()])
        elif who_this_is_for and isinstance(who_this_is_for, list):
            reqs_html = "\n".join([f"<li>{r}</li>" for r in who_this_is_for if r and str(r).strip()])
        elif who_this_is_for and isinstance(who_this_is_for, str):
            reqs_html = f"<li>{who_this_is_for}</li>"
        else:
            reqs_html = "<li>Professionals with relevant analytical and domain expertise.</li>"

        # Preferred Qualifications section (if provided)
        pref_qual = data.get("preferred_qualifications", [])
        pref_qual_html = ""
        if pref_qual and isinstance(pref_qual, list) and len(pref_qual) > 0:
            pref_bullets = "\n".join([f"<li>{q}</li>" for q in pref_qual if q and str(q).strip()])
            pref_qual_html = f"<b>Preferred Qualifications:</b><br>\n<ul>\n{pref_bullets}\n</ul><br>\n<br>\n"

        email_html = f"""{intro}<br>
<br>
<b>Organization:</b> {client_name}<br>
<b>Referral Partner:</b> Crossing Hurdles<br>
<b>Role:</b> {role}<br>
<b>Type:</b> {job_type}<br>
<b>Compensation:</b> {pay}<br>
<b>Location:</b> {location}<br>
<b>Work Schedule:</b> {commitment}<br>
<b>Start Date:</b> {start_date}<br>
<b>Application Form Link – {apply_link_html}</b><br>
<br>
<b>About {client_name}:</b><br>
{about_desc}<br>
<br>
<b>Role Overview:</b><br>
{role_overview}<br>
<br>
<b>What You'll Work On:</b><br>
<ul>
{resps_html}
</ul>
<br>
<b>Who This Is For:</b><br>
<ul>
{reqs_html}
</ul>
<br>
{pref_qual_html}<b>Application Process:</b><br>
Complete the application form by {click_here_html} to apply for the role.<br>
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
