import re


def clean_job_text(text):
    if not text:
        return ""

    # Convert multiple spaces/newlines into cleaner text
    text = re.sub(r'\s+', ' ', text)

    # Remove common webpage junk
    junk_patterns = [
        r'\bSign in\b',
        r'\bLog in\b',
        r'\bLogin\b',
        r'\bSign up\b',
        r'\bHome\b',
        r'\bSearch jobs\b',
        r'\bShare\b',
        r'\bFollow\b',
        r'\bApply now\b',
        r'\bRecommended jobs\b',
        r'\bSimilar jobs\b',
        r'\bRelated jobs\b',
        r'\bPrivacy Policy\b',
        r'\bTerms of Use\b',
        r'\bCookie Policy\b',
    ]

    for pattern in junk_patterns:
        text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)

    # Remove duplicate spaces again
    text = re.sub(r'\s+', ' ', text).strip()

    # Limit text length
    text = text[:12000]

    return text