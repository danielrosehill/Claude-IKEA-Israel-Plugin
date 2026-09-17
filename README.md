# Claude IKEA Israel Plugin

A Claude Code plugin for checking what IKEA Israel actually has, in which of its
five branches, and where in the building it sits.

IKEA Israel publishes **real unit counts per store** — not a traffic-light band,
not "limited availability", but `194`. It also publishes the self-serve aisle and
bin, and the scheduled restock date when a branch is out. All of it is reachable
from three public endpoints with no session, no cookies and no browser.

Mapped 2026-09-17 by driving a real Chrome session from an Israeli residential
connection, then re-verifying every finding from plain `curl`. Sibling to
[Claude-Grainger-Plugin](https://github.com/danielrosehill/Claude-Grainger-Plugin)
and [Claude-Uline-Plugin](https://github.com/danielrosehill/Claude-Uline-Plugin),
built on the same principle: the value is the encoded routing and the verification
discipline, not the integration.

## What makes this one different

Grainger and Uline are exercises in getting past a bot wall. This is the
opposite problem. The endpoints answer `curl` happily on the first try — the
difficulty is that several of the answers are **wrong in ways that look right**.

Four traps, all verified, all of which return HTTP 200:

| Looks like | Actually |
|---|---|
| `expand=SalesLocations` → no warehouse location for this item | The key is absent because the expand list was incomplete. All three values or none |
| `hours.normal: []` → IKEA Israel publishes no opening hours | It publishes them as Hebrew prose in `extras.normal[0].body` |
| Store `name` → five stores all called "Northern Birch Ltd." | That is the franchisee. The name a human means is `displayName` |
| `STO/523` has 1337 units → the best-stocked branch | Not in the store directory. Not a building a customer can enter |

Plus one that bites at the character level: rendered price text on the RTL site
carries **invisible bidi override characters wedged inside the digits**
(`U+202D`, `U+202C`), which silently break `\d+` matches. The JSON is clean. That
is most of why this plugin reads JSON and not pages.

## Install

```
/plugin marketplace add danielrosehill/Claude-Code-Plugins
/plugin install ikea-israel@danielrosehill
```

## Setup

None. No account, no session export, no cookie jar.

The availability endpoint needs an `X-Client-Id`; a working public one ships in
`scripts/ikea_il.py`. It is not a secret and not a personal credential. If it
ever starts returning 401, that is a rotated key rather than a dead endpoint —
override it:

```bash
export IKEA_IL_CLIENT_ID=...
```

Check the whole thing in one call:

```bash
python3 scripts/ikea_il.py probe
```

## Commands

| Command | Does |
|---|---|
| `/ikea-israel:ikea-find <need>` | Search by Hebrew or English, return article numbers and ILS prices |
| `/ikea-israel:ikea-stock <article>` | Unit counts across all five branches, plus restock dates |
| `/ikea-israel:ikea-where <article> <branch>` | Aisle and bin, or full-serve counter, plus quantity |

Skills: `ikea-il-route`, `ikea-il-search`, `ikea-il-branch-stock`,
`ikea-il-warehouse-location`, `ikea-il-pdp-read`.

## Scripts

```bash
python3 scripts/ikea_il.py probe                       # all three routes, one call each
python3 scripts/ikea_il.py stores                      # the five IL branches
python3 scripts/ikea_il.py search "מסילת תלייה"        # Hebrew, English or article number
python3 scripts/ikea_il.py search 602.056.64           # dotted form works too
python3 scripts/ikea_il.py stock 602.056.64 00263850   # up to 50 articles per call
python3 scripts/ikea_il.py stock 00263850 --in-stock-only
python3 scripts/ikea_il.py locate 00263850 נתניה       # one article, one branch
```

Python 3 standard library only. No dependencies. Everything prints JSON;
failures print a classified JSON error and exit non-zero, so a caller that only
checks the exit code is still told the truth.

```jsonc
// locate 00263850 נתניה
{ "item_no": "00263850", "store_code": "206", "store_name": "נתניה",
  "quantity": 0, "message_type": "OUT_OF_STOCK",
  "sales_locations": [ { "division": "SELF_SERVE", "type": "AISLE_AND_BIN",
                         "id": "11K000", "aisle": "11", "bin": "K" } ] }
```

Note that an out-of-stock article still reports its aisle and bin. Location and
quantity are independent facts; quote both or neither.

## The five branches

| Code | Name | City |
|---|---|---|
| 206 | נתניה | נתניה |
| 217 | ראשון לציון | ראשון לציון |
| 318 | קריית אתא | קריית אתא |
| 531 | באר שבע | באר שבע |
| 613 | אשתאול | אזה"ת הר טוב |

613 is the one that breaks naive name matching — filed as אשתאול, addressed in
אזה"ת הר טוב.

An availability response returns **nine** class units, not five. `RU/IL` is the
national home-delivery row; `523`, `737` and `738` are not branches. The script
marks every row with `in_store_directory` so this is visible rather than
assumed.

## Selector policy

Where the browser tier does touch the DOM, it targets the **least specific hook
that identifies the thing** — `[data-product-no]` rather than `.pipf-page`,
`script[type="application/ld+json"]` filtered by `@type`, `role` and
accessible name rather than class or coordinates.

Three generations of class prefix coexist on a single PDP (`pipf-`, `pipcom-`,
`lower-funnel-fragments-`), and the CSS-module classes carry a build hash
(`_availabilityGroupContainer_11089_6`). Whichever you hard-code, there is
precedent on the same page for it being replaced. Full ladder, most durable
first, in [`reference/dom-selectors.md`](reference/dom-selectors.md).

## Docs

- [`reference/api-surface.md`](reference/api-surface.md) — every endpoint,
  marked verified or inferred, with the refusal modes and the 50-item cap
- [`reference/rtl-and-bidi.md`](reference/rtl-and-bidi.md) — the invisible
  characters, where they are and where they are not
- [`reference/dom-selectors.md`](reference/dom-selectors.md) — selector ladder,
  what rots and what does not
- [`profiles/ikea-il.json`](profiles/ikea-il.json) — the whole lot,
  machine-readable

## Conduct

Read-only, low-rate, against a public catalogue. No account, no sign-in, no
cart, no orders, no stock-notification subscriptions, no captcha handling, no
parallel fan-out. Nothing here automates purchasing.

IKEA's data belongs to IKEA. This is a research aid for a customer deciding
which branch to drive to, subject to IKEA's terms.

## Status

Verified 2026-09-17 against the live site. Whether the endpoints geo-fence
non-Israeli traffic was **not tested** — treat that as unknown rather than
absent. Undocumented endpoints change without notice: if a shape looks wrong,
capture the body and compare against `reference/api-surface.md` before
concluding the site is down.

MIT.
