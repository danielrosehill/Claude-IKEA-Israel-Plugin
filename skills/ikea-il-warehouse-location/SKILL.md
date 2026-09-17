---
name: ikea-il-warehouse-location
description: Find where in an IKEA Israel store an article is physically picked — self-serve aisle and bin, or full-serve warehouse counter. Use when someone is going to the store and needs to find the item.
allowed-tools: Read, Bash(python3 *)
---

# Where in the building is it

The availability API returns the pick location per store, per article.

```bash
python3 scripts/ikea_il.py locate 00263850 206
```

```json
"sales_locations": [
 { "division": "SELF_SERVE", "type": "AISLE_AND_BIN",
   "id": "11K000", "aisle": "11", "bin": "K" }
]
```

## Two shapes, and they mean different errands

**`SELF_SERVE` / `AISLE_AND_BIN`** — flat-pack, picked by the customer.
`aisle` and `bin` are the numbers painted on the self-serve warehouse racking.
Report them as **aisle 11, bin K**. The `id` (`11K000`) is the same thing
concatenated; prefer the parsed fields.

**`WAREHOUSE` / `CONTACT_STAFF`** — full-serve. The customer cannot pick it; a
coworker fetches it. Here the `id` is a **store-local, free-form string** and is
not an aisle/bin in disguise. One article across five branches:

```
206  702105      531  407204
217  FS 071      613  406000
318  61C000      523  RLSC B
```

Six values, four different formats. **Do not parse these. Do not present one as
an aisle.** Say "full-serve — ask staff at the collection point", and quote the
raw id only if the person specifically wants something to show a coworker.

The `pickup` tag on the availability row agrees with this and is a second
signal for the same fact: `CUSTOMER_PICKUP` goes with `SELF_SERVE`,
`COWORKER_PICKUP` with `WAREHOUSE`.

## When there is no location at all

Small market-hall goods — glassware, candles, textiles — return **no**
`salesLocations` entry. That is correct and not an error: they are taken off a
display shelf in the showroom, not picked from a numbered rack. Say so; do not
report it as missing data.

## The one that will fool you

`expand=SalesLocations` on its own returns **HTTP 200 with the `salesLocations`
key absent entirely**. Not an empty array — absent. Which reads exactly like
"this article has no warehouse location".

The full string is required:

```
expand=StoresList,Restocks,SalesLocations
```

`scripts/ikea_il.py` hard-codes it. If you ever build the URL by hand and get
back nothing, suspect the expand list before you conclude anything about the
article.

## An aisle is not a stock check

The pick location persists whether or not anything is on the rack — an
out-of-stock article still reports aisle 11, bin K. **verified.** Location and
quantity are independent; quote both or neither.
