# notes

{What to save. Content to write, a topic to summarize from the conversation, or explicit filename and content.}

---

## Mission Briefing: Notes Protocol

Save the user's requested content to `.cursor/notes/`. The folder is gitignored.

1. **Extract:** Determine what to save from the user's input. If they provide explicit content, use it. If they reference recent conversation (e.g. "summarize our discussion"), create a concise summary.
2. **Filename:** Use a descriptive slug from the topic, or `YYYY-MM-DD-description.md`. Default extension: `.md`. If the user specifies a filename (e.g. "as rag-approach.md"), use it.
3. **Write:** Create the file at `.cursor/notes/<filename>`.
4. **Confirm:** Report the path.

---

**Begin notes protocol now.**
