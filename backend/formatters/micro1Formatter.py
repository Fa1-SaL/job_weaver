"""
Micro1 formatter — produces HTML job description and outreach email.
Extracted verbatim from the original llm_jd_parser.py render_jd / render_email
(Micro1 branch) to preserve 100% backward compatibility.
"""

from formatters.base import ClientFormatter


class Micro1Formatter(ClientFormatter):

    def format_jd(self, data: dict) -> str:
        responsibilities = "\n".join(
            [f"<li>{r}</li>" for r in data["role_responsibilities"] if r and r.strip()]
        )
        requirements = "\n".join(
            [f"<li>{r}</li>" for r in data["requirements"] if r and r.strip()]
        )

        commitment = data.get("commitment", "").strip()
        commitment_line = f"<b>Commitment:</b> {commitment}<br>\n" if commitment else ""

        pay_line = f"<b>Compensation:</b> {data['pay']}<br>\n" if data.get("pay") else ""

        app_process = """\
<b>Application Process</b><br>
<ul>
<li>Easy Apply on LinkedIn</li>
<li>Check email for next steps</li>
<li>Participate in resume evaluation &amp; interview stage</li>
</ul>"""

        jd_text = f"""<b>Position:</b> {data['role']}<br>
<b>Type:</b> {data['type']}<br>
{pay_line}<b>Location:</b> {data['location']}<br>
{commitment_line}
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

{app_process}

<br>

#LI-CH"""
        return jd_text.strip()

    def format_email(self, data: dict) -> str:
        boost_section = """\
<li>
You may also explore additional opportunities with \
<a href="https://refer.micro1.ai/referral/jobs?referralCode=463495f6-7cc6-49ed-8e8f-5ef2a1cc3fd7\
&utm_source=referral&utm_medium=share&utm_campaign=job_referral">Micro1</a>.
</li>
<li>
For regular updates, you can follow our \
<a href="https://whatsapp.com/channel/0029Vb6eLrf23n3gz313El2h">WhatsApp channel</a> \
for upcoming openings.
</li>"""

        pay_line = f"<b>Compensation:</b> {data['pay']}<br>\n" if data.get("pay") else ""
        app_process = """\
<b>Application process:</b><br>
<ul>
<li>Participate in resume evaluation &amp; interview stage</li>
</ul><br>"""

        pay_display = f" – {data['pay']}" if data.get("pay") else ""
        apply_line = (
            f"<b>Apply asap (reviewed on a rolling basis):</b><br>\n"
            f"<a href=\"{data['link']}\">{data['role']}</a>{pay_display}<br><br>"
        )

        return f"""<br>I'm from Crossing Hurdles, a global recruitment firm. We would like to refer you for an interesting opportunity that involves leveraging your expertise to train AI models.<br><br>

<b>Organization:</b> {data['client']}<br>
<b>Role:</b> {data['role']}<br>
<b>Type:</b> {data['type']}<br>
{pay_line}<b>Location:</b> {data['location']}<br>
<b>Apply Here:</b> <a href="{data['link']}">{data['role']}</a><br><br>

<b>About {data['client']}:</b><br>
{data['client_desc']}<br><br>

<b>Role Overview:</b><br>
{data['role_overview']}<br><br>

<b>Who This Is For:</b><br>
{data['who_this_is_for']}<br><br>

{app_process}
{apply_line}
<b>Take Steps to Boost Your Profile:</b>
<ul>
{boost_section}
</ul>

<br>

<i>
P.S. We're committed to addressing your queries, though responses may take longer than usual. \
Meanwhile, for immediate assistance, please reach out to support@micro1.ai
</i>""".strip()
