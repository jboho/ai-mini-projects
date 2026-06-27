import json
import anthropic

CATEGORIES = ("filler_phrase", "redundant_context", "over_specified", "ignored_instruction")

_RUBRIC = """You analyze Claude Code conversation pairs to find unnecessary text in user prompts.

For the PROMPT below, identify specific text that could be removed or shortened without changing the quality or meaning of the RESPONSE.

Categories:
- filler_phrase: Polite openers or intent signals with no informational content (e.g., "Please", "I need you to", "Make sure to", "As an expert")
- redundant_context: Information the model already knows or that duplicates earlier context
- over_specified: Instructions the model applies by default (e.g., "write clean code", "don't break existing tests", "be thorough")
- ignored_instruction: A directive in the prompt that does not appear to have shaped the response

Return ONLY a JSON object with key "findings" (array). Each element:
{
  "category": "<one of the four above>",
  "excerpt": "<exact quoted text from the prompt, max 60 chars>",
  "suggestion": "<one sentence: how to remove or rewrite>",
  "confidence": "<high|medium|low>"
}

If no issues found, return {"findings": []}."""


def _audit_pair(client: anthropic.Anthropic, pair: dict, model: str) -> list[dict]:
    prompt_text = pair["prompt"]
    user_content = f"{_RUBRIC}\n\n---\n\nPROMPT:\n{prompt_text}\n\nRESPONSE:\n{pair['response'][:600]}"
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": user_content}],
        )
        result = json.loads(msg.content[0].text)
        return [
            {**f, "source_prompt": prompt_text}
            for f in result.get("findings", [])
            if f.get("category") in CATEGORIES
        ]
    except (json.JSONDecodeError, KeyError, IndexError, anthropic.APIError):
        return []


def audit_pairs(pairs: list[dict], model: str = "claude-haiku-4-5-20251001") -> list[dict]:
    client = anthropic.Anthropic()
    all_findings = []
    for pair in pairs:
        all_findings.extend(_audit_pair(client, pair, model))
    return all_findings
