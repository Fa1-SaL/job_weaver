"""
Formatters for the 8 Domain Pages.
Each formatter subclasses MercorFormatter so `format_jd` produces standard Mercor JD formatting,
while `format_email` generates the tailored InMail Draft exact to the PDF specification.
"""

from formatters.mercorFormatter import MercorFormatter


class CrossingHurdlesFormatter(MercorFormatter):
    """Page 1: Crossing Hurdles InMail Draft"""
    def format_email(self, data: dict) -> str:
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
    """Page 2: CodeGeniusRecruit InMail Draft"""
    def format_email(self, data: dict) -> str:
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
    """Page 3 & 4: CuraSenseAI InMail Draft"""
    def format_email(self, data: dict) -> str:
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
    """Page 5: LegalTrustAI InMail Draft"""
    def format_email(self, data: dict) -> str:
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
    """Page 6: CapitexAI InMail Draft"""
    def format_email(self, data: dict) -> str:
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

I’m reaching out from <b>Capitex</b> to refer you for the role of <a href="{link}"><b>{role}</b></a> at <b>Mercor</b>.<br><br>

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
    """Page 7: STEMSyncAI InMail Draft"""
    def format_email(self, data: dict) -> str:
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
    """Page 8 & 9: LinguaSenseAI InMail Draft"""
    def format_email(self, data: dict) -> str:
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
    """Page 10 & 11: DesignMeshAI InMail Draft"""
    def format_email(self, data: dict) -> str:
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
