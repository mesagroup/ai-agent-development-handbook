# Handing over the handbook page

The rendered handbook is one self-contained HTML file built from [`engineering/`](engineering/README.md) by `scripts/render_handbook_artifact.py`. It travels with the first audit report so that every handbook citation in that report resolves to a text the recipient holds. This note is the copy that stays in the repository; it names no recipient, and a copy that does goes with the artefact.

## What it accompanies

The prose report of the sweep against `<python-target>`, the agent repository this handbook was extracted from. The report cites the handbook in two shapes, and both are covered below. Later reports for `<polyglot-monorepo-target>` and `<single-package-target>` cite the same page unless the handbook has changed in between, in which case the page is re-rendered from the commit the report was produced against and the check below is re-run.

## How a recipient opens it

Open the file in a browser. It is a single page with a sidebar listing the parts, a light and dark theme, and no dependency on the network: the diagrams are inline, the styles are inline, and nothing is fetched. It also renders inside a hosted artifact frame, where following an in-page link is intercepted and scrolls rather than navigating.

## How a citation in the report opens in the page

Every heading in the page carries an id of the form `<part>-<slug>`, where `<part>` is the handbook file's stem and `<slug>` is the heading's GitHub-style slug. A citation resolves by one of two rules, depending on which shape the report used:

- **A URL** of the form `.../docs/engineering/<part>.md#<fragment>` opens as `#<part>-<fragment>` in the page. `lifecycle.md#fan-work-out-to-parallel-agents-and-merge-it-honestly` is `#lifecycle-fan-work-out-to-parallel-agents-and-merge-it-honestly`. A URL with no fragment opens the part itself.
- **A matrix row id** of the form `<part>/<slug>` or `<part>/<slug>-<letter>` opens as `#<part>-<slug>`, the letter dropped: the letter names one of several rows a heading was split into, the heading is one, and the matrix's own validator holds every row's slug against its heading, so the slug in the id is the heading's. `lifecycle/fan-work-out-to-parallel-agents-and-merge-it-honestly-b` is `#lifecycle-fan-work-out-to-parallel-agents-and-merge-it-honestly`.

To follow one, append the anchor to the page's address in the browser, or use the sidebar to reach the part and search the page for the heading. The recipient does not need this repository: the URL's organisation and repository name are the address the citation was written at and resolve only for members of the owning organisation, which is why the page exists.

## What was checked before handover

`scripts/check_handbook_citations.py --page <the rendered file>` holds every citation the skills carry and every matrix row the emitter can list against the ids the page carries, and prints, for each of the two shapes, how many it found and how many resolved, then the page's id count. A handover records that output beside the page's commit. The check is re-run whenever the handbook or the skills change, because a heading reworded after a report was issued orphans that report's citation silently.

## Where the artefact lives

`<artefact-location>`: a release asset of this repository or a directory on the engagement's channel, decided by the maintainer and recorded here with a placeholder where it names the recipients' side. Until it is recorded, the page is rendered on demand into `test-reports/handbook.html`, which is not committed.

## Re-rendering

`uv run python scripts/render_handbook_artifact.py` needs the `d2` CLI on the path and writes the page to `test-reports/handbook.html`; its last line reports the section count, the diagram count and `residual .md hrefs: 0`. Then run the check above with `--page` pointing at the output.
