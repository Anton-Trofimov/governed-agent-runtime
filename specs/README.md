# Specification Structure

## Core specifications

`core/` contains the evolving normative specification of the governed runtime:

- product and scope;
- agent charter;
- runtime architecture;
- state and evidence models;
- context assembly;
- tool contracts;
- runtime policy;
- action preconditions;
- confirmation and state transitions.

## Experiment specifications

`experiments/` contains experiment-specific plans, acceptance cases and
evaluation methods.

Core specifications may evolve through controlled changes. Completed experiment
definitions remain versioned through Git and milestone tags.

## SDD change sequence

Specification change
→ acceptance-case change
→ schema or test change
→ implementation change
→ experiment result
→ decision or ADR
