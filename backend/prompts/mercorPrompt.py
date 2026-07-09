"""
Mercor LLM extraction prompt.

This is the canonical extraction prompt used for Mercor jobs.
It instructs the model to return a strict JSON object with all required fields.
"""

PROMPT_TEMPLATE = """\
You are a structured data extractor for recruitment.

Extract ONLY the required variables from the job description.

Output strictly in JSON.
Do NOT generate formatted email or job description.

Expected JSON structure:

{
  "role": "",
  "type": "",
  "pay": "",
  "location": "",
  "commitment": "",
  "role_responsibilities": [],
  "requirements": [],
  "role_overview": "",
  "who_this_is_for": "",
  "client": "{CLIENT_NAME}",
  "client_desc": "short company description",
  "link": "application/referral link if available",
  "suggested_titles": [],
  "subject": "",
  "linkedin_title": "",
  "skills": [],
  "job_functions": ["", "", ""],
  "industries": ["", "", ""],
  "justifications": {}
}

Rules:
- responsibilities and requirements must be lists of bullet points
- keep text concise
- no extra keys
- no markdown
- no explanation outside JSON
- role must be a market-standard job title (no vague terms like "expert")
- CRITICAL DEADLINE EXCLUSION: Completely omit any deadlines, completion dates, or turnaround time windows mentioned in the JD (e.g. "Your turnaround time will be 3 hours of conversation that needs to be filled before 12/28"). The output must not hint anything regarding deadlines while keeping all other details covered.

RESPONSIBILITIES RULES:
- Extract ALL meaningful actions from the JD (even if implicit)
- Expand short responsibilities into clear, complete bullet points
- Combine scattered lines into structured responsibilities
- Target 4-6 bullets when sufficient information exists
- Each bullet must:
  - start with an action verb
  - be specific and complete
  - reflect real work being done

Example Responsibilities:
Input: "create deliverables", "review peer work"
Output:
- Create structured deliverables based on domain-specific tasks and requirements
- Review peer-developed work to ensure quality and alignment with project standards
- Identify issues in outputs and suggest improvements
- Maintain consistency and accuracy across all deliverables

REQUIREMENTS RULES:
- Extract qualifications fully, not partially
- Expand incomplete lines into proper sentences
- Convert "X years" into: "Candidates should have strong relevant experience in the domain"
- Target 4-6 bullets when possible
- Each bullet must:
  - be complete
  - grammatically correct
  - recruiter-friendly

IMPORTANT:
- Do NOT leave bullets short or incomplete
- Do NOT output fragments like: "4+ years experience"
- Always expand into full professional sentences

ROLE OVERVIEW RULES:
- must be 40-70 words
- explain what the candidate will actually do
- include impact of the work
- avoid generic phrasing
- must feel like a real job pitch

Bad: "Assess AI responses"
Good: "Evaluate and improve AI-generated outputs by identifying inaccuracies, refining reasoning, \
and ensuring domain-specific correctness in high-stakes applications such as finance, healthcare, \
and legal systems."

WHO_THIS_IS_FOR RULES:
- must be 40-70 words
- clearly define target candidate
- include: domain (finance, legal, etc.), experience level, type of work they've done
- avoid vague phrases like "strong skills"

Bad: "Candidates with expertise in finance"
Good: "Professionals with hands-on experience in finance, accounting, law, or healthcare who have \
worked in analytical, advisory, or compliance roles and are comfortable evaluating complex outputs \
for accuracy and reasoning."

CORE PRINCIPLE FOR TITLES

A job title must optimize for:

Candidate relevance (attract the right people)
Searchability (match how candidates describe themselves)
Clarity (immediate understanding in <2 seconds)
Market alignment (use real industry-standard phrasing)

Never prioritize creativity over accuracy.

TITLE DESIGN RULES
1. ALWAYS MATCH THE ACTUAL WORK, NOT PERCEIVED SENIORITY
Example:
If the role is execution-heavy → use Developer / Engineer / Specialist
If the role is analytical → use Analyst / Scientist
If the role is creative-production → use Producer / Designer
If the role is academic → use Professor / Researcher
If the role is operational → use Specialist, not Engineer

Do NOT inflate titles (avoid "Expert" unless truly required).

2. TOOL OR DOMAIN MUST BE INCLUDED IF NICHE

If the JD revolves around a specific tool, framework, or system:

Include it explicitly in the title
Format:
Role - Tool
Role (Tool)
Tool-based Role

Examples:

C# Game Developer (MonoGame)
Power Electronics Engineer - SPICE
CAD Designer - Autodesk Inventor

Do NOT dilute specificity (avoid "/ DAW", "/ AI Model", "/ Any Tool").

3. USE MARKET LANGUAGE, NOT INTERNAL LANGUAGE

Avoid unnatural constructions such as:

"Autodesk Inventor Designer"
"AI Model Specialist"
"Operating System Engineer (Usage)"

Instead:

Mechanical Designer - Autodesk Inventor
Applied Data Scientist - AI
Windows OS Specialist

4. PRIORITIZE SEARCH KEYWORDS USED BY CANDIDATES

Use titles candidates actually use on LinkedIn:

GOOD:

Game Developer
Gameplay Programmer
Audio Engineer
Mechanical Design Engineer
Econometrician

BAD:

Graphic Specialist (for programmers)
Application Developer (for game roles)
Economics Specialist (too broad)

5. AVOID CROSS-DOMAIN CONFUSION

Never mix unrelated audiences:

Do NOT target Graphic Designers for programming roles
Do NOT use Audio Engineer for music composition roles
Do NOT use Data Analyst for ML-heavy roles
Do NOT use Game Designer for engineering roles

Each title must map to a clearly defined talent pool.

6. TITLE LENGTH OPTIMIZATION

Ideal title length:

3-6 words preferred
Max: 8 words

If too long → reduce
If too vague → add tool/domain

7. USE STRUCTURED FORMATS

Prefer these formats:

Role - Tool
Role (Tool)
Domain Role
Role - Domain

Examples:

AI/ML Engineer
Generative AI Engineer
Applied Data Scientist - AI
MonoGame Game Developer
Ardour Audio Engineer

8. SIGNAL CORRECT SPECIALIZATION LEVEL

Use modifiers carefully:

Use "Senior" only if JD requires experience depth
Use "Specialist" for tool/domain expertise
Use "Engineer" only for technical/system-building roles
Use "Producer" for creative workflow ownership
Use "Consultant" for advisory roles

9. ALIGN TITLE WITH RESPONSIBILITIES SIGNALS

Map responsibilities → title:
example:
Coding + architecture → Engineer / Developer
Modeling + ML → Data Scientist / ML Engineer
Transcription + language → Linguist / Language Specialist
CAD + manufacturing → Mechanical Designer / CAD Engineer
Audio production → Audio Engineer / Producer
Investigation → Criminal Investigator

OUTPUT FORMAT

Given a JD, produce 5 job titles
BEST TITLE (single top recommendation)
4-5 ALTERNATIVE TITLES (ranked)

Keep output concise and decisive.

ABSOLUTE RULES
No inflated titles
No mixed-domain targeting
No internal jargon
No unnecessary complexity

If a title attracts the wrong audience, it is incorrect - even if technically accurate.

ADDITIONAL INFORMATION:
Do not use the keyword "AI" in the title unless absolutely necessary.

SUBJECT RULES:
Format: {role} | $X/hr Remote | {CLIENT_NAME} x AI Labs
Remove pay if missing
Do not mention Remote if role is not remote

SKILLS RULES:
- Return EXACTLY 4-5 skills.
- Skills must be BROAD, SEARCHABLE, industry-standard terms that recruiters type into LinkedIn.
- Each skill must be 1-3 words MAX.
- NO soft skills (e.g., communication, teamwork).
- NO niche or descriptive phrases (e.g., "STEM problem-solving", "AI-driven analysis").
- NO verbs or verb phrases.
- Do NOT repeat the role title.
Good examples: Python, SQL, Data Analysis, Machine Learning, Financial Modeling, Project Management, UX Design
Bad examples: Bilingual Communication, AI-Driven Analysis, STEM Problem-Solving

JOB FUNCTIONS RULES:
Select EXACTLY 3 from this EXACT list - copy the values verbatim, no modifications:
Accounting & Auditing, Administrative, Advertising, Analytics, Customer Service, Design, \
Education, Engineering, Finance, General Business, Health care provider, Human Resources, IT, \
Legal, Manufacturing, Marketing, Product Management, Project Management, Public Relations, \
Research, Sales, Strategy/Planning, Training, Consulting, Writing/Editing, Art/Creative
DO NOT invent new values. DO NOT rephrase. Choose based on role responsibilities, not just the job title.

INDUSTRIES RULES:
Select EXACTLY 3 from this EXACT list - copy the values verbatim, no modifications:
Accommodation and Food Services, Administrative and Support Services, Construction, \
Consumer Services, Education, Entertainment Providers, Farming, Ranching, Forestry, \
Financial Services, Government Administration, Holding Companies, Hospitals and Health Care, \
Manufacturing, Oil, Gas, and Mining, Professional Services, \
Real Estate and Equipment Rental Services, Retail, Technology, Information and Media, \
Transportation, Logistics, Supply Chain and Storage, Utilities, Wholesale, Research Services, \
Investment Management, Translation and Localization, Strategic Management Services, \
Information Services, Higher Education, Primary and Secondary Education, Medical Practices
DO NOT invent new values. DO NOT rephrase. Choose based on the industry context of the role.

JUSTIFICATIONS RULES:
- Return a flat JSON dictionary under the "justifications" key.
- The dictionary must map each parsed item in suggested_titles, job_functions, industries, and skills to a specific, high-quality, and helpful one-line justification (max 20 words).
- DO NOT use generic phrases like "matches the title", "relevant industry", or "required for the role". Instead, give a deep, domain-specific explanation referencing specific tasks or requirements from the job description.
  Good Examples:
  - {"Audio Visual Specialist": "Aligns with the peer-review of acoustics deliverables mentioned in section 2."}
  - {"Python": "Required to build the scalable training pipelines and ML tool integration in core duties."}
  - {"Research Services": "Matches Turing's focus on benchmarking and scaling model evaluation environments."}
  - {"Engineering": "Applies directly to the backend API orchestration and multi-agent system design."}

Job Description:
"""
