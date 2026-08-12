---
id: data-protection/stored-artifact-pii
domain: data-protection
locality: global
handbook:
  - data-protection/personal-data-does-not-belong-in-the-trail
tooling:
  any: [pdscan]
---

# Personal data in stored artifacts

Whether personal data has reached the artifacts that outlive the call - stored traces and run records, eval datasets, and the fixtures somebody extracted from a real case because it reproduced a bug. The call-site half of this claim is `security/sensitive-data`'s: it reads logging and exception-handling call sites and outbound URL construction, so a payload reaching a log statement or an identifier carried in a URL is its row and is not restated here, and this record takes only the stored copy that is still there after the call has returned.

## Severity

The bands that assert personal data is present rest on a value the pass actually read in the artifact, or on the generation script that says where the data came from, and never on a field name, a fixture's filename or a directory named `real-data`. That is `SKILL.md`'s line drawn where this record meets it: inference may establish *that* a personal-data surface exists, which is what selects the band, and may not establish *what an artifact contains*, which is what the finding has to cite. Where an artifact plainly exists and its content is out of reach - a dataset the repository ignores rather than commits, a binary or an encrypted archive - **the band asserting a payload drops one level and the row reports the artifact as unexamined with its contents undocumented**, because an artifact nobody could read is a true finding about the reach of the pass, while the same row called Critical asserts a leak on the strength of a path. The band about the schema is a **mechanism** band: a field that captures a payload is a fact about what the emitter writes rather than a claim about what any store holds today, so it stands whatever established the surface, and it cites the field rather than a value.

**Critical** - personal data read in a stored artifact the repository commits: a trace, a run record, a captured log, a fixture or an eval dataset. What makes this the top band is the committing rather than the leak: the artifact is in the history and on every clone anybody has taken since, so it has already been copied to machines nobody is tracking, and it is the one band whose fix is not a change to the working tree.

**Critical** - an eval dataset or a fixture built from a raw copy of production, whether or not the data itself is committed. Read the generation script rather than the data for this one, because that is where "built from real inputs" is visible even when the output is ignored: a dump of the production store, a copy of a customer's uploads, a replay of recorded traffic, with no redaction between it and the fixture. It is Critical because a dataset is the copy that gets shared widest - it goes to whoever is improving the model, into a notebook, sometimes to a vendor - and because it was produced by a practice doing its job, which is why it is the last place anybody looks for personal data.

**Important** - a trace or run-record schema that captures a payload field, where nothing is committed but the store the emitter writes to will hold them. This is the mechanism band above: cite the field in the schema or the emitter, and report the store as the place the payloads accumulate rather than asserting what is in it, which is a claim the clone cannot make. It is Important rather than Critical because the exposure is bounded by who can read that store, and it is not Minor because nothing expires a field that keeps being captured.

**Minor** - an artifact whose join key is a directly identifying value, such as an email address, a phone number or an account name, where an opaque internal reference would join back just as well. This is already the shape Part 10 asks for rather than a leak, which is why it is the bottom band: the payload is not there. The row is that the key still identifies a person to everyone who can read the artifact, and a reference costs nothing to use instead.

## Tooling fallback

**Detect before prescribing, and note that the tool here is one the target would never run itself.** Prefer `pdscan` where the project inventory records the audit environment as already carrying it. It is a standalone Go binary in no language registry, so no one-shot runner can supply it - the same kind, and the same consequence, as `osv-scanner` in `deps/vulnerabilities`. Do not attempt `uvx pdscan` or `npx pdscan`: each fails the way a missing package fails, which reads as a tool that could not be obtained rather than as a name that was never obtainable through a runner at all.

**Its absence is not `no-evidence`.** `audit-core` defines that status as no tooling **or fallback** being able to run, and the reading pass below runs whether or not the binary is present, so where `pdscan` is missing this row carries the domain's own status with the axes the scanner would have covered named as unscanned. Reporting `no-evidence (tool-unavailable)` instead would record an unanswered question on a check the clone can answer, which is the same false negative as reading an empty scan as a clean result.

