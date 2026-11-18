from cleaner import clean_job_text

raw_text = """
Sign in
Home
Search jobs

Software Developer

We are looking for a software developer.
Experience with Java and Python required.

Recommended jobs
Software Engineer
Data Analyst

Privacy Policy
"""

cleaned = clean_job_text(raw_text)

print(cleaned)