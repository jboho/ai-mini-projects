"""Five writing-style system prompts for resume generation.

Each template shapes the LLM's voice and formatting preference.
The user prompt (injected at call time) always contains the job description
and the target fit level, keeping style and content concerns separate.
"""

from __future__ import annotations

from .schemas.pair import WritingStyle

SYSTEM_PROMPTS: dict[WritingStyle, str] = {
    WritingStyle.FORMAL: (
        "You are a professional resume writer specializing in corporate and "
        "enterprise environments. Write in a formal, structured tone using "
        "complete sentences, conservative language, and industry-standard "
        "terminology. Avoid contractions and colloquialisms. "
        "Quantify achievements where possible. Emphasize reliability, "
        "process adherence, and organizational impact."
    ),
    WritingStyle.CASUAL: (
        "You are a resume writer for startup and tech culture environments. "
        "Write in a relaxed, conversational tone that conveys personality. "
        "Use first-person-adjacent phrasing ('Built...', 'Shipped...', "
        "'Helped the team...'), short punchy bullet points, and a voice that "
        "feels authentic rather than corporate. Highlight culture fit and "
        "collaborative spirit."
    ),
    WritingStyle.TECHNICAL: (
        "You are a resume writer for senior engineering and technical roles. "
        "Be specific: name exact versions, frameworks, architectures, and "
        "infrastructure. Include metrics where real engineers would (latency, "
        "throughput, uptime, scale). Use precise technical vocabulary. "
        "Prefer depth over breadth — a few well-described technical "
        "achievements beat a long list of buzzwords."
    ),
    WritingStyle.ACHIEVEMENT: (
        "You are a resume writer focused entirely on measurable impact. "
        "Every bullet point must follow an action-result pattern: "
        "'[Strong verb] [specific action], resulting in [quantified outcome]'. "
        "Examples: 'Reduced API response time by 40% by introducing Redis "
        "caching', 'Grew monthly active users from 10K to 85K in 8 months'. "
        "Never write a bullet without a number or percentage."
    ),
    WritingStyle.CAREER_CHANGER: (
        "You are a resume writer specializing in career transitions. "
        "Frame transferable skills as direct assets for the new role. "
        "Acknowledge the transition narrative explicitly in the summary "
        "('Transitioning from X to Y, bringing Z years of...'). "
        "Draw parallels between past experience and new domain requirements. "
        "Emphasize learning velocity, adaptability, and cross-domain patterns."
    ),
}

FIT_LEVEL_INSTRUCTIONS: dict[str, str] = {
    "Excellent": (
        "The candidate is a near-perfect match. Include ALL required skills from "
        "the job description, match or exceed the experience requirement, and align "
        "the seniority level exactly. The resume should read like it was written "
        "for this specific job."
    ),
    "Good": (
        "The candidate is a strong but not perfect match. Include most required "
        "skills (at least 80%) and come close to the experience requirement (within "
        "1 year). Leave 1-2 preferred skills missing or slightly misaligned."
    ),
    "Partial": (
        "The candidate has partial overlap. Include about half the required skills "
        "and either underqualify (2+ years short) or be one seniority level off. "
        "Some experience is relevant but the overall fit is questionable."
    ),
    "Poor": (
        "The candidate is a weak match across all four dimensions — skills, "
        "experience, language quality, and skill proficiency:\n"
        "SKILLS: Include fewer than 30% of the required skills. The rest of the "
        "skills listed should be from a different domain entirely.\n"
        "EXPERIENCE: The candidate is early in their career with only 1-2 years "
        "of total experience. Their most recent role was at junior or associate "
        "level (e.g. 'Junior Developer', 'Associate Analyst'). The role requires "
        "significantly more seniority.\n"
        "LANGUAGE: The candidate over-relies on vague buzzwords to compensate for "
        "limited experience. Scatter at least 4-5 of these phrases naturally across "
        "the summary and achievement bullets: 'results-driven', 'leveraged', "
        "'synergies', 'thought leader', 'cutting-edge', 'holistic approach', "
        "'proven track record'. They should feel like someone padding a thin resume.\n"
        "PROFICIENCY INFLATION: Despite only 1-2 years of experience, the candidate "
        "claims Expert proficiency on 5-7 skills. Set years_used to 3-4 years on "
        "several of those Expert skills (exceeding their actual career length). This "
        "creates an implausible skill portfolio that a recruiter would flag immediately."
    ),
    "Mismatch": (
        "The candidate is clearly unsuitable across all four dimensions — skills, "
        "experience, language quality, and skill proficiency:\n"
        "SKILLS: Include almost none of the required skills. The candidate's "
        "background is from a completely unrelated field.\n"
        "EXPERIENCE: The candidate has 1 year or less of total professional "
        "experience, has recently graduated, or has just changed careers. Their "
        "most recent title is entry-level (e.g. 'Intern', 'Junior', 'Graduate "
        "Trainee'). The role requires a senior or lead professional.\n"
        "LANGUAGE: The candidate heavily pads the resume with buzzwords and vague "
        "claims to disguise the mismatch. Include at least 5-6 of these phrases "
        "spread across the summary and achievement bullets: 'results-driven', "
        "'leveraged synergies', 'thought leader', 'paradigm shift', 'cutting-edge', "
        "'holistic approach', 'proven track record', 'self-starter', 'go-getter', "
        "'dynamic professional'. The resume should read like someone who learned "
        "resume writing from a template without real substance behind it.\n"
        "PROFICIENCY INFLATION: Despite 1 year or less of experience, the candidate "
        "claims Expert proficiency on 6-8 skills and sets years_used to 3-5 years "
        "on those skills. The total years_used across all skills should far exceed "
        "the candidate's actual career length — this is a hallucination signal."
    ),
}


def build_resume_user_prompt(job_description_json: str, fit_level: str) -> str:
    fit_instruction = FIT_LEVEL_INSTRUCTIONS[fit_level]
    return (
        f"Generate a resume for the following job description.\n\n"
        f"JOB DESCRIPTION (JSON):\n{job_description_json}\n\n"
        f"FIT LEVEL TARGET: {fit_level}\n"
        f"FIT INSTRUCTIONS: {fit_instruction}\n\n"
        "Return a complete resume as a JSON object matching the Resume schema. "
        "The metadata fields (trace_id, prompt_template, fit_level, writing_style) "
        "will be filled in by the caller — set them to placeholder strings. "
        "Use realistic names, companies, dates (past 10 years), and skills."
    )
