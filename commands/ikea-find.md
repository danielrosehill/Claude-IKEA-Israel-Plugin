---
description: Search IKEA Israel and return article numbers with ILS prices
argument-hint: <what you are looking for, Hebrew or English>
allowed-tools: Read, Bash(python3 *), Skill
---

Find on IKEA Israel: **$ARGUMENTS**

Use the `ikea-il-search` skill.

`python3 scripts/ikea_il.py search "$ARGUMENTS"`

Return a shortlist with article number, joined `name` + `typeName` + measure,
and ILS price. The article number is the part that matters — it is what every
subsequent lookup needs.

Do not read `online_sellable: false` as out of stock. It is common on IL and
means collect-from-branch, not unavailable. If the user's question was really
about availability, follow up with `ikea-il-branch-stock`.
