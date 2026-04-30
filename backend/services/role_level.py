import re


def detect_role_level(job_description: str) -> str | None:
    """Detect role level from job description text.
    Returns one of: 'graduate', 'non-graduate', or None.

    'graduate' covers entry-level and junior roles (1-2 yrs typical).
    'non-graduate' covers everything mid-level and above.
    """
    text = job_description.lower()

    # Senior signals win over graduate signals when both appear
    if re.search(r"\b(principal|staff)\b", text):
        return "non-graduate"
    if re.search(r"\b(lead|head|manager)\b.*\b(engineer|developer|team)\b", text) or \
       re.search(r"\b(engineer|developer)\b.*\b(lead|head)\b", text) or \
       re.search(r"\btech(?:nical)?\s+lead\b", text) or \
       re.search(r"\blead\s+(?:software|backend|frontend|full\s*stack)\b", text):
        return "non-graduate"
    if re.search(r"\bsenior\b", text):
        return "non-graduate"
    if re.search(r"\bjunior\b", text):
        return "graduate"
    if re.search(r"\b(?:graduate|grad|entry[\s-]level|new\s+grad|intern(?:ship)?|trainee)\b", text):
        return "graduate"

    # Years of experience
    years_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text)
    if years_match:
        years = int(years_match.group(1))
        return "graduate" if years <= 2 else "non-graduate"

    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)", text)
    if range_match:
        upper = int(range_match.group(2))
        return "graduate" if upper <= 2 else "non-graduate"

    return None
