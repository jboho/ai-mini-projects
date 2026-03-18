# add-rule

{The decision, pattern, or convention to codify. Can be a brief description - the AI will help articulate it fully. If omitted, the AI will infer from recent conversation context.}

---

## **Mission Briefing: Rule Codification Protocol**

You are capturing a decision, pattern, or convention from this session and codifying it into the appropriate rule file. This ensures consistency across future development and AI interactions.

---

## **Phase 0: Rule Extraction**

- **Directive:** Identify and articulate the rule to be created.
- **Actions:**
  1. If the user provided a description, use it as the basis.
  2. If no description provided, analyze the recent conversation context to identify:
     - Decisions made about code style, patterns, or conventions
     - Corrections or preferences expressed by the user
     - Patterns that emerged as "the way we do things here"
  3. Articulate the rule clearly and concisely.
- **Output:** Present the extracted rule (Pattern/Decision, Context, Example with ❌/✅).
- **Constraint:** Do NOT proceed until rule is articulated.

---

## **Phase 1: Scope Recommendation**

- **Directive:** Recommend GLOBAL vs PROJECT-SPECIFIC with rationale. Wait for user confirmation or override.

---

## **Phase 2: File Pattern Determination (Project-Specific Only)**

- **Directive:** If project-specific, determine file patterns (globs) or alwaysApply. Wait for user confirmation.

---

## **Phase 3: Rule Drafting**

- **Directive:** Draft the complete rule file content for user approval. **Do NOT save until user explicitly approves.**

---

## **Phase 4: Rule Creation**

- **Directive:** Upon approval, create or update the rule file in `.cursor/rules/` (project) or `~/.cursor/rules/` (global). Report path and next steps.

---

**Begin rule extraction now.**
