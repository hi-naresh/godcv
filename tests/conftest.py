import pytest
from backend.services.parser import parse_resume

SAMPLE_RESUME_MD = """---
name: Test User
title: Software Engineer | London, UK
email: test@example.com
phone: +441234567890
portfolio: example.com
github: github.com/testuser
linkedin: linkedin.com/in/testuser
font_size: 11
line_spacing: 1.4

---
# Summary
Software engineer with 3 years of experience in Python and cloud infrastructure.

---

# Education

**M.Sc. in Computer Science - University of London** *Jan 2023 – Jan 2024*
***Coursework**:* Distributed Systems; Machine Learning; Data Engineering.

---
# Skills

**Backend:** Python, FastAPI, Django, PostgreSQL, Redis.

**Cloud/Infra:** AWS, Docker, Kubernetes, Terraform, CI/CD.

**Programming:** Python, TypeScript, Go.

---
# Experience

**Senior Engineer — Acme Corp (London, ~50 people)** *Jan 2023 – Present*
- Built scalable data pipelines processing 1M+ records daily.
- Designed microservices architecture reducing latency by 30%.

**Junior Developer — StartupXYZ (Remote, ~10 people)** *Jun 2021 – Dec 2022*
- Developed REST APIs serving 500+ daily active users.
- Implemented CI/CD pipelines with GitHub Actions and Docker.

---
# Projects

**[DataFlow Engine](https://github.com/test/dataflow)** | Stack - Python, Apache Kafka, PostgreSQL, Docker
- Built real-time data streaming pipeline processing 10K events/second.

**[CloudDash](https://clouddash.dev)** | Stack - TypeScript, React, AWS Lambda, DynamoDB
- Dashboard for monitoring cloud infrastructure costs and usage.

---
# Volunteering and Interests
**Open Source Contributor** - Regular contributor to Python data tools.

**Interests**: Hiking, Chess, Coffee.
"""

SAMPLE_JD = """Senior Backend Engineer - TechCorp

We're looking for a Senior Backend Engineer to join our platform team.

Requirements:
- 5+ years of experience with Python and distributed systems
- Experience with Kubernetes, Docker, and cloud infrastructure (AWS preferred)
- Strong background in data pipelines and real-time processing
- Experience leading technical projects and mentoring junior engineers
- Familiarity with FastAPI or Django

Nice to have:
- Experience with Apache Kafka or similar streaming platforms
- Knowledge of infrastructure-as-code (Terraform)
"""


@pytest.fixture
def sample_resume():
    return SAMPLE_RESUME_MD


@pytest.fixture
def sample_jd():
    return SAMPLE_JD


@pytest.fixture
def parsed_resume():
    return parse_resume(SAMPLE_RESUME_MD)
