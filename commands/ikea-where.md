---
description: Find where in an IKEA Israel branch an article is picked, and how many are there
argument-hint: <article number> <branch name or code>
allowed-tools: Read, Bash(python3 *), Skill
---

Locate in store: **$ARGUMENTS**

Use the `ikea-il-warehouse-location` skill.

`python3 scripts/ikea_il.py locate <article> <store>`

- `SELF_SERVE` / `AISLE_AND_BIN` → report as **aisle N, bin X**.
- `WAREHOUSE` / `CONTACT_STAFF` → full-serve. The `id` is a free-form
  store-local string in no consistent format. Say "ask staff at the collection
  point"; do not present it as an aisle.
- No `sales_locations` at all → a market-hall item taken off a showroom shelf.
  Correct, not missing data.

Quote the quantity alongside. A pick location persists whether or not anything
is on the rack.
