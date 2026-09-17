---
name: ikea-il-branch-stock
description: Answer whether a specific article is in stock at a specific IKEA Israel branch, with real unit counts and restock dates. Use for any "is it available in X" or "which branch has it" question.
allowed-tools: Read, Bash(python3 *)
---

# Is this article in stock at this branch

IKEA Israel returns **real unit counts per store**, not a band. This is the
headline capability of the plugin.

```bash
python3 scripts/ikea_il.py locate 602.056.64 206          # one article, one store
python3 scripts/ikea_il.py locate 00263850 נתניה          # store by Hebrew name
python3 scripts/ikea_il.py stock 602.056.64 00263850      # articles across all stores
python3 scripts/ikea_il.py stock 602.056.64 --in-stock-only
```

Up to **50 article numbers per call**. Batch them. One call per article is nine
times the rows for the same answer.

## The five branches

| Code | Name | City |
|---|---|---|
| 206 | נתניה | נתניה |
| 217 | ראשון לציון | ראשון לציון |
| 318 | קריית אתא | קריית אתא |
| 531 | באר שבע | באר שבע |
| 613 | אשתאול | אזה"ת הר טוב |

613 is the one that breaks name matching: it is filed as אשתאול but its address
city reads אזה"ת הר טוב. Match against the code, `display_name`,
`display_name_long` and the address city before giving up.

## The trap that would send someone to the wrong building

An availability response carries **nine** class units, not five. Three of them
are not branches:

- `RU/IL` — the country row. Home delivery only, never a shelf quantity.
- `STO/523` — reported **1337 units** cash-and-carry and is absent from the
  store directory. Not a shoppable branch.
- `STO/737`, `STO/738` — present, no quantity, also not in the directory.

`classUnitType == "STO"` does not mean "somewhere a customer can walk in".
`ikea_il.py stock` marks every row with `in_store_directory`. **If it is false,
the row is not a branch — never report it as stock a person can go and collect.**
523 is the dangerous one precisely because its number is the largest on the page.

## What the numbers mean

- `quantity` — actual units. `194`, `41`, `1337`.
- `message_type` — `HIGH_IN_STOCK`, `MEDIUM_IN_STOCK`, `OUT_OF_STOCK`.
  Observed set; treat anything else as unknown rather than guessing its rank.
- `updated` — **per store, per article**, and often a day old. One response
  carried 2026-09-16T16:21 for Beer Sheva beside 2026-09-17T09:39 for Rishon
  LeZion.
- `restocks` — `earliestDate`, `latestDate`, `quantity`, `reliability`. Present
  on out-of-stock rows when a delivery is scheduled. This is what turns "no"
  into something useful.
- `pickup` — `CUSTOMER_PICKUP` (you take it off the rack) or `COWORKER_PICKUP`
  (staff fetch it from the warehouse).

## Reporting

Quote the count, the branch **name** and the timestamp together:

> 194 units at נתניה (store 206), as of 2026-09-17 08:41.

Not "in stock". The count and its age are the whole value; a bare "yes" throws
away both and implies a live shelf reading that this data is not.

If the answer is zero everywhere, check `restocks` before saying so — "none in
any branch, 12 units due at ראשון לציון between 29 Oct and 5 Nov" is a different
answer from "unavailable".

Say plainly that this is IKEA's own stock figure at a stated time, not a live
count of what is physically on the shelf right now. Only a person or a phone
call to the branch can confirm the latter.
