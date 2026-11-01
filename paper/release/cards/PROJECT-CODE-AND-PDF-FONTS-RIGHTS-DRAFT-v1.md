# Project code and rendered-font rights card

Status: DRAFT; packaging guidance, not legal certification. Official terms accessed and local metadata checked 2026-11-01. No font files were copied into the package.

## Project code

The repository root `LICENSE` contains Apache License 2.0, January 2004 (11,358 bytes; SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`). This is the declared project code licence, not clearance of every repository asset or a determination of contributor ownership. Author identities, contributions, funding and institutional facts remain owner-supplied; this card invents none.

For allowlisted project code, preserve the licence, applicable notices and modification notices; retain any relevant third-party NOTICE obligations. Apache-2.0 does not supply a general trademark licence or warranty. See the [authoritative Apache text](https://www.apache.org/licenses/LICENSE-2.0). Dependency packages, provider data, models, articles and fonts remain separately governed. This review did not perform a complete dependency licence inventory; runtime binaries and installed packages are external unless separately reviewed and allowlisted.

## Manuscript font evidence

The retained manuscript PDF SHA-256 is `4f19060e0bb67fdd932780de9765a415f42c518cde74895302aa45b942ead588`; its `paper/PDF-BUILD.json` SHA-256 is `f920afd5ea4259ca8f8f4da4255dc43a0d317978cffabf7434dc8ac4ba77dcb5`. Read-only PDF inspection found embedded TrueType subsets `ArialMT` and `Arial-BoldMT`. Its Base-14 resources Helvetica, Helvetica-Bold and Times-Roman have no embedded font programs. The manifest records five loaded fonts with policy `subset_when_used`; only regular/bold Arial are embedded. These are different statements.

The exact installed files used for those two subsets were checked without copying them:

| Local build dependency | SHA-256 matching PDF-BUILD | OS/2 `fsType` |
| --- | --- | ---: |
| Arial regular, `arial.ttf` | `b3658eadae55e682b5f69eb64c439c1ecc8f196c0bb8d4756d145d13bc86476a` | 8 |
| Arial bold, `arialbd.ttf` | `e8f4e3baf6cc35fed6fcce3a540e8b39e8f6cda1d22a28f2ec8f526fef7a43f5` | 8 |

Microsoft's [font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq), last updated 2024-11-19, distinguishes document embedding from generally restricted Windows font-file redistribution and self-hosting. Its [OpenType OS/2 specification](https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fstype) defines value 8 as editable embedding; the checked values have neither the no-subsetting nor bitmap-only bit set. This supports the observed document-subset use. It is not an audit of the owner's Windows entitlement, every application requirement or every font distribution scenario.

## Proposed disposition

Admit the reviewed rendered PDF as a document with embedded subsets, conditional on the owner's lawful installed-font/application use; do not relabel the font programs Apache-2.0. Exclude `.ttf`, `.otf`, `.woff`, font caches and extracted PDF font programs. An SVG naming a font does not bundle that font. Keep the build's font hashes/version dependence visible.

Recipients may view the PDF using its document embedding. Rebuilding with the same font bytes requires independently lawful access to those local dependencies. A separately qualified open-font variant can improve portability, but is a new rendering variant and must not claim the frozen PDF's byte hash. No font substitution or PDF/manuscript modification was made in this review.
