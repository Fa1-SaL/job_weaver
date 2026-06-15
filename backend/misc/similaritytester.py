from openai import OpenAI

client = OpenAI(api_key="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")

text = """Generalist Expert
Hourly contract
Remote
Recent hire 1Recent hire 2Recent hire 3
2160 hired this month

$23-$30
per hour
Mercor logo
Posted by Mercor
mercor.com





Role Overview
Mercor is collaborating with a leading AI lab to contract detail-oriented generalists for a data annotation project. Contractors will support the development of AI systems by categorizing and labeling diverse datasets using predefined taxonomies. The project offers an opportunity to directly contribute to the accuracy, reliability, and performance of next-generation AI models.

Key Responsibilities
Synthesize information from large volumes of data

Annotate and categorize text, images, and other data according to detailed guidelines

Apply predefined rubrics and taxonomies to produce structured, high-quality outputs

Flag inconsistencies, ambiguities, or errors in datasets

Contribute to the improvement of AI systems through consistent annotation work

Ideal Qualifications
Ability to synthesize complex or high-volume information into structured formats

Strong critical reasoning, reading comprehension, and written communication skills

Prior experience applying rubrics, taxonomies, or standardized guidelines (preferred but not required)

A college degree and experience with data annotation projects

More About the Opportunity
Expected commitment: ~20 hours/week
Application Process
Submit your resume to begin

Complete a Training Assessment

We consider all qualified applicants without regard to legally protected characteristics and provide reasonable accommodations upon request.
"""

response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text,
    dimensions=1536
)

embedding = response.data[0].embedding

print(embedding)