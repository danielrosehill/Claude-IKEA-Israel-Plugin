# Reading a PDP in the browser, and how little to depend on

Mapped 2026-09-17 on
`https://www.ikea.com/il/he/p/metod-suspension-rail-galvanised-60205664/`
in a real Chrome session.

**Read this before writing any selector.** The governing rule for this plugin is
the least specific hook that identifies the thing — because IKEA ships UI
changes continuously and the specific hooks are the ones that rot.

---

## The ladder, most durable first

### 1. `data-product-*` on the page root — use this

One element on the PDP carries the whole product identity as attributes:

```html
<div class="pipf-page js-product-pip"
     data-product-id="60205664"
     data-product-no="60205664"
     data-product-name="METOD"
     data-product-type="ART"
     data-product-price="60"
     data-product-quantity="1"
     data-online-sellable="false">
```

Select on the attribute, never on the class:

```js
document.querySelector('[data-product-no]')
```

Why this one: the values are machine-formatted. No currency symbol, no Hebrew,
no thousands separator, and **no bidi control characters** — unlike the rendered
price a few nodes away. It is also the only place `itemType` and
`onlineSellable` appear in the DOM at all.

`[data-product-no]` survives a class rename, a design-system swap and a
re-layout. `.pipf-page` survives none of them.

### 2. JSON-LD — use this for price and SKU

```js
[...document.querySelectorAll('script[type="application/ld+json"]')]
  .map(s => JSON.parse(s.textContent))
  .find(o => o['@type'] === 'Product')
```

Three blocks on the page; take the `Product` one by `@type`, not by index.
Gives `sku` and `mpn` in dotted form (`602.056.64`), `offers.price`,
`offers.priceCurrency`, `offers.availability` (a schema.org URL),
`name`, `category`, `color`, and the physical dimensions as Hebrew strings
(`"200 ס\"מ"`).

Clean of bidi marks. **verified.**

`offers.availability: "https://schema.org/InStock"` is a *national* claim. It
says nothing about any branch. Do not repeat it as if it did.

### 3. `data-skapa` — the design system marker

155 elements carry it. Skapa is IKEA's design system; the attribute marks a
component boundary. Useful for scoping a query ("the nearest component wrapper")
without naming a class. Not useful for identifying *which* component.

### 4. Semantic HTML and ARIA — use for interaction

`h1` is the product title. `role="dialog"` is the only reliable handle on the
store-picker sheet and the cookie banner alike. 55 elements carry `role`,
35 carry `aria-label`.

Prefer these to coordinates when clicking. Find the control by its accessible
name, not by where it sat in a screenshot.

### 5. `pipcom-*` / `pipf-*` / `lower-funnel-fragments-*` — tolerate, don't target

Three generations of class prefix coexist on one page:

| Prefix | Example | Note |
|---|---|---|
| `pipf-` | `pipf-product-identifier`, `pipf-page` | older PIP frame |
| `pipcom-` | `pipcom-price-module`, `pipcom-typography-heading-s` | newer component library |
| `lower-funnel-fragments-` | `lower-funnel-fragments-store-section__button` | the availability micro-frontend |

If you must use one, match on a substring of the *semantic* part and accept
either generation:

```js
document.querySelector('[class*="product-identifier"]')   // -> "602.056.64"
document.querySelector('[class*="availability"]')
```

Three prefixes for one page is itself the argument: whichever you hard-code,
there is precedent for it being replaced.

### 6. Hashed CSS-module classes — never target

```
_availabilityGroupContainer_11089_6
_availabilityGroupWrapper_11089_1
```

The `11089` is a build hash. It changes on every deploy that touches the file.
A selector containing one is already broken; it just has not noticed yet.

---

## The availability panel

The store section renders inside the `lower-funnel-fragments` micro-frontend and
resolves to text like:

```
איך ניתן לקבל את המוצר
החלפת חנות
איקאה נתניה
חנות - במלאי
```

Clicking **בדוק מלאי בחנות** / **החלפת חנות** opens a `role="dialog"` sheet
listing all five stores with a per-store status line, plus a
**הצג רק חנויות עם מלאי זמין** toggle. **verified.**

The selected store persists across a reload — it is stored client-side, so the
PDP renders the chosen branch's status on next load without re-picking.
**verified.**

**But do not scrape this panel.** It gives you a Hebrew status band
(`חנות - במלאי`) where the API gives you `194`. It gives you no aisle, no bin, no
restock date, and it costs a browser session and several clicks per article
against the API's fifty per request. Its only honest use is confirming that what
the API said matches what a customer would be shown.

## The cookie banner

A `role="dialog"` consent banner sits at the bottom of every page and is the
first `[role="dialog"]` in the document. It will shadow a
`document.querySelector('[role="dialog"]')` aimed at the store sheet.

Do not dismiss it. Accepting cookie or consent banners is a decision for the
person whose browser it is, not for an agent reading a page. Scope past it
instead — take the last matching dialog, or scope to the availability container
first. Reading the page works fine with the banner present. **verified.**

---

## When to open a browser at all

Rarely. Everything on this page that a procurement question needs — price,
article number, per-branch quantity, aisle and bin, restock date — is in the
JSON described in [`api-surface.md`](api-surface.md), in cleaner form, fifty
articles at a time, with no session.

Open a browser to:

- confirm a surprising API answer against what a customer actually sees
- read something genuinely only rendered client-side (long description, the
  assembly-instructions links, the room-set imagery)
- check that a page still exists in the shape this document describes

Do not open a browser to gather data the script tier already returns. It is
slower, it drives the user's own visible Chrome, and it hands you bidi-polluted
text in place of numbers.
