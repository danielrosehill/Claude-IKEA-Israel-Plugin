---
name: ikea-il-route
description: Decide how to reach ikea.com/il/he and prove the route answers before spending calls on it. Use at the start of any IKEA Israel task, and whenever a lookup comes back empty.
allowed-tools: Read, Bash(python3 *)
---

# Choosing a route into IKEA Israel

Three public endpoints, no session, no cookies, no browser. Unlike most retail
scanners, the scripted tier here is the *complete* tier — it is not a degraded
fallback for a browser route.

## Order of preference

1. **`scripts/ikea_il.py`** — search, per-store quantity, restock dates,
   warehouse pick location, store roster. Everything a procurement question
   needs.
2. **`claude-in-chrome`** — only to confirm a surprising answer against what a
   customer is shown, or to read something genuinely client-side-only.

There is no third route and no session to export. If the script tier fails, the
browser will not rescue it — both hit the same endpoints.

## Always first

```bash
python3 scripts/ikea_il.py probe
```

One call per endpoint. Read `status` and the three `ok` flags before anything
else.

## When probe says no

| `status` | Meaning | Do |
|---|---|---|
| `NO_CLIENT_ID` | availability endpoint returned 401 | The client id rotated. Set `$IKEA_IL_CLIENT_ID`. This is **not** the API being gone — the 401 body says so explicitly |
| `NETWORK` | endpoint unreachable | Ordinary connectivity. Report it as itself |
| `HTTP_ERROR` | a real HTTP status | Report the status. Do not retry in a loop |
| `NOT_JSON` | 200, body is not JSON | The endpoint may have changed shape. Capture the body and look before concluding anything |
| `SHAPE_CHANGED` | JSON without the expected keys | Same. Read `reference/api-surface.md` and compare |
| `BAD_REQUEST` | 400 | The API states its own constraint in the body. Read it — it is usually the 50-item cap |

## The empty answer that is not an answer

Two ways this site returns a confident nothing:

- **`expand=` missing a value.** `expand=SalesLocations` alone returns 200 with
  the `salesLocations` key absent — reads exactly like "this item has no
  warehouse location". The script hard-codes the full expand string; if you ever
  hand-roll a request, all three values or none.
- **`hours.normal` in the store directory is empty for every IL store**, while
  the real hours sit in `extras.normal[0].body` as Hebrew prose. Reading the
  structured field concludes IKEA Israel publishes no opening hours.

Before reporting that something does not exist, ask whether the lookup could
have been lying. If a query that should hit comes back empty, suspect the query.

## What never happens here

- **No sign-in, no cart, no order, no stock-notification subscription.**
  Read-only against a public catalogue.
- **No fan-out.** 50 articles per availability call. One request per article is
  nine times the rows for the same data.
- **No retry loops.** Two attempts, then change route or say what failed.
