# sample_code_scratch

A small Python checkout app to test Code Dependency Impact Analyzer CLI from scratch.

## Suggested CLI flow

1. Parse only:

```
code-impact parse ./data/sample_code_scratch
```

2. Full pipeline with query:

```
code-impact analyze ./data/sample_code_scratch -q "What breaks if I change checkout_order?" --mode fast
```

3. Query existing graph:

```
code-impact query "What depends on record_event?" --mode slow
```
