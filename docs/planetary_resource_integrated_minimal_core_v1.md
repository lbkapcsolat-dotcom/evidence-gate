# EQUILIBRIUM Planetary Resource Systems Core V1
## Integrated Minimal Planetary Core V1

This gate composes the frozen core without introducing new provider work or new domain equations.

The fixture contains exactly three resource layers: ELECTRICITY, NATURAL_GAS, and FRESHWATER. It uses one frozen 60-second interval, one node per layer, one electricity storage, one natural-gas boundary import, and one typed gas-to-electricity cross-layer process.

The cross-layer process is executed through the frozen coefficient-uncertainty, coefficient-validity, and process-manifest-version path. Storage is executed through the frozen typed-self-loss and active-topology binding path. Layer balances are evaluated through the frozen end-to-end uncertainty path.

The fixture is synthetic and physically typed. It does not consume the three real-source canaries and therefore performs no real multi-source fusion.

Acceptance requires:
- all three nominal layer residuals equal zero;
- uncertainty remains non-exact in each layer balance;
- the storage next state is produced through the topology-bound storage successor;
- process version and validity guards remain active;
- evidence lineage from every fixture input appears in the integrated output lineage;
- exactly one deterministic integrated-state receipt is emitted;
- no frozen core file is patched.

The next work after this gate is deterministic replay of the integrated state, not another open-ended core-gap review.

CI execution is required on both Python 3.12 and 3.13 before PASS.
