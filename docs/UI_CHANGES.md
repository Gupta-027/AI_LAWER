# Interface revision for the hosted demo

The welcome screen now puts the request field before the synthetic examples.
After the first message, a compact heading leads into the conversation and case
workspace. On desktop these sit beside each other; narrow screens stack them.
The workspace switches between **My case**, **Next steps** and **My draft**.
Preparing a draft opens the draft tab, while correction warnings and replacement
previews remain available.

Case editing uses readable field labels instead of internal dictionary keys.
Entering a previously unknown fact clears its unresolved status. The mode badge
distinguishes rules demo, unverified provider configuration, confirmed extraction
connection and model fallback. Language, privacy, source and download controls
remain available.

Design references and their bounded roles are recorded in
[UI_REFERENCES.md](UI_REFERENCES.md). Structure was informed by inspected
Spellbook/Dropbox Dash chat screens, Plane/Notion request-entry screens and a
Fabric supporting-panel example; the product keeps its own colours and content.

Before: [desktop](ui-before-desktop.png), [mobile](ui-before-mobile.png).

After: [welcome](preview-desktop.png), [active workspace](preview-case.png),
[draft](preview-draft.png), [mobile welcome](preview-mobile.png),
[mobile case](preview-mobile-case.png).

Verification: 29 unit methods passed, including session isolation, independent
languages, manual-edit protection, friendly fact editing, HTML escaping and
Render launch settings. The separate deterministic evaluation remains 68/68
assertions across 14 conversations. Local browser checks confirmed the selected
draft tab and no horizontal overflow at 390px in empty and active states. No
comprehension improvement, full accessibility audit or successful Render cloud
deployment is claimed from these checks.
