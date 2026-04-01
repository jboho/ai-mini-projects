# adapt-domain

Adapt a mini project to a new domain. The AI will prompt you for each missing piece before proceeding.

---

## Mission Briefing: Domain Adaptation Protocol

You will help the user adapt a mini project to a different domain while preserving all technical requirements and success criteria.

**Before doing anything else**, prompt the user for each of the following. Collect all values before proceeding:

1. **Original topic** — e.g., "DIY home repair customer support"
2. **Chosen domain** — e.g., "e-commerce / online shopping support"
3. **Original success criteria** — paste the success criteria from the mini project
4. **Original project description** — paste or summarize the project description

Ask for these one at a time or in a single message. If the user provides some values in the command placeholder above, use those and only ask for the rest.

---

## Once All Information Is Collected

Assemble and execute this request:

```
I have a mini project about [original topic].
I want to adapt it to [chosen domain].

Here are the requirements I MUST keep (do not change any of these):
- Same Python libraries and technical approach (do not change the tech stack)
- Same techniques and methods used in the original project
- Same success criteria as the original (listed below)
- Same overall structure and learning objectives

Original success criteria:
[paste the success criteria from the mini project here]

Original project description:
[paste or summarize the project description here]

Please convert this project to my chosen domain. Keep every technical requirement
and success criterion exactly in place. Only change the domain, example data,
and scenario descriptions.

If it is not possible to meaningfully adapt this project to my chosen domain
while keeping all technical and educational requirements intact, please tell me why and suggest
a different domain that would work well.
```

---

**Begin by prompting the user for the four required inputs. Do not proceed until all are collected.**
