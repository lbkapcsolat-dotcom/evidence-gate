# Evidence Gate

A tiny, dependency-free Python engine for classifying a claim from explicit evidence assessments.

It returns exactly one of three states:

- `SUPPORTED` — at least one evidence item supports the claim and none contradict it.
- `INSUFFICIENT` — there is not enough supporting or contradicting evidence.
- `CONFLICTING` — at least one evidence item contradicts the claim.

The rules are deliberately conservative, deterministic, and easy to audit.

## Quick start

Requires Python 3.10+ and no third-party packages.

```bash
python evidence_gate.py examples/example.json
```

Example output:

```json
{
  "claim": "The dataset contains 100 rows.",
  "contradicting_count": 0,
  "insufficient_count": 1,
  "status": "SUPPORTED",
  "supporting_count": 1
}
```

## Input format

```json
{
  "claim": "The dataset contains 100 rows.",
  "evidence": [
    {
      "source": "dataset-metadata.json",
      "assessment": "supports"
    }
  ]
}
```

Each `assessment` must be one of:

- `supports`
- `contradicts`
- `insufficient`

Unknown assessment values fail closed with an error instead of being silently promoted.

## Tests

```bash
python -m unittest -v
```

The initial test suite covers supported, conflicting, insufficient, empty-evidence, and invalid-input cases.

## Why this exists

Evidence Gate is a minimal building block for workflows where an AI or automation should not turn incomplete evidence into a stronger claim. The engine separates the evidence decision from any language model and keeps the decision rule inspectable.

## License

MIT
