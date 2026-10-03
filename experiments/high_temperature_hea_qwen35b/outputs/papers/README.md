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
    ├── reader_question_rejections.json
    └── rejected_items.json
```

## Important PDF notice

The PDFs are included **only for visual inspection by human readers**. They are not used to
generate, score, or ground pipeline evidence. The review interface may read the PDF text layer
after extraction solely to position visual highlight rectangles.

The JATS XML is the machine-readable article input. Exact evidence grounding is validated against
the structure-preserving text generated from that XML.

`questions.json` contains the high-recall reader questions. `reader_question_rejections.json`
retains invalid model candidates and exact duplicates removed from overlapping chunks for audit.
The older `rejected_items.json` records the original role/decision-question extraction audit.

Each `metadata.json` records the article citation metadata, license, PMC version, checksum-qualified
PMC OA PDF source, and the visual-only use restriction.
