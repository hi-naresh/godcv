from backend.services.gemini import GeminiClient


class ATSScorerAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def score(self, resume_markdown: str, job_description: str) -> dict:
        """Run a rigorous ATS evaluation on a resume against a job description."""
        prompt = f"""You are a ruthless ATS (Applicant Tracking System) evaluator. Score this resume against the job description exactly how a real ATS would — no encouragement, no rounding up, brutally honest.

EVALUATION CATEGORIES (score each 0-100):

1. contact_info: Are name, email, phone, LinkedIn all present and clearly parseable? Missing any = penalty.

2. parsability: Is the format clean single-column? No tables, images, columns, fancy formatting that breaks ATS parsers? Standard markdown structure?

3. keyword_match: Count the EXACT important keywords/phrases from the JD that appear in the resume. ATS systems do NOT understand synonyms — "ML" and "Machine Learning" are different. Count exact matches only. Score = (matched keywords / total important JD keywords) * 100.

4. section_headers: Are section names standard (Experience, Education, Skills, Projects, Summary)? Creative names like "What I've Built" or "My Journey" get penalized — ATS can't parse them.

5. date_format: Are dates consistent and parseable? "Jan 2023 – Present" is good. "2023" alone, inconsistent formats, or missing dates get penalized.

6. title_match: Does any job title in the resume align with the JD title? Exact match = 100, close match = 70, no match = 30.

7. hard_skills: Are the JD's required hard skills EXPLICITLY listed in the Skills section? Skills buried only in bullet points get partial credit. Skills completely missing = 0 for each.

8. quantified_results: What percentage of experience/project bullets contain specific numbers, metrics, or percentages? "Improved performance by 30%" beats "Improved performance significantly."

9. experience_depth: Does the years of experience match what the JD asks? If JD says "5+ years" and resume shows 2 years, that's a major penalty.

RESUME:
{resume_markdown}

JOB DESCRIPTION:
{job_description}

Respond with JSON:
{{
  "ats_score": "<weighted average of all categories, integer 0-100>",
  "breakdown": {{
    "contact_info": {{"score": "<0-100>", "detail": "<one sentence explanation>"}},
    "parsability": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "keyword_match": {{"score": "<0-100>", "detail": "<X/Y JD keywords found>"}},
    "section_headers": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "date_format": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "title_match": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "hard_skills": {{"score": "<0-100>", "detail": "<X/Y required skills in Skills section>"}},
    "quantified_results": {{"score": "<0-100>", "detail": "<X/Y bullets have metrics>"}},
    "experience_depth": {{"score": "<0-100>", "detail": "<one sentence>"}}
  }},
  "brutal_verdict": "<2-3 sentences. Would this resume pass ATS screening? Where would it rank? What are the deal-breakers?>"
}}"""

        return await self.gemini.generate_json(prompt)
