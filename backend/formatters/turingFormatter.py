"""
Turing formatter — produces HTML job description and outreach email.
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
        role = clean_position(data.get('role', ''))
        location = data.get('location', '').strip()
        loc_lower = location.lower()
        if "onsite" in loc_lower or "on-site" in loc_lower or "hybrid" in loc_lower:
            pass
        else:
            location = "Remote"

        commitment = data.get("commitment", "10–40 hrs/week").strip() or "10–40 hrs/week"
        pay = data.get("pay", "").strip()
        pay_line = f"<b>Compensation:</b> {pay}<br>\n" if pay else "<b>Compensation:</b> To be discussed<br>\n"

        responsibilities = "\n".join(
            [f"<li>{r}</li>" for r in data.get("role_responsibilities", []) if r and r.strip()]
        )
        requirements = "\n".join(
            [f"<li>{r}</li>" for r in data.get("requirements", []) if r and r.strip()]
        )

        app_process = """<b>Application Process</b><br>
<ul>
<li>Easy Apply on Linkedin</li>
<li>Check email for next steps</li>
</ul>"""

        jd_text = f"""<b>Position:</b> {role}<br>
<b>Type:</b> {data.get('type', '').strip()}<br>
{pay_line}<b>Location:</b> {location}<br>
<b>Commitment:</b> {commitment}<br>
<br>

<b>Role Responsibilities</b>
<ul>
{responsibilities}
</ul>

<b>Requirements</b>
<ul>
{requirements}
</ul>

<br>

{app_process}"""
        return jd_text.strip()

    def format_email(self, data: dict) -> str:
        link = data.get("link", "").strip()
        role = clean_position(data.get("role", ""))
        client_name = data.get("client", "Turing")
        about_desc = data.get("client_desc", "").strip()
        if not about_desc or "talent solutions" in about_desc.lower():
            about_desc = (
                "Turing is a leading AI company accelerating the advancement of frontier AI systems. "
                "It partners with top AI labs and global enterprises to improve model capabilities "
                "across reasoning, coding, and real-world system integration."
            )
        role_overview = data.get("role_overview", "").strip()
        who_this_is_for = data.get("who_this_is_for", "").strip()

        article = get_article(role)
        where_you_will = data.get("where_you_will", "").strip()
        if not where_you_will:
            where_you_will = "contribute to training advanced AI models and ensuring high-quality system integration"

        intro = f"I am from Crossing Hurdles, a global recruitment firm. We would like to refer you for an exciting opportunity with Turing as {article} <b>{role}</b>, where you will {where_you_will}."

        location = data.get("location", "").strip()
        loc_lower = location.lower()
        if "onsite" in loc_lower or "on-site" in loc_lower or "hybrid" in loc_lower:
            pass
        else:
            location = "Remote"

        job_type = data.get("type", "").strip()
        if job_type and location:
            type_display = f"{job_type} | {location}"
        elif job_type:
            type_display = job_type
        else:
            type_display = location

        pay = data.get("pay", "").strip()
        pay_display = pay if pay else "To be discussed"

        commitment = data.get("commitment", "10–40 hrs/week").strip() or "10–40 hrs/week"
        commitment = commitment.replace("-", "–")
        if "remote" in location.lower() and "pst overlap" not in commitment.lower():
            commitment = f"{commitment} | Min. 6-hour PST overlap"

        apply_link = f'<a href="{link}">{role}</a>' if link else role

        if link:
            how_to_apply_bullets = f'<li>Submit your application through the following <a href="{link}">link</a></li>'
        else:
            how_to_apply_bullets = '<li>Submit your application through the referral link</li>'

        how_to_apply = f"""<b>How to Apply:</b><br>
<ul>
{how_to_apply_bullets}
<li>Shortlisted candidates will be required to complete an assessment/interview.</li>
<li>Candidates demonstrating strong performance will advance to the pre-onboarding stage.</li>
</ul>"""

        boost_profile = """<b>Take Steps to Boost Your Profile:</b><br>
<ul>
<li>You may also explore additional opportunities with <a href="https://t.mercor.com/cU1Py">Mercor</a> and <a href="https://refer.micro1.ai/referral/jobs?referralCode=463495f6-7cc6-49ed-8e8f-5ef2a1cc3fd7&utm_source=referral&utm_medium=share&utm_campaign=job_referral">Micro1</a>, both platforms connecting skilled professionals to AI training projects.</li>
<li>For regular updates, you can follow our <a href="https://whatsapp.com/channel/0029Vb6eLrf23n3gz313El2h">WhatsApp channel</a> for upcoming openings.</li>
</ul>"""

        footer = f"""<i>P.S. We're committed to addressing your queries, though responses may take longer than usual. Meanwhile, for immediate assistance, please reach out to <a href="mailto:support@turing.com">support@turing.com</a></i>"""

        email_html = f"""{intro}<br>
<br>
<b>Organization:</b> {client_name}<br>
<b>Hiring Partner:</b> Crossing Hurdles<br>
<b>Role:</b> {role}<br>
<b>Type:</b> {type_display}<br>
<b>Pay:</b> {pay_display}<br>
<b>Commitment:</b> {commitment}<br>
<b>Apply:</b> {apply_link}<br>
<br>
<b>About {client_name}:</b><br>
{about_desc}<br>
<br>
<b>Role Overview:</b><br>
{role_overview}<br>
<br>
<b>Who This Is For:</b><br>
{who_this_is_for}<br>
<br>
{how_to_apply}
<br>
{boost_profile}
<br>
{footer}"""

        return email_html.strip()


