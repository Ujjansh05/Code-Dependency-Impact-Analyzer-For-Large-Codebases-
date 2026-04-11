# sample_code_scratch

A small Python checkout app to test GraphXploit CLI from scratch.

## Suggested CLI flow

1. Parse only:

```
graphxploit parse ./data/sample_code_scratch
```

2. Full pipeline with query:

```
graphxploit analyze ./data/sample_code_scratch -q "What breaks if I change checkout_order?" --mode fast
```

3. Query existing graph:

```
graphxploit query "What depends on record_event?" --mode slow
```
