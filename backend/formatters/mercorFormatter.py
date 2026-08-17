"""
Mercor formatter — produces HTML job description and outreach email.
Extracted verbatim from the original llm_jd_parser.py render_jd / render_email
(Mercor branch) to preserve 100% backward compatibility.
"""

try:
    from .base import ClientFormatter, prepare_html_data
except ImportError:
    from formatters.base import ClientFormatter, prepare_html_data


class MercorFormatter(ClientFormatter):

    def format_jd(self, data: dict) -> str:
        data = prepare_html_data(data)
        responsibilities = "\n".join(
            [f"<li>{r}</li>" for r in data["role_responsibilities"] if r and str(r).strip()]
        )
        requirements = "\n".join(
            [f"<li>{r}</li>" for r in data["requirements"] if r and str(r).strip()]
        )
        responsibilities_section = (
            f"<b>Role Responsibilities</b>\n<ul>\n{responsibilities}\n</ul>\n"
            if responsibilities else ""
        )
        requirements_section = (
            f"<b>Requirements</b>\n<ul>\n{requirements}\n</ul>\n"
            if requirements else ""
        )

        commitment = data.get("commitment", "").strip()
        commitment_line = f"<b>Commitment:</b> {commitment}<br>\n" if commitment else ""

        pay = data.get("pay", "").strip()
        pay_line = f"<b>Compensation:</b> {pay}<br>\n" if pay else ""
        role_type = data.get("type", "").strip()
        type_line = f"<b>Type:</b> {role_type}<br>\n" if role_type else ""

        app_process = """<b>Application Process</b><br>
<ul>
<li>Upload resume</li>
<li>Interview</li>
<li>Submit form</li>
</ul>"""

        jd_text = f"""<b>Position:</b> {data['role']}<br>
{type_line}
{pay_line}<b>Location:</b> {data['location']}<br>
{commitment_line}
<br>

{responsibilities_section}
{requirements_section}

<br>

{app_process}

<br>

#LI-CH"""
        return jd_text.strip()

    def format_email(self, data: dict) -> str:
        data = prepare_html_data(data)
        boost_items = []
        boost_items.append("""\
<li>
Need tips to improve your chances of selection? Check out the \
<a href="https://docs.google.com/document/d/1xYe9X4t2Bv6BEScXwwvix35Kmlc92xiulEpBDLcCZb8/edit?usp=sharing" style="color: #0066cc;">\
Interview Preparation Playbook\
</a>
</li>""")
        boost_items.append("""\
<li>
You can strengthen your profile through the \
<a href="https://work.mercor.com/home?tab=assessments&referralCode=c88e7e37-c849-4793-a401-f58c8615e4c7" style="color: #0066cc;">\
Assessment tab\
</a> in your dashboard. Completing skill based assessments can help unlock future opportunities, \
including roles you have not applied to or roles that may not be publicly listed.
</li>""")
        boost_items.append("""\
<li>
You may also explore additional opportunities with \
<a href="https://t.mercor.com/cU1Py" style="color: #0066cc;">Mercor</a> and \
<a href="https://refer.micro1.ai/referral/jobs?referralCode=463495f6-7cc6-49ed-8e8f-5ef2a1cc3fd7&utm_source=referral&utm_medium=share&utm_campaign=job_referral" style="color: #0066cc;">Micro1</a>, \
both platforms connecting skilled professionals to AI training projects.
</li>""")
        boost_items.append("""\
<li>
For regular updates, you can follow our \
<a href="https://whatsapp.com/channel/0029Vb6eLrf23n3gz313El2h" style="color: #0066cc;">WhatsApp channel</a> \
for upcoming openings.
</li>""")

        boost_section = "\n\n".join(boost_items)
        pay_line = f"<b>Compensation:</b> {data.get('pay', '')}<br>\n" if data.get("pay") else ""
        referral_partner = "<b>Referral Partner:</b> Crossing Hurdles<br>\n"
        role_type = data.get("type", "").strip()
        type_line = f"<b>Type:</b> {role_type}<br>\n" if role_type else ""
        client = data.get("client", "").strip()
        organization_line = f"<b>Organization:</b> {client}<br>\n" if client else ""
        client_desc = data.get("client_desc", "").strip()
        about_section = (
            f"<b>About {client}:</b><br>\n{client_desc}<br><br>\n"
            if client and client_desc else ""
        )
        role_overview = data.get("role_overview", "").strip()
        overview_section = (
            f"<b>Role Overview:</b><br>\n{role_overview}<br><br>\n"
            if role_overview else ""
        )
        who_this_is_for = data.get("who_this_is_for", "").strip()
        audience_section = (
            f"<b>Who This Is For:</b><br>\n{who_this_is_for}<br><br>\n"
            if who_this_is_for else ""
        )
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
            f"<a href=\"{data['link']}\" style=\"color: #0066cc;\">{data['role']}</a>{pay_display}<br><br>"
        ) if data.get("link") else ""
        apply_here_line = (
            f'<b>Apply Here:</b> <a href="{data["link"]}" style="color: #0066cc;">{data["role"]}</a><br><br>\n'
            if data.get("link") else ""
        )

        return f"""<br>I'm from Crossing Hurdles, a global recruitment firm. We would like to refer you for an interesting opportunity that involves leveraging your expertise to train AI models.<br><br>

{organization_line}
{referral_partner}<b>Role:</b> {data['role']}<br>
{type_line}
{pay_line}<b>Location:</b> {data['location']}<br>
{apply_here_line}

{about_section}{overview_section}{audience_section}

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