**Scope the invocation to the artifact directories rather than to the clone root** - `pdscan file://<dir>` over the log, trace, fixture and eval-data directories. It line-scans files rather than selecting them by extension, excluding only a few formats by type, and descends into zip and gzip archives, so pointed at the whole tree it reports git objects and vendored binary assets as matches. A run whose output is mostly noise is one whose real findings get triaged away with it.

**Two caveats decide what its output means, and either one alone turns a tool that ran into a false clean.** Its rules are regex-based and US-shaped - a US social-security number's shape, US street suffixes, a list of common US surnames - with nothing for a passport number, an IBAN or a non-US national identifier, so **empty output discharges this check only on the axes it scans** and everything else falls to the reading pass below. Name those axes in the row rather than reporting a scan as clean. And its flag that prints the matched values propagates the very leak this check exists to find, out of the artifact into a findings report and from there into a ticket, so a finding reports the location and the rule that matched, and quotes a value only where a false positive has to be demonstrated and nothing weaker will demonstrate it.

**The reading pass, which runs whether or not the tool did.** Read the committed fixture and test-data directories, which are where a real case lands once somebody has reproduced a bug with it. Read the eval datasets **and their generation scripts**, because the scripts are where "built from real inputs" is visible even when the data is not committed. Read the trace and run-record schema or emitter, for which fields it captures. And read the log and trace configuration, for what is shipped to a backend, since an artifact that never lands in the repository still lands somewhere and this check is about the stored copy rather than about the commit.

**What no pass can see, and how it is reported.** Whether a fixture's source was synthetic, consented, or a real case somebody put through redaction is provenance, and provenance is a fact about how a file was made rather than something in the file. The artifact is readable and its origin is in no repository, so that is `warn (unverifiable-from-here)` under `SKILL.md`'s rule for which status carries the annotation, naming whoever created the fixture as who would settle it. Keep it apart from the top band: personal data actually read in a committed artifact is settled by the clone and is a plain `violation` with no annotation, because annotating it would report as open a question the repository has already answered.

**Reject the secret-scanner substitution explicitly.** `gitleaks`, `trufflehog` and `detect-secrets` each scope themselves to credentials in their own documentation, and a credential is not a data subject, so `security/secrets-in-code`'s tooling list is not transferable here and a clean secret scan is no evidence about this check. Where one of them has run, report it as what it is - a credential scan - and never as the scan this row rests on.

## Fix

Replace the payload with the identifier you can join back to it. That is what Part 10 asks for and it is also what keeps the trail diagnosable: a record naming the run, the shape and size of its inputs, the tools called, the timings and the cost is the whole of what observability wants, and none of it needs the document quoted. Rebuild fixtures from synthetic or consented data, or from real data put through the same redaction the production path uses, which has the second benefit that the fixture then exercises the shape production actually produces. Where the schema is the finding, the fix belongs in the emitter rather than in the store, because a field that is never captured needs nothing expired later.

**Where a committed artifact already holds personal data, removing it from the working tree does not remove it.** It stays in the history and on every clone taken since, so the fix is a history rewrite, or a decision to treat what was exposed as exposed and act on that - the same shape as a leaked credential, where deleting the line without rotating leaves it live in the history. Either one is decided with whoever owns the risk rather than by the audit, because a history rewrite is disruptive to everyone holding a clone and the exposure question is not the audit's to answer. So the remediation names the decision and who makes it, and never lands a quiet `git rm` that clears the row from the working tree while the data stays exactly where it was.

## Review lens

**Boundary with the code lens** - a finding here is about a stored artifact. Personal data reaching a logging or exception call site, and an identifier carried in a URL, are `security/sensitive-data`'s rows and are not restated in this one, because a claim counted in both domains is one gap reported twice with its fix split across two owners.

**Provenance honesty** - a fixture is not reported as synthetic because it looks synthetic, nor as real because its filename suggests it. Where provenance is recorded nowhere in the repository, the row says so and names who would know, rather than resolving it in whichever direction the rest of the row was already heading.

**Scan-axis honesty** - a row resting on an empty scanner run names the axes that run covered, because the scanner's rules are regionally shaped and a clean result over them is not a clean result over personal data. And no row quotes a matched value it did not have to quote to demonstrate a false positive, since the report travels further than the artifact it was taken from.
