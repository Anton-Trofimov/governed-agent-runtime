# Synthetic Runtime Knowledge

## Purpose

This directory contains controlled synthetic domain knowledge for the
payment-api incident-response environment used by the experiments.

Files under `knowledge/` may become available to the governed runtime only
through explicitly declared source mappings, adapters, tool contracts and
context-assembly rules.

Presence in this directory does not automatically make a file model-visible.

## Current contents

The current knowledge set includes:

- `service-catalog.yaml` — synthetic service identities and metadata;
- `service-topology.yaml` — synthetic dependency relationships;
- `ownership.yaml` — synthetic service ownership and escalation information;
- `capacity-profiles.yaml` — synthetic capacity constraints and profiles;
- `runbooks/` — operational guidance that may support diagnosis and planning.

These files describe the experimental environment. They do not describe a real
production system.

## Runtime access boundary

Runtime loaders must use explicitly declared paths and contracts.

They must not:

- scan the repository broadly for context;
- load every file under `knowledge/` automatically;
- treat development documentation as evidence;
- use reports, coding-agent instructions or project handoff files as runtime
  knowledge;
- expose hidden evaluation data to the model or runtime path being evaluated.

A knowledge file becomes usable only when the experiment defines:

1. why the source is allowed;
2. which tool or adapter can access it;
3. how the source is normalized;
4. which fields become evidence;
5. whether the resulting context is model-visible, runtime-only or audit-only.

## Separation from scenario observations

`knowledge/` contains relatively stable synthetic domain knowledge.

`fixtures/scenarios/` contains scenario-specific raw observations and user
requests, such as:

- metrics;
- deployment events;
- configuration snapshots;
- dependency status;
- incident-specific source responses.

Knowledge must not contain hidden expected answers or scenario acceptance
labels.

Hidden ground truth and evaluator-only material belong under `evals/hidden/`.

## Guidance is not authorization

Runbooks, ownership data and capacity profiles may inform:

- diagnostic hypotheses;
- evidence requests;
- remediation planning;
- escalation paths;
- technical precondition checks.

They do not authorize operational execution.

The runtime remains responsible for policy gates, permissions, confirmation,
transition validation and tool execution control.

## Files that do not belong here

Do not place the following under `knowledge/`:

- coding-agent instructions;
- development status or handoff notes;
- Codex review reports;
- implementation plans;
- normative runtime specifications;
- test expectations or hidden labels;
- public project documentation;
- production credentials or real operational secrets.

Those materials belong in their dedicated repository areas:

- `AGENTS.md`;
- `project-meta/`;
- `reports/`;
- `specs/`;
- `tests/`;
- `docs/`.

## Change discipline

Changes to synthetic knowledge should preserve scenario reproducibility.

When a knowledge change affects an experiment:

1. update the relevant experiment or source contract;
2. update affected fixtures or tests;
3. document whether the change alters expected evidence;
4. avoid silently changing completed experiment results.

Git history and experiment reports retain the historical state used by earlier
runs.
