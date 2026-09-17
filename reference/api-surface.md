# Every IKEA Israel endpoint this plugin uses

Mapped 2026-09-17 by driving a real Chrome session against
`https://www.ikea.com/il/he/p/metod-suspension-rail-galvanised-60205664/` from an
Israeli residential connection, then re-verifying each finding from plain `curl`
on the same machine.

Marked **verified** where a request was actually issued and the response read.
Marked **inferred** where the conclusion is reasoning about observed data rather
than a direct test.

---

## The three routes

| # | Endpoint | Auth | Gives you |
|---|---|---|---|
| 1 | `sik.search.blue.cdtapps.com/il/he/search-result-page` | none | article numbers, Hebrew names, ILS prices, PDP URLs |
| 2 | `api.salesitem.ingka.com/availabilities/ru/il` | `X-Client-Id` | per-store quantity, restock dates, warehouse pick location |
| 3 | `www.ikea.com/il/he/meta-data/informera/stores-detailed.json` | none | the five IL stores, addresses, opening hours |

All three answer plain `curl` with no cookies, no session, no user-agent
spoofing and no browser. **verified**

This is the opposite of the sibling Grainger plugin, where the scripted tier
needs an exported signed-in session and the browser is the only route to a
price. Here the browser buys you nothing the JSON does not already have — and
costs you the bidi problem described in [`rtl-and-bidi.md`](rtl-and-bidi.md).
Use the browser to check a claim, not to gather data.

---

## 1. Search

```
GET https://sik.search.blue.cdtapps.com/il/he/search-result-page?q={query}&size={n}
```

No auth, CORS open, `size=200` returned 198 products in one call. **verified**

Accepts Hebrew (`q=מסילת תלייה`, percent-encoded), Latin product names (`q=billy`),
a bare article number (`q=60205664`) and the dotted form (`q=602.056.64`) — the
last two both resolve to the single matching article. **verified**

Products land at:

```
searchResultPage.products.main.items[].product
```

Fields worth having: `itemNo`, `itemType` (`ART` | `SPR`), `name` (the range
name, e.g. `METOD`), `typeName` (the Hebrew product noun), `itemMeasureReferenceText`,
`salesPrice.numeral`, `salesPrice.currencyCode`, `pipUrl`, `onlineSellable`.

`name` and `typeName` are two halves of one label. `name` alone is `METOD`,
which identifies nothing. Join them.

`onlineSellable: false` is common on IL and does **not** mean out of stock — the
METOD rail is `false` while sitting on 194 units in Netanya. It means IKEA Israel
will not ship it to you. **verified**

### Also exists but is not the search endpoint

`sik.search.blue.cdtapps.com/il/he/search` — the shorter path, which many
third-party write-ups name. It failed CORS from the page context. Use
`search-result-page`. **verified (failure)**

---

## 2. Availability — the one that matters

```
GET https://api.salesitem.ingka.com/availabilities/ru/il
    ?itemNos={comma,separated}
    &expand=StoresList,Restocks,SalesLocations
Header: X-Client-Id: <id>
```

### The expand trap

`expand=SalesLocations` on its own returns **HTTP 200 with the `salesLocations`
key entirely absent**. No warning, no error, no empty array — the key is not
there. Ask for all three or you silently lose the warehouse location:

```
expand=SalesLocations                        -> salesLocations missing   (200)
expand=StoresList,Restocks,SalesLocations    -> salesLocations present   (200)
```

**verified**, same article, same minute, both 200.

This is the failure mode worth guarding against: a caller that asked for one
expand value, got a clean 200, and found no sales locations will report "this
item has no warehouse location" — which is a sentence about the request, not
about the item. `scripts/ikea_il.py` hard-codes the full expand string for this
reason.

### The client id

| Value | Result |
|---|---|
| `b6c117e5-ae61-4ef5-b4cc-e0b1e37f0631` | **200** |
| header omitted | 401 `{"title":"The API key you provided does not exist"}` |
| `lff` | 401, same body |
| any other string | 401, same body |

**verified.** The UUID is the publicly circulated IKEA availability client id;
it is not anyone's personal credential and nothing about it is secret.

`lff` is interesting because it is what the site itself sends. Grepping the
loaded bundles for `X-Client-Id` finds it hard-coded in
`product-availability.route-*.js` as the literal string `"lff"` (lower-funnel
fragments) — and this public endpoint rejects it. **verified.** The site
therefore reaches availability through some path that accepts `lff`, which this
plugin has not mapped; no UUID appears anywhere in the 163 scripts the PDP
loads. **verified (absence).**

Consequence for the future: if the UUID starts returning 401, that is a rotated
key, not a dead endpoint. Override with `$IKEA_IL_CLIENT_ID` rather than
assuming the API is gone. The 401 body is unambiguous and easy to classify,
which is a kindness — nothing here returns a refusal disguised as an empty
result.

### Limits, stated by the API itself

A 100-item request returns 400 with its own JSON Schema in the body:

```json
{"items": {"maxLength": 15, "minLength": 8, "type": "string"},
 "maxItems": 50, "minItems": 1, "uniqueItems": true}
```

So: **50 article numbers per call, unique, 8–15 characters each.** **verified.**

50 articles × 9 class units came back as 450 availability rows in a single
response, ~300 KB. Batching is cheap; fanning out one article per request is
not just slower, it is nine times more rows for the same data.

### Response shape

