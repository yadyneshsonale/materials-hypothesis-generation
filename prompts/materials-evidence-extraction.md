# Linked Materials Evidence Extraction

The executable prompt is `_EXTRACT_SYSTEM` in `materials_extract.py`.

The extractor emits condition-specific evidence units rather than independent argumentative
labels. Every accepted unit links one material state to at least one intervention or structural
state and one mechanism or property outcome. It retains:

- material identity, composition, form, and initial state;
- composition or processing intervention and parameters;
- resulting phases, microstructure, and defects;
- proposed or observed mechanism;
- quantitative or qualitative property outcome and measurement method;
- temperature, time, environment, load, strain rate, and pressure;
- comparison baseline;
- limitations, confidence, section, and verbatim provenance.

Records are split when the material, processing history, temperature, environment, or loading
condition changes. Missing fields remain empty and must not be inferred.
