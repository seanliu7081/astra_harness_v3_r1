# Astra harness v3 r1

This repository packages `foundation_vision_harness_V3 / astra_tools_r1`.
Preserve the frozen policy, prompts, protocol, execution, and scoring semantics.
Portability changes and their hashes are recorded in `provenance/`.
Keep credentials, virtual environments, model weights, and generated runs out of Git.
Use project-local installation paths; do not depend on a sibling checkout.
Offline tests, dependency checks, and installation checks make no model calls.
Live full-task episodes require the user's explicit request; `run --approved`
launches one episode with no automatic retries or API-key fallback.
