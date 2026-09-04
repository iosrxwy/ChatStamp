# ChatStamp

Portable Agent Skill. Humans install from `README.md`.

`/tu` `/tc` use the command file on screen. `/au` `/ac` read `SKILL.md` at the install path (`~/.cursor/skills/chat-stamp/SKILL.md`).

- Prefer a clear existing title and only wrap the format. If the title is unclear or the wrong language, use the user's messages plus the assistant wrap-up with code stripped.
- Date source is `created` or `updated` in `~/.config/chat-stamp/config.json`.
- `locale` is `zh` or `en`. Title language follows the user, never a single chat's body.
- Chinese user → every title stays Chinese, even when the transcript is English.
- Scripts only write title / archive-empty. Never pin, sort, or move projects.
