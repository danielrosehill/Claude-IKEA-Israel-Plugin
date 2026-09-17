---
description: Check IKEA Israel stock for an article across all five branches
argument-hint: <article number, or a product to search for>
allowed-tools: Read, Bash(python3 *), Skill
---

Branch stock for: **$ARGUMENTS**

Use the `ikea-il-branch-stock` skill.

1. If the argument is not an article number, resolve it first with
   `ikea_il.py search` and say which article you settled on.
2. `python3 scripts/ikea_il.py stock <article...>` — batch, up to 50 per call.
3. Drop every row where `in_store_directory` is false. `523` reports the largest
   quantity on the page and is not a branch a customer can enter.

Report the unit count, the branch name and the `updated` timestamp together.
Never a bare "in stock" — the count and its age are the answer.

If everything is zero, read `restocks` before saying unavailable.

State plainly that this is IKEA's stock figure at a stated time, not a live
shelf count.
