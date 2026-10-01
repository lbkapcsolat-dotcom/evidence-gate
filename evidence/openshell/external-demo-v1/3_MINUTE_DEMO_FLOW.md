# ESS x NVIDIA OpenShell External Assurance Demo Package V1

Target: UNIQA / NiQA founding pilot.

Pinned close seal: e4d8cb581966247aa1c376eac1b58476cb6392b0
OpenShell pin: v0.1.2 (6648bd0c290efbc41ba131ee9831ee45cd431f94)

## 3-minute demo flow

### 0:00–0:25 | Why this exists
We do not claim that AI is safe because a model says so. The demo shows a bounded assurance layer over a real OpenShell runtime event: one allowed network action becomes a reproducible evidence object with a native event ID, policy revision, policy hash and PASS/HOLD result.

### 0:25–0:55 | Runtime evidence source
Show the single provider-native OCSF event captured from OpenShell v0.1.2. Highlight: metadata.uid, container.uid, caller process, destination, firewall rule, action and policy hash.

### 0:55–1:30 | ESS assurance receipt
Show the ESS receipt generated from that event. Explain that the receipt is deterministic: the same event replayed twice gives the same canonical claim hash.

### 1:30–2:00 | Fail-closed falsification
Mutate one bound field, destination domain, and show PASS becomes HOLD. This is the core buyer value: claims do not survive evidence tampering.

### 2:00–2:35 | Stream and persistence
Show that live stream events are converted to one receipt per unique native UID, duplicates collapse, process restart preserves registry equality, and cross-run artifact rehydration preserves byte equality.

### 2:35–3:00 | Claim ceiling
State the boundary explicitly: this is not NVIDIA equivalence, not a superiority claim, not production security proof, and not compliance certification. Cross-event correlation remains HOLD.

## Buyer close
The pilot asks for one AI workflow, not a system redesign. We will produce a PASS/HOLD evidence matrix and a bounded receipt set for the selected workflow.
