# Extraction validation

Checked on 2026-11-12 (Asia/Shanghai), using only the new repository and new
project-local virtual environments.

- Clean Python 3.12 controller and Python 3.10 simulator installations completed;
  both environments passed `pip check`.
- **59 offline tests passed**, including the r1 integration path, protocol,
  vision backends and geometry, task integrity, relocated paths containing
  spaces, and inspection without a simulator or credential store.
- A separate Git clone in a path containing spaces installed both controller and simulator
  from scratch. It passed all 59 tests, integrity checks, offline inspection,
  simulator imports, and both dependency checks with its own paths. GitHub Actions also passed on a clean hosted runner.
- The optional CUDA vision environment installed from scratch; SAM3/DA3 APIs
  and the exact builder symbols used by the harness imported successfully.
  No model was instantiated or checkpoint downloaded; see
  `provenance/vision_install_validation.json` and `docs/vision.md`.
- All nine V3 modules match the archived `astra_tools_r1` hashes. Six embedded
  layout files and six T04/T08 scene/hash files passed integrity checks.
- All 293 vendored LIBERO files match their recorded hashes. Panda kinematics
  loads its robot and gripper XML from the new simulator environment.
- Fresh simulator resets of both packaged obstacle scenes reproduced their
  exact r1 initial-observation hashes. These checks performed initialization
  and reset settling only, with zero policy actions and zero model requests.
- A Python library wheel built successfully and contains robot facts, HTML,
  and the embedded task layouts. Full episode launching uses the repository
  scripts and bundled simulator assets; the wheel alone is not the deployment.

Reset evidence is in `provenance/install_validation.json`; clone evidence is in
`provenance/clone_install_validation.json`; simulator versions
are in `validation/clean_simulator_install.json`. Source portability edits are
listed in `provenance/source_manifest.json`.

No live Astra task was launched and no credentials were copied. These checks
establish packaging and reset compatibility, not a new success-rate or timing
result. Login and inference still require the user's subscription and model
access. Large vision checkpoints remain separate downloads.
