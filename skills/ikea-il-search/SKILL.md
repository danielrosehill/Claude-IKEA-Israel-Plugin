---
name: ikea-il-search
description: Find IKEA Israel articles by Hebrew name, English range name, or article number, and get ILS prices. Use before any stock question, because stock lookups need article numbers.
allowed-tools: Read, Bash(python3 *)
---

# Finding an article

Stock questions need article numbers. This is how you get one.

```bash
python3 scripts/ikea_il.py search "מסילת תלייה" --size 24
python3 scripts/ikea_il.py search billy
python3 scripts/ikea_il.py search 602.056.64     # dotted or plain, both resolve
```

No auth, no session. `--size 200` works.

## Reading the result

`name` is the range (`METOD`, `BILLY`) and identifies nothing on its own.
`typeName` is the Hebrew product noun (`מסילת תלייה`). **Join them** — "METOD
מסילת תלייה, 200 ס\"מ" is the label a person recognises.

`item_no` is the 8-digit article number. The site also writes it dotted
(`602.056.64`); they are the same thing and both are accepted as input.

`item_type` is `ART` (a single article) or `SPR` (a pre-set combination). Both
report real stock — an `SPR` reading zero is a real zero, not an artefact.

## The trap

`online_sellable: false` is common on IKEA Israel and does **not** mean out of
stock. The METOD rail is `false` while sitting on 194 units in Netanya. It means
IKEA Israel will not ship it — you collect it from a branch.

Never translate `online_sellable: false` into "unavailable". Check the branch.

## Price

`price` is a JSON number in `currency` (ILS). Use it. Do not lift a price off a
rendered page — see `reference/rtl-and-bidi.md` for why the DOM's price text has
invisible direction-override characters wedged inside the digits.

## Reporting

Give the article number alongside the name every time. It is the only thing that
survives a translation, a reorder or a bidi mangling, and it is what the next
lookup needs.
