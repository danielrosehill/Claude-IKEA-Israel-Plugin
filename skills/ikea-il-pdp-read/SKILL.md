---
name: ikea-il-pdp-read
description: Read an IKEA Israel product page in a real browser when the JSON is not enough, without being fooled by RTL text. Use only to confirm a surprising API answer or to read something genuinely client-side-only.
allowed-tools: Read, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__get_page_text, mcp__claude-in-chrome__read_page, mcp__claude-in-chrome__find, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__tabs_close_mcp
---

# Reading a PDP in a browser

**Check first whether you need to.** Price, article number, per-branch quantity,
aisle and bin and restock dates are all in the JSON — cleaner, fifty articles at
a time, no browser. See `ikea-il-branch-stock` and `ikea-il-search`.

Open a browser only to confirm a surprising API answer against what a customer
is shown, or to read genuinely client-side-only content.

## Selector discipline

The least specific hook that identifies the thing. IKEA ships UI changes
continuously; the specific hooks are the ones that rot. Full ladder in
`reference/dom-selectors.md`.

**Use:**

```js
document.querySelector('[data-product-no]')
```

One element carries `data-product-id`, `data-product-no`, `data-product-name`,
`data-product-type`, `data-product-price`, `data-online-sellable` — all
machine-formatted, no Hebrew, no currency symbol, no bidi marks.

```js
[...document.querySelectorAll('script[type="application/ld+json"]')]
  .map(s => JSON.parse(s.textContent))
  .find(o => o['@type'] === 'Product')
```

Take the `Product` block by `@type`, never by index. Gives `sku`/`mpn` dotted,
`offers.price`, `offers.priceCurrency`.

**Do not use:** hashed CSS-module classes like `_availabilityGroupContainer_11089_6`
— the `11089` is a build hash. Do not use `pipf-*`, `pipcom-*` or
`lower-funnel-fragments-*` class names directly; three generations of prefix
coexist on one page, which is the argument against depending on any of them.
If you must, match a substring of the semantic part: `[class*="product-identifier"]`.

## The RTL problem

`<html dir="rtl" lang="he-IL">`, and rendered numeric text carries **invisible
bidi control characters inside the digits** — `U+202D` before and `U+202C` after,
verified on the live price. They survive copy/paste, show up in no terminal, and
silently break `\d+` matches so a price regex returns nothing at all.

JSON-LD and the `data-product-*` attributes carry none. **Take numbers from
those, not from rendered text.** If you must parse page text, strip
`[‎‏‪-‮⁦-⁩]` first.

## Practical notes

- A `role="dialog"` cookie banner is the **first** `[role="dialog"]` on every
  page and will shadow a query aimed at the store sheet. Scope past it.
  **Do not dismiss or accept it** — that is the browser owner's decision, not
  yours. Reading the page works fine with it present.
- `offers.availability: "https://schema.org/InStock"` in JSON-LD is a *national*
  claim and says nothing about any branch. Never repeat it as a branch answer.
- Store selection persists across reloads, so the PDP renders the previously
  chosen branch's status without re-picking.
- Find controls by accessible name, not by screenshot coordinates.
- Close tabs you opened.
