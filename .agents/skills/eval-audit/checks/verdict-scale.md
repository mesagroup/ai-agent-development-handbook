---
id: eval/verdict-scale
domain: eval
locality: local
handbook:
  - evaluation/ask-for-a-described-category-not-a-bare-number
routes:
  - lang: any
    kind: procedure
    note: >-
      Needs reading - no tool in this domain's evidence pass reaches this: read the judge prompt or scorer template for the output it requests, then read the code that consumes the verdict for how it thresholds or aggregates it. The prompt alone is half the check, because a well-described scale can still be undone by a consumer that averages it.
---

# Judge verdict scale (shape of the model's own judgment)

Where the suite asks a model for a judgment of its own - a confidence, a quality score, a severity, a relevance rating - does it ask for a point on a small closed scale whose every point carries a described trigger, or for a free number? A judge prompt that requests a float, a percentage, or a 0-100 score is the finding; so is a scale whose labels are named but never defined, since an undescribed label is only a coarser number. Check what consumes the verdict too: a cutoff placed between two rubric anchors asks graders for a distinction the rubric never defined, and a mean taken over ordinal labels treats spacing the scale never claimed.

## Severity

**Important** - a free numeric self-report that something downstream thresholds or averages, so the pipeline acts on precision the scale cannot carry.

**Minor** - a described scale whose labels are sound but whose boundary is stated only as a number, or an ordinal scale reported with an unspecified correlation where a rank-aware statistic belongs.

## Fix

**Replace the free number with a described scale:** name the points, and give each one a sentence saying when it applies, drawn from cases the suite has actually seen. Keep the scale small, and re-state any cutoff as a named boundary ("act on Moderate and above") so the threshold is a decision with a reason rather than a value someone nudged. Where a number really is wanted, source it from something other than the model's self-report: a deterministic scorer, a count, a measured cost or latency.

## Review lens

**Anchor quality** - does each label carry a trigger a second reader could apply to the same case and land in the same bucket, or is it a bare word that leaves the boundary to taste?

**Consumer honesty** - does anything downstream threshold, average, or rank the verdict in a way the scale's granularity does not support?
