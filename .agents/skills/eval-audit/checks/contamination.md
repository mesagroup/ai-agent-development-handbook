---
id: eval/contamination
domain: eval
locality: local
handbook:
  - evaluation/build-a-dataset-you-can-trust
  - evaluation/name-the-anti-patterns-out-loud
---

# Contamination / leakage

Test items that leaked into prompts/few-shots, ground truth derived from the model under test, or an eval the prompt was tuned against being reported as held-out.

## Severity

**Critical** - dataset contamination / leakage that invalidates reported numbers.

## Tooling fallback

Needs reading - no tool in this domain's evidence pass reaches this: compare the eval dataset and any few-shot/prompt examples for overlapping items, and check whether ground truth was produced independently of the model under test.

## Fix

**De-contaminate:** hold out the eval set from prompt-tuning/few-shots; source ground truth independently of the model under test; label leaked items and re-baseline.

## Review lens

**Contamination** - the eval set is genuinely held out from tuning; ground truth is independent of the model under test.
