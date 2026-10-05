# GitHub ↔ Hugging Face Cross-Domain Evidence Bridge

This branch defines a **public-safe integration contract** only.

## Roles

- GitHub is the source / CI / control-plane surface.
- Hugging Face is intended as a private artifact / evidence / model mirror.
- Mirroring does not transfer authority.

## Integrity rule

A mirrored artifact is accepted only when the source commit, payload hash, manifest hash, repository identities, timestamp, and post-write remote readback all match.

## Current state

Hugging Face remote write is intentionally **HOLD** until repository write permission is explicitly available and a post-write readback succeeds.

## Non-claims

- no global bind
- no runtime admission
- no production readiness
- no deployment
- no automatic bidirectional synchronization
- no private authority identifiers published here
