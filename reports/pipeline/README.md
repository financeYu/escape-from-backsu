# Pipeline Reports

`reports/pipeline/` documents the Step 19 pipeline report boundary.

Generated run summaries and manifests belong under:

```text
reports/pipeline/generated/
```

Generated files in that directory are local runtime artifacts and are not
committed by default. A small fixture may be promoted only when a test or review
explicitly requires it and the fixture states that it is not canonical market
state.

Step 19 pipeline reports must stay compact:

- selected stages
- skipped or blocked stages
- input and output refs
- validation status
- boundary checks
- timestamp and git commit when available
- warnings and errors

They must not include secrets, large data dumps, market data caches, generated
chart images, trading recommendation language, or Step 20 completion claims.
