# Scenario Fixtures

Scenario fixtures contain synthetic source data used by deterministic tools and
future model experiments.

Structure:

- `scenario.yaml` defines the scenario and source mapping;
- `user-request.json` contains the initial user request;
- `source/` contains deterministic raw source responses;
- hidden ground truth is stored separately under `evals/hidden/`.

Source files do not contain expected answers or acceptance labels.

Raw source data becomes model-visible only after the corresponding allowed tool
call and runtime normalization.
