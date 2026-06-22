# New-repo audit checklist

A structured first-pass audit of an unfamiliar repo. **Discipline: every
architectural claim cites a file path, and every conclusion carries a confidence
label `(Confidence: High | Medium | Low)`.** Stay within ~70% of the context
budget — summarize, don't dump whole files.

## 1. Orientation

- [ ] Purpose + domain (from README / package metadata) — cite the file.
- [ ] Languages, frameworks, runtimes, build system.
- [ ] How to run / test / lint / build.

## 2. Architecture (cite a path per claim)

- [ ] Entry point(s).
- [ ] **Primary service / business-logic file** (don't stop at routes/models).
- [ ] Data model / schemas; persistence.
- [ ] External integrations (APIs, queues, cloud).
- [ ] Utility modules (hashing, versioning, caching) — often skipped.

## 3. Quality & risk

- [ ] Test coverage shape; notable edge cases; last few migrations.
- [ ] Secret-leak scan (see `playbooks/security/secret-scanning-patterns.md`).
- [ ] Dead/commented-out code, TODO/FIXME density.
- [ ] CI gates and what they enforce.

## 4. Output

- [ ] A short report: findings with `file:path` citations and a
      `(Confidence: H/M/L)` per claim; list "alternatives considered / not
      verified" honestly rather than overstating.
