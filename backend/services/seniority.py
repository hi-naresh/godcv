import re

def detect_seniority(job_description: str) -> str | None:
    """Detect seniority level from job description text.
    Returns one of: 'graduate', 'junior', 'mid-level', 'senior', 'lead', 'principal', or None.
    """
    text = job_description.lower()

    # Explicit title keywords (highest priority)
    if re.search(r"\b(principal|staff)\b", text):
        return "principal"
    if re.search(r"\b(lead|head|manager)\b.*\b(engineer|developer|team)\b", text) or \
       re.search(r"\b(engineer|developer)\b.*\b(lead|head)\b", text) or \
       re.search(r"\btech(?:nical)?\s+lead\b", text) or \
       re.search(r"\blead\s+(?:software|backend|frontend|full\s*stack)\b", text):
        return "lead"
    if re.search(r"\bsenior\b", text):
        return "senior"
    if re.search(r"\bjunior\b", text):
        return "junior"
    if re.search(r"\b(?:graduate|grad|entry[\s-]level|new\s+grad|intern(?:ship)?|trainee)\b", text):
        return "graduate"

    # Years of experience
    years_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text)
    if years_match:
        years = int(years_match.group(1))
        if years <= 1: return "graduate"
        elif years <= 2: return "junior"
        elif years <= 5: return "mid-level"
        else: return "senior"

    # Range patterns "3-5 years"
    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)", text)
    if range_match:
        upper = int(range_match.group(2))
        if upper <= 2: return "junior"
        elif upper <= 5: return "mid-level"
        else: return "senior"

    return None