```jsonc
{
  "availabilities": [ {
      "classUnitKey": { "classUnitCode": "206", "classUnitType": "STO" },
      "itemKey":      { "itemNo": "60205664", "itemType": "ART" },
      "availableForCashCarry": true,
      "buyingOption": {
        "cashCarry": {
          "availability": {
            "quantity": 194,
            "probability": { "thisDay": { "messageType": "HIGH_IN_STOCK",
                                          "colour": { "rgbHex": "#0A8A00" } } },
            "restocks": [ { "earliestDate": "2026-10-29",
                            "latestDate":   "2026-11-05",
                            "quantity": 12,
                            "reliability": "HIGH",
                            "type": "DELIVERY" } ],
            "updateDateTime": "2026-09-17T08:41:43.870Z"
          },
          "tags": ["COWORKER_PICKUP"],
          "unitOfMeasure": "PIECE",
          "eligibleForStockNotification": false
        },
        "homeDelivery": { "range": { "inRange": true } }
      }
  } ],
  "salesLocations": [ {
      "classUnitKey": { "classUnitCode": "206", "classUnitType": "STO" },
      "itemKey":      { "itemNo": "00263850", "itemType": "ART" },
      "salesLocations": [ { "division": "SELF_SERVE",
                            "type": "AISLE_AND_BIN",
                            "id": "11K000",
                            "aisleAndBin": { "aisle": "11", "bin": "K" },
                            "recommendationRank": 1 } ]
  } ],
  "timestamp": "...", "traceId": "..."
}
```

`quantity` is a real unit count, not a band. 194, 831, 41, 1337, 119, 146 across
the six units holding the METOD rail. **verified.**

`probability.thisDay.messageType` observed values: `HIGH_IN_STOCK`,
`MEDIUM_IN_STOCK`, `OUT_OF_STOCK` — across 450 rows drawn from 50 articles.
**verified.** A `LOW_IN_STOCK` sibling is plausible from the naming but was not
seen; do not enumerate it as known. **inferred, unconfirmed.**

`probability` has exactly one day key, `thisDay`, plus `updateDateTime`. There is
no forward-looking probability here. **verified.**

`tags` distinguishes how the item is collected: `CUSTOMER_PICKUP` (you take it
off the self-serve rack yourself) versus `COWORKER_PICKUP` (staff fetch it).
This agrees with the `division` on the sales location and is a second signal for
the same fact. **verified.**

`updateDateTime` varies by store and by article — 2026-09-16T16:21 for Beer
Sheva alongside 2026-09-17T09:39 for Rishon LeZion in one response. Quote it.
A quantity roughly a day old is normal here, not a fault, but it is also not a
live shelf count. **verified.**

### itemType ART vs SPR

`SPR` articles are sold as a pre-set combination. They are **not** a special case
for availability: sampling 50 SPR and 50 ART articles gave 187/400 and 201/400
non-zero store rows respectively, with SPR quantities up to 143. **verified.**

An SPR reading zero is a real zero, not an artefact of asking about a family
instead of a part. (Checked because the first SPR sampled read zero everywhere
and looked like one.)

---

## 3. Store directory

```
GET https://www.ikea.com/il/he/meta-data/informera/stores-detailed.json
```

Plain JSON array, no auth, 9 KB, five entries. **verified.**

### `name` is a trap

Every store's `name` is `"Northern Birch Ltd."` — the Israeli franchisee's legal
entity, identical across all five. The human-facing name is `displayName`
(`נתניה`) with `displayNameAlternate` (`איקאה נתניה`) as the long form.
**verified.**

Reading `name` gives you five identically-named stores and no error.

### `hours` is published and empty

```jsonc
"hours": { "normal": [], "exceptions": [], "restaurant": [], "bistro": [],
           "cafe": [], "clickncollect": [], "swedishFoodMarket": [],
           "smaland": [], "closed": [] }
```

Every array is empty for every IL store. The actual opening hours are Hebrew
prose in `extras.normal[0].body`:

> `א-ד: 10:00 - 20:00. ה': 10:00 - 22:00. ו' וערבי חג: 09:00 - 15:00.`

**verified.** A consumer that reads `hours.normal` concludes IKEA Israel
publishes no opening hours. It publishes them; it just does not publish them
there. `scripts/ikea_il.py stores` returns both fields side by side so the
emptiness is visible rather than assumed.

### Store codes

| Code | `displayName` | City |
|---|---|---|
| 206 | נתניה | נתניה |
| 217 | ראשון לציון | ראשון לציון |
| 318 | קריית אתא | קריית אתא |
| 531 | באר שבע | באר שבע |
| 613 | אשתאול | אזה"ת הר טוב |

**verified.** Note 613: `displayName` is אשתאול but the address city is
אזה"ת הר טוב. Matching a user's town against one field only will miss it.

### Class unit codes that are not stores

An availability response for one article returned **nine** class units: eight
`STO` and one `RU`.

- `RU/IL` — the country row. Carries `homeDelivery` only, never a cash-and-carry
  quantity. It is the national picture, not a store.
- `STO/523` — reported 1337 units cash-and-carry, and is **absent from the store
  directory**. **verified.** Almost certainly a distribution or fulfilment unit
  rather than a shoppable branch. **inferred** — not confirmed against any IKEA
  source.
- `STO/737`, `STO/738` — present with `availableForCashCarry: false`, no
  quantity, also absent from the directory. **verified.**

So `classUnitType == "STO"` does **not** mean "a store a customer can walk into".
Join against the directory and treat a code that is not in it as not-a-branch.
`scripts/ikea_il.py stock` surfaces this as `in_store_directory`.

Telling someone an item is in stock at 523 would send them to a building that is
not open to them.

---

## Geography

Everything above was issued from an Israeli residential IP. Whether any of the
three endpoints geo-fences non-IL traffic was **not tested** — there is no
working US-egress route on this machine as of 2026-09-02. Treat the IL-IP
requirement as unknown, not as absent.

---

## Conduct

Read-only. No cart, no order, no account, no sign-in, no stock-notification
subscription — `eligibleForStockNotification` is read and never acted on.
Batch rather than fan out. Nothing here automates purchasing.
