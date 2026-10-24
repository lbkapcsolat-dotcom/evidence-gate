# Real URL demos

## GitHub PR

```bash
python live_source_collector.py \
  "https://github.com/lbkapcsolat-dotcom/evidence-gate/pull/7" \
  --output-dir live_github_demo
```

Expected runtime artifacts:

```text
live_github_demo/result.json
live_github_demo/receipt.json
```

## Google Drive stored file

```bash
export GOOGLE_OAUTH_ACCESS_TOKEN="..."
python live_source_collector.py \
  "https://drive.google.com/file/d/1Y965Pm3M7Ug7m5Ksyd7-FenDJFn57Pde/view?usp=drivesdk" \
  --output-dir live_drive_demo
```

Expected runtime artifacts:

```text
live_drive_demo/result.json
live_drive_demo/receipt.json
```

The repository stores no OAuth token.
