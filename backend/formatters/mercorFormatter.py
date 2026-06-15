"""
Mercor formatter — produces HTML job description and outreach email.
Extracted verbatim from the original llm_jd_parser.py render_jd / render_email
(Mercor branch) to preserve 100% backward compatibility.
"""

from formatters.base import ClientFormatter


class MercorFormatter(ClientFormatter):

    def format_jd(self, data: dict) -> str:
        responsibilities = "\n".join(
            [f"<li>{r}</li>" for r in data["role_responsibilities"] if r and r.strip()]
        )
        requirements = "\n".join(
            [f"<li>{r}</li>" for r in data["requirements"] if r and r.strip()]
        )

        commitment = data.get("commitment", "").strip()
        commitment_line = f"<b>Commitment:</b> {commitment}<br>\n" if commitment else ""

        pay_line = f"<b>Compensation:</b> {data.get('pay', '')}<br>\n"

        app_process = """<b>Application Process</b><br>
<ul>
<li>Upload resume</li>
<li>Interview</li>
<li>Submit form</li>
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
        boost_items = []
        boost_items.append("""\
<li>
Need tips to improve your chances of selection? Check out the \
<a href="https://docs.google.com/document/d/1xYe9X4t2Bv6BEScXwwvix35Kmlc92xiulEpBDLcCZb8/edit?usp=sharing">\
Interview Preparation Playbook\
</a>
</li>""")
        boost_items.append("""\
<li>
You can strengthen your profile through the \
<a href="https://work.mercor.com/home?tab=assessments&referralCode=c88e7e37-c849-4793-a401-f58c8615e4c7">\
Assessment tab\
</a> in your dashboard. Completing skill based assessments can help unlock future opportunities, \
including roles you have not applied to or roles that may not be publicly listed.
</li>""")
        boost_items.append("""\
<li>
You may also explore additional opportunities with \
<a href="https://t.mercor.com/cU1Py">Mercor</a> and \
<a href="https://refer.micro1.ai/referral/jobs?referralCode=463495f6-7cc6-49ed-8e8f-5ef2a1cc3fd7\
&utm_source=referral&utm_medium=share&utm_campaign=job_referral">Micro1</a>, \
both platforms connecting skilled professionals to AI training projects.
</li>""")
        boost_items.append("""\
<li>
For regular updates, you can follow our \
<a href="https://whatsapp.com/channel/0029Vb6eLrf23n3gz313El2h">WhatsApp channel</a> \
for upcoming openings.
</li>""")

        boost_section = "\n\n".join(boost_items)
        pay_line = f"<b>Compensation:</b> {data.get('pay', '')}<br>\n"
        referral_partner = "<b>Referral Partner:</b> Crossing Hurdles<br>\n"
        app_process = """\
<b>Application process:</b> (~20 Min)<br>
<ul>
<li>Upload resume</li>
<li>Interview</li>
<li>Submit form</li>
</ul><br>"""

        pay_display = f" – {data['pay']}" if data.get("pay") else ""
        apply_line = (
            f"<b>Apply asap (reviewed on a rolling basis):</b><br>\n"
            f"<a href=\"{data['link']}\">{data['role']}</a>{pay_display}<br><br>"
        )

        return f"""<br>I'm from Crossing Hurdles, a global recruitment firm. We would like to refer you for an interesting opportunity that involves leveraging your expertise to train AI models.<br><br>

<b>Organization:</b> {data['client']}<br>
{referral_partner}<b>Role:</b> {data['role']}<br>
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
Meanwhile, for immediate assistance, please reach out to support@mercor.com
</i>""".strip()
