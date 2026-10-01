# Buyer-safe architecture diagram

No internal implementation details, credentials or private repository structure are shown.

```mermaid
flowchart LR
  A[AI workflow action] --> B[NVIDIA OpenShell runtime boundary]
  B --> C[Provider-native OCSF event]
  C --> D[ESS evidence normalizer]
  D --> E[Assurance receipt]
  E --> F[PASS/HOLD matrix]
  E --> G[Replay and mutation checks]
  E --> H[Durable registry]

  X[Cross-event correlation] -. remains HOLD .-> E
```

## Buyer interpretation
- OpenShell is the runtime source for provider-native evidence.
- ESS does not replace OpenShell and does not claim equivalence.
- ESS consumes evidence, builds receipts, and fails closed when a bound evidence field is changed.
- Cross-event causality is not claimed unless the provider supplies native correlation evidence.
