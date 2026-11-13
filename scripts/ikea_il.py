#!/usr/bin/env python3
"""IKEA Israel (ikea.com/il/he) read-only scanner.

Three public endpoints, no session, no cookies, no browser. Verified 2026-09-17.

  search      sik.search.blue.cdtapps.com/il/he/search-result-page
  stock       api.salesitem.ingka.com/availabilities/ru/il   (needs X-Client-Id)
  stores      www.ikea.com/il/he/meta-data/informera/stores-detailed.json

Everything prints JSON on stdout. Failures print a classified JSON error and
exit non-zero, so a caller that only checks the exit code is still told the
truth. See reference/api-surface.md for why that matters here.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SEARCH_BASE = "https://sik.search.blue.cdtapps.com/il/he/search-result-page"
AVAIL_BASE = "https://api.salesitem.ingka.com/availabilities/ru/il"
STORES_URL = "https://www.ikea.com/il/he/meta-data/informera/stores-detailed.json"

# Public IKEA availability client id. Not a secret and not a personal one: it is the
# id the public availability endpoint accepts. The site's own bundle sends
# "lff", which this endpoint rejects with 401 -- see reference/api-surface.md.
CLIENT_ID = os.environ.get("IKEA_IL_CLIENT_ID", "b6c117e5-ae61-4ef5-b4cc-e0b1e37f0631")

# The API caps itemNos at 50 and enforces uniqueness. Its own 400 body says so.
MAX_ITEMS = 50

# expand= is not a menu you pick from. Asking for SalesLocations alone returns
# 200 with the key absent. All three or you get a silent partial answer.
EXPAND = "StoresList,Restocks,SalesLocations"

# Bidi control characters the RTL DOM sprinkles through rendered text. They are
# invisible, they survive copy/paste, and they break \d+ matches. API JSON is
# clean -- this is only needed when parsing text lifted from the page.
BIDI = re.compile("[‎‏‪-‮⁦-⁩]")

TIMEOUT = 30


def fail(kind, detail, **extra):
    out = {"status": kind, "detail": detail}
    out.update(extra)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(2)


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 401:
            fail("NO_CLIENT_ID",
                 "Availability endpoint rejected the client id. Set $IKEA_IL_CLIENT_ID.",
                 http_status=401, body=body[:300])
        if e.code == 400:
            fail("BAD_REQUEST", "The API rejected the request parameters.",
                 http_status=400, body=body[:600])
        fail("HTTP_ERROR", "HTTP %d from %s" % (e.code, urllib.parse.urlsplit(url).netloc),
             http_status=e.code, body=body[:300])
    except urllib.error.URLError as e:
        fail("NETWORK", "Could not reach %s: %s" % (urllib.parse.urlsplit(url).netloc, e.reason))
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        fail("NOT_JSON", "200 but the body did not parse as JSON. Capture it before "
                         "concluding the endpoint is gone.", head=body[:300])


def strip_bidi(s):
    return BIDI.sub("", s) if isinstance(s, str) else s


def normalise_item_no(raw):
    """602.056.64, 60205664 and 060205664 all mean the same article."""
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    return digits.zfill(8)


# --------------------------------------------------------------------- stores

def load_stores():
    data = get_json(STORES_URL)
    out = {}
    for s in data:
        out[str(s.get("id"))] = {
            # `name` is the franchisee legal entity, identical for every store.
            # `displayName` is the one a human means. Do not swap these.
            "id": str(s.get("id")),
            "display_name": s.get("displayName"),
            "display_name_long": s.get("displayNameAlternate"),
            "legal_entity": s.get("name"),
            "city": (s.get("address") or {}).get("city"),
            "address": (s.get("address") or {}).get("displayAddress"),
            "cash_and_carry": s.get("cashAndCarry"),
            "classification": (s.get("buClassification") or {}).get("code"),
            "url": s.get("storePageUrl"),
            # hours.normal is published but empty for every IL store. The real
            # hours are Hebrew prose in extras.normal[0].body.
            "hours_structured": (s.get("hours") or {}).get("normal") or [],
            "hours_text": [e.get("body") for e in (s.get("extras") or {}).get("normal", [])],
        }
    return out


def cmd_stores(args):
    stores = load_stores()
    print(json.dumps({"store_count": len(stores), "stores": list(stores.values())},
                     ensure_ascii=False, indent=1))


# --------------------------------------------------------------------- search

def cmd_search(args):
    q = urllib.parse.quote(args.query)
    url = "%s?q=%s&size=%d" % (SEARCH_BASE, q, args.size)
    data = get_json(url)
    try:
        items = data["searchResultPage"]["products"]["main"]["items"]
    except (KeyError, TypeError):
        fail("SHAPE_CHANGED", "search-result-page returned JSON without "
                              "searchResultPage.products.main.items",
             top_keys=list(data)[:10])
    rows = []
    for it in items:
        p = it.get("product")
        if not p or not p.get("itemNo"):
            continue
        rows.append({
            "item_no": p["itemNo"],
            "item_type": p.get("itemType"),
            "name": p.get("name"),
            "type_name": p.get("typeName"),
            "measure": p.get("itemMeasureReferenceText"),
            "price": (p.get("salesPrice") or {}).get("numeral"),
            "currency": (p.get("salesPrice") or {}).get("currencyCode"),
            "online_sellable": p.get("onlineSellable"),
            "url": p.get("pipUrl"),
        })
    print(json.dumps({"query": args.query, "returned": len(rows), "results": rows},
                     ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------- stock

def fetch_availability(item_nos):
    if len(item_nos) > MAX_ITEMS:
        fail("TOO_MANY_ITEMS",
             "The API caps itemNos at %d per call; chunk the list." % MAX_ITEMS,
             asked=len(item_nos))
    url = "%s?itemNos=%s&expand=%s" % (AVAIL_BASE, ",".join(item_nos), EXPAND)
    return get_json(url, {"X-Client-Id": CLIENT_ID})


def cmd_stock(args):
    item_nos = []
    for raw in args.items:
        for part in raw.split(","):
            n = normalise_item_no(part)
            if n and n not in item_nos:
                item_nos.append(n)
    if not item_nos:
        fail("NO_ITEMS", "No parseable article numbers in %r" % args.items)

    data = fetch_availability(item_nos)
    stores = {} if args.no_store_names else load_stores()

    # Warehouse pick location, keyed (store, item). Present only for items that
    # are picked from the warehouse at all; market-hall goods have none, and an
    # absent entry is not an error.
    locs = {}
    for sl in data.get("salesLocations") or []:
        key = (sl["classUnitKey"]["classUnitCode"], sl["itemKey"]["itemNo"])
        locs[key] = [{
            "division": l.get("division"),
            "type": l.get("type"),
            "id": l.get("id"),
            "aisle": (l.get("aisleAndBin") or {}).get("aisle"),
            "bin": (l.get("aisleAndBin") or {}).get("bin"),
        } for l in sl.get("salesLocations", [])]

    by_item = {}
    for a in data.get("availabilities") or []:
        cu = a["classUnitKey"]
        item_no = a["itemKey"]["itemNo"]
        row = by_item.setdefault(item_no, {
            "item_no": item_no,
            "item_type": a["itemKey"].get("itemType"),
            "stores": [],
            "country_home_delivery": None,
        })
        if cu["classUnitType"] == "RU":
            hd = (a.get("buyingOption") or {}).get("homeDelivery") or {}
            row["country_home_delivery"] = (hd.get("range") or {}).get("inRange")
            continue

        cc = ((a.get("buyingOption") or {}).get("cashCarry")) or {}
        avail = cc.get("availability") or {}
        prob = (avail.get("probability") or {}).get("thisDay") or {}
        code = cu["classUnitCode"]
        meta = stores.get(code)
        entry = {
            "store_code": code,
            "store_name": meta["display_name"] if meta else None,
            "in_store_directory": meta is not None,
            "quantity": avail.get("quantity"),
            "message_type": prob.get("messageType"),
            "available_for_cash_carry": a.get("availableForCashCarry"),
            "pickup": cc.get("tags") or [],
            "unit_of_measure": cc.get("unitOfMeasure"),
            "updated": avail.get("updateDateTime"),
            "restocks": avail.get("restocks") or [],
            "sales_locations": locs.get((code, item_no), []),
        }
        if args.in_stock_only and not entry["quantity"]:
            continue
        row["stores"].append(entry)

    for row in by_item.values():
        row["stores"].sort(key=lambda e: (e["quantity"] is None, -(e["quantity"] or 0)))

    print(json.dumps({
        "asked": item_nos,
        "returned": len(by_item),
        "expand": EXPAND,
        "items": list(by_item.values()),
    }, ensure_ascii=False, indent=1))


def cmd_locate(args):
    """One article, one store: where in the building, and how many."""
    item_no = normalise_item_no(args.item)
    if not item_no:
        fail("NO_ITEMS", "Could not parse an article number from %r" % args.item)
    stores = load_stores()
    target = None
    for code, meta in stores.items():
        if args.store in (code, meta["display_name"], meta["display_name_long"]):
            target = meta
            break
    if target is None:
        fail("UNKNOWN_STORE",
             "No IL store matches %r." % args.store,
             known=[{"code": c, "name": m["display_name"]} for c, m in stores.items()])

    data = fetch_availability([item_no])
    out = {"item_no": item_no, "store_code": target["id"], "store_name": target["display_name"]}
    for a in data.get("availabilities") or []:
        if a["classUnitKey"]["classUnitCode"] != target["id"]:
            continue
        avail = (((a.get("buyingOption") or {}).get("cashCarry")) or {}).get("availability") or {}
        out["quantity"] = avail.get("quantity")
        out["message_type"] = ((avail.get("probability") or {}).get("thisDay") or {}).get("messageType")
        out["restocks"] = avail.get("restocks") or []
        out["updated"] = avail.get("updateDateTime")
    for sl in data.get("salesLocations") or []:
        if sl["classUnitKey"]["classUnitCode"] != target["id"]:
            continue
        out["sales_locations"] = [{
            "division": l.get("division"),
            "type": l.get("type"),
            "id": l.get("id"),
            "aisle": (l.get("aisleAndBin") or {}).get("aisle"),
            "bin": (l.get("aisleAndBin") or {}).get("bin"),
        } for l in sl.get("salesLocations", [])]
    out.setdefault("sales_locations", [])
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_probe(args):
    """Cheapest possible proof that each of the three routes still answers."""
    result = {}

    stores = load_stores()
    result["stores"] = {"ok": True, "count": len(stores),
                        "codes": sorted(stores)}

    data = get_json("%s?q=billy&size=1" % SEARCH_BASE)
    n = len(data.get("searchResultPage", {}).get("products", {})
                .get("main", {}).get("items", []))
    result["search"] = {"ok": n > 0, "items": n}

    av = fetch_availability(["00263850"])
    result["availability"] = {
        "ok": bool(av.get("availabilities")),
        "rows": len(av.get("availabilities") or []),
        "sales_locations_present": bool(av.get("salesLocations")),
        "client_id_source": "env" if os.environ.get("IKEA_IL_CLIENT_ID") else "built-in",
    }

    result["status"] = "OK" if all(v.get("ok") for v in
                                   (result["stores"], result["search"],
                                    result["availability"])) else "DEGRADED"
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if result["status"] != "OK":
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("probe", help="prove all three routes answer").set_defaults(fn=cmd_probe)
    sub.add_parser("stores", help="the IL store roster").set_defaults(fn=cmd_stores)

    p = sub.add_parser("search", help="find articles by name, Hebrew or article number")
    p.add_argument("query")
    p.add_argument("--size", type=int, default=24)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("stock", help="per-store stock for up to 50 articles")
    p.add_argument("items", nargs="+", help="article numbers, dotted or plain")
    p.add_argument("--in-stock-only", action="store_true")
    p.add_argument("--no-store-names", action="store_true",
                   help="skip the store directory fetch")
    p.set_defaults(fn=cmd_stock)

    p = sub.add_parser("locate", help="one article in one store: quantity and pick location")
    p.add_argument("item")
    p.add_argument("store", help="store code (206) or Hebrew display name")
    p.set_defaults(fn=cmd_locate)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
