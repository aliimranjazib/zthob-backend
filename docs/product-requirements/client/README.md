# Client Product Overview (Editor Guide)

This folder contains the **client-facing** product overview — written in plain language for business stakeholders, not developers.

## Public URLs (after deploy)

| Resource | URL |
|----------|-----|
| Web page | `https://app.mgask.net/product-overview/` |
| PDF download | `https://app.mgask.net/product-overview/pdf/` |

## Chapter files

Edit markdown in `chapters/` — files are loaded in numeric order:

| File | Chapter |
|------|---------|
| `01-introduction.md` | Introduction |
| `02-who-uses-mgask.md` | Who Uses Mgask |
| `03-customer-app.md` | Customer App |
| `04-tailor-and-owner-app.md` | Tailor and Owner App |
| `05-rider-app.md` | Rider App |
| `06-how-orders-work.md` | How Orders Work |
| `07-payments-and-delivery.md` | Payments and Delivery |
| `08-staff-and-access.md` | Staff and Access |
| `09-glossary.md` | Glossary |
| `10-about-this-document.md` | About This Document |

## How to update

1. Edit the relevant chapter `.md` file(s)
2. Deploy to staging/production (markdown is bundled in the Docker image)
3. Regenerate the PDF (optional but recommended before sharing):

```bash
node scripts/export-client-overview-pdf.mjs
```

4. Share the web URL or PDF with the client

## Writing guidelines

- Use plain business language — no code, API paths, or technical status names
- Group features by **user and app**, not by backend system
- Use mermaid diagrams sparingly (user journeys only)
- Do not include internal notes, known gaps, or QA content

## Internal vs client docs

| Audience | Location |
|----------|----------|
| **Client** | This folder + `/product-overview/` |
| **Dev / QA** | `../PRODUCT_REQUIREMENTS.md` and appendices |
