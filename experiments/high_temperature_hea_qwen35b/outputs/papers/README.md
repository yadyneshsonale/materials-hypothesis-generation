# Per-paper inputs and outputs

This directory contains one folder for each of the 50 research papers:

```text
PMCxxxxxxx/
├── metadata.json
├── input/
│   ├── README.md
│   ├── article.xml
│   └── article.pdf
└── output/
    ├── roles.json
    ├── questions.json
    └── rejected_items.json
```

## Important PDF notice

The PDFs are included **only for visual inspection by human readers**. They are not parsed,
extracted, scored, or used as evidence by the data pipeline.

The JATS XML is the machine-readable article input. Exact evidence grounding is validated against
the structure-preserving text generated from that XML.

Each `metadata.json` records the article citation metadata, license, PMC version, checksum-qualified
PMC OA PDF source, and the visual-only use restriction.
