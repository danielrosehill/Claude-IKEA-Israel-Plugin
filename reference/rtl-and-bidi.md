# Hebrew, RTL and the invisible characters in between

Verified 2026-09-17 against `ikea.com/il/he`.

The IL site is a genuinely right-to-left document: `<html dir="rtl" lang="he-IL">`.
That is not a styling detail. It changes what the DOM hands you, and it is the
single best reason to prefer this site's JSON over its rendered text.

---

## The finding

Price text on a product page, read straight out of the DOM:

```
מחיר יחידה: ‭30‬₪/מ'
```

Those two invisible characters around the `30` are real:

| Position | Code point | Name |
|---|---|---|
| before the digits | `U+202D` | LEFT-TO-RIGHT OVERRIDE |
| after the digits | `U+202C` | POP DIRECTIONAL FORMATTING |

**verified** by enumerating code points on the live page.

The same page's JSON-LD block contains **zero** bidi control characters.
**verified** — scanned for `U+200E`, `U+200F`, `U+202A`–`U+202E`, `U+2066`–`U+2069`
across all three `<script type="application/ld+json">` blocks.

## Why it bites

The overrides sit *inside* the numeric run. They are zero-width, they survive
copy and paste, they survive being written to a file, and they do not show up in
a terminal or a diff. A regex like `(\d+)\s*₪` matches — until the day the
override lands between the digits and the currency sign, at which point it stops
matching and returns nothing.

Nothing errors. You get an empty capture group, which reads exactly like "this
page has no price".

The same applies to any identifier the site renders with digits embedded in
Hebrew: article numbers, phone numbers, dates, aisle and bin. The direction is
not carried by the characters — it is carried by these marks and by the
surrounding `dir`. Strip the marks and the digits are still correct; keep them
and every naive string comparison is a coin toss.

## What to do

**Do not read prices or numbers out of the DOM.** Two clean sources exist:

1. `scripts/ikea_il.py search` — the search API's `salesPrice.numeral` is a JSON
   number. No formatting, no marks, no parsing.
2. JSON-LD on the PDP — `offers.price`, `offers.priceCurrency`, `sku`, `mpn`.
   Clean, and the only structured block on the page worth reading.

If you must take text from the page anyway, strip the controls first:

```python
BIDI = re.compile("[‎‏‪-‮⁦-⁩]")
clean = BIDI.sub("", text)
```

`scripts/ikea_il.py` exposes this as `strip_bidi()`. It is deliberately not
applied to API output, which does not need it — running it there would hide the
fact that the API is clean.

---

## Writing Hebrew back out

Everything the API returns is plain Hebrew with no direction information:
`נתניה`, `ראשון לציון`, `מסילת תלייה`, `א-ד: 10:00 - 20:00`.

Plain text carries no direction. A consumer that renders it left-to-right will
reorder the separators inside anything mixed — dates, hours ranges, addresses
with house numbers. `א-ד: 10:00 - 20:00` is exactly the shape that goes wrong.

So: in a terminal reply, quote the Hebrew and let it be. In anything that gets
sent, published or typeset — an email, a PDF, an HTML report — wrap it properly
in an RTL container rather than hoping. That is out of scope for this plugin and
is what the `rtl-email` and `hebrew-correspondence` plugins exist for.

---

## Store names and matching

`displayName` is `נתניה`; `displayNameAlternate` is `איקאה נתניה`. A user is as
likely to type either, or to type the city while the store is filed under
another name — Eshtaol (`אשתאול`) sits at an address whose city field reads
`אזה"ת הר טוב`. **verified.**

Match a user's string against `displayName`, `displayNameAlternate`, the address
`city` and the numeric store code, and when none hit, say which five exist
rather than guessing the nearest. `scripts/ikea_il.py locate` returns the roster
in its `UNKNOWN_STORE` error for exactly that reason.
