# Changelog

All notable changes to Austerity DSL are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The spirit of this changelog reflects the second founding pillar of Austerity:
**known risk over unknown risk**. Every entry documents not only what changed,
but what was deliberately deferred and why. Risks that cannot be resolved in the
current version are named here and carried forward — not silently omitted.

---

## [Unreleased]

Planned for v0.2 — language and runtime:

- Static analysis for rule ordering warnings (G1)
- Reachability analysis for dead rules (G3)
- Namespacing for rule name collisions across files (G4)
- Parser warning for float equality comparisons (G6)
- Linting tool for intra-block read-after-write (G7)
- Conflict detection for inter-rule shared-key writes (G8)
- Guard expression syntax for division-by-zero prevention (G9)
- Exponent threshold warning for large integer exponentiation (G10)
- Multiline strings
- Block comments
- Relaxed CONST blocks allowing expressions (G2)
- Complexity linting for WHEN conditions (G5)
- Formal continuous risk management framework (design.md section 12)
- Rule aliasing and named rule groups (inter-rule references)
- Real sensor data input interface to replace seeded simulation
- Log redundancy and watchdog process for production deployments

Planned for Cycle 2 — research and publication:

- Whitepaper: Austerity DSL — a risk-informed design methodology for
  safety-critical domain-specific languages. Submission target: ArXiv cs.PL.
- Literature review: 2003 Northeast Blackout Task Force report; Leveson (2011);
  Fowler (2010); Mernik et al. (2005); Therac-25 forensics; Lee (2006).
- Case study: mapping Task Force findings to Austerity design principles —
  which findings v0.1 addresses, which are deferred to v0.2 or later.
- v0.2 design goals to be re-examined after whitepaper findings are consolidated.

---

## [0.1.1] — 2026-06-05

Correctness fixes and language extension to the MVP.
All changes are backward-compatible. No syntax breaking changes.
The Junction 14 simulation produces verified output across 150 steps
with seed 42, including a full emergency cycle and two queue extension events.

### Added — Language

- `DEFINE` block for string literal aliases.
  Aliases are expanded by the parser at parse time before any rule is
  evaluated. The engine and audit log always see the full expanded values.
  Aliases are a writing convenience only — they have no runtime presence.
  Syntax: `DEFINE / NAME = value / END`, placed after `AUSTERITY 0.1`
  and before the first `RULE`. One `DEFINE` block per file.
  Conventional style: alias names in UPPERCASE to distinguish them
  visually from state keys (snake_case) and rule names (snake_case).

### Changed — Parser (`parser.py`)

- Added `_parse_define_block()`: extracts and validates the optional
  `DEFINE` block from the tagged line list. Removes DEFINE lines from
  the tagged list before `_group_into_blocks` runs, so the block
  grouper requires no changes. Errors caught: DEFINE after first RULE,
  duplicate DEFINE blocks, empty DEFINE block, duplicate alias names,
  missing alias value, missing END.
- Added `_apply_substitutions()`: replaces alias names with their value
  strings in all tagged lines after DEFINE extraction. Uses whole-word
  regex replacement sorted longest-first to prevent partial matches
  (e.g. `NS` must not match inside `NSG`).
- Updated `parse()` call sequence: `_parse_define_block()` and
  `_apply_substitutions()` inserted between `_check_version()` and
  `_group_into_blocks()`. All downstream functions are unchanged.

### Changed — Engine (`engine.py`)

- `_apply_assignments()`: added `cycle_timer` clamp at zero after all
  assignments are applied. Previously the clamp existed only in
  `apply_environment_update()`. A rule subtracting from `cycle_timer`
  (e.g. `reduce_cycle_on_low_traffic`) could push the timer negative,
  which appeared in the audit log as `timer: -4`. The timer now clamps
  to zero consistently after both environment updates and rule mutations.

### Changed — Demo: Junction 14 (`intersection.rules`)

- Added `DEFINE` block with five aliases:
  `NSG`, `NSY`, `EWG`, `EWY`, `AR` — expanding to the full phase name
  strings. All eleven rules updated to use aliases in WHEN and THEN clauses.
- `extend_north_south_on_heavy_load`: added ceiling condition
  `AND cycle_timer < 20`. Without this, the rule fired every step the
  north queue exceeded threshold, growing the timer without bound.
  The ceiling limits each extension event to a single firing per ~10-step
  window, preventing green phase starvation of the opposing direction.
- `extend_east_west_on_heavy_load`: same ceiling fix as above.
- `reduce_cycle_on_low_traffic`: added phase guard
  `(phase = NSG OR phase = EWG)`. Previously this rule fired during
  yellow and clearance phases, shortening safety-critical fixed-duration
  intervals. Yellow and clearance durations are now protected.
- Added inline comments to `emergency_recovery` explaining that the
  `clearance = false` condition is what distinguishes post-emergency
  recovery from normal clearance intervals, and that firing on every
  step of ALL_RED-with-no-clearance is the intended behaviour.

### Changed — Config (`config.json`)

- `steps` increased from 50 to 150. The previous value was insufficient
  to observe a full double phase cycle or an emergency event.
- `step_delay_ms` reduced from 500 to 200. Faster display for demos
  while remaining readable.

### Fixed

- Negative `cycle_timer` values now correctly clamp to zero after rule
  mutations, not only after environment updates. Previously `timer: -4`
  could appear in the audit log at step 9 of seed-42 run.
- Queue extension rules no longer fire unboundedly on sustained heavy
  traffic. The ceiling condition `AND cycle_timer < 20` resolves the
  known issue documented in v0.1.0.

### Resolved Known Issues

- **Queue extension rules fire every step on heavy traffic.** Resolved
  by ceiling condition in both extension rules. Removed from known issues.

### Known Issues (carried forward)

- **Expression evaluation uses Python `eval()` with restricted context.**
  Division by zero in THEN expressions remains possible at runtime (G9).
  A full expression parser is the v0.2 path.

- **Rule ordering is semantically significant with no static warning (G1).**
  `clearance_to_east_west_green` and `clearance_to_north_south_green`
  share identical WHEN conditions. Last-declared wins. Correct and
  documented, but a static analysis warning is planned for v0.2.

- **Seed prompt does not accept a new seed value directly.**
  Entering a number at the `[Y/S/N]` prompt instead of `S` falls through
  to the default seed. Minor UX issue in `runner.py`. Deferred to v0.2.

- **Audit log has no redundancy.**
  Log writes to a single file with no replication or watchdog. Acceptable
  for MVP demo; a production deployment would require log redundancy.
  Deferred — this is an infrastructure concern, not a language concern.

---

## [0.1.0] — 2026-06-04

First working release of the Austerity DSL MVP.
The runtime executes `.rules` files against a JSON state definition,
produces ASCII terminal output, and writes a full audit log.
Verified against the Junction 14 traffic intersection demo.

### Added — Language

- Rule syntax: `RULE / WHEN / THEN / END` block structure
- State model: flat key-value store with three types — numeric, boolean, string
- WHEN clause operators: `=` `!=` `>` `<` `>=` `<=` `AND` `OR` `NOT` and parentheses
- THEN clause operators: `+` `-` `*` `/` `//` `%` `**` on numerics; `+` for string concatenation
- Single-line comments with `#`; inline comments supported
- Mandatory version declaration: `AUSTERITY 0.1` as first non-comment line (P5)
- Boolean literals: `true` and `false` (lowercase only)
- Conflict resolution: last-declared rule wins when two rules write the same key
- Identifiers: letters, digits, underscores; must start with a letter; snake_case convention
- Keywords uppercase; identifiers and boolean literals lowercase

### Added — Runtime (Python MVP)

- `parser.py` — two-pass parser; tokenises and validates `.rules` files against state
- `engine.py` — evaluates WHEN conditions and THEN expressions; applies state mutations
- `logger.py` — writes structured plain-text audit log; human-readable without tooling
- `runner.py` — entry point; step loop; ASCII terminal output with queue bar charts; seed prompt; run-again prompt

### Added — Safety Principles (P1–P9)

- P1 — No implicit type conversion (Ariane 5, 1996): mixed-type assignments are runtime errors
- P2 — Sequential execution is a safety guarantee (Therac-25, 1985–1987): no concurrency, no parallelism
- P3 — Units are part of the data (Mars Climate Orbiter, 1999): unit annotation syntax reserved for future version
- P4 — Never fails silently (2003 Northeast blackout): every error names file, line, expected value, and suggested fix
- P5 — Version mismatches are loud errors (Knight Capital, 2012): `AUSTERITY 0.1` declaration mandatory; mismatch halts before loading rules
- P6 — Floating point error accumulates (Patriot missile, 1991): documented warning; recalibration recommended for long runs
- P7 — Rounding behaviour is specified (Euro conversion, 1999): exact rounding semantics documented in language reference
- P8 — Undefined references caught before execution (null reference): all identifiers validated against state at parse time
- P9 — Reserved words never silently change meaning: reserved words retain reserved status permanently across versions

### Added — Demo: Junction 14 Traffic Intersection

- `examples/traffic/intersection.rules` — 11 rules in three sections:
  - Section 1: Normal phase rotation (6 rules) — full NORTH_SOUTH_GREEN → YELLOW → ALL_RED → EAST_WEST_GREEN → YELLOW → ALL_RED cycle
  - Section 2: Queue pressure adjustments (3 rules) — extends or shortens active green phase based on traffic load
  - Section 3: Emergency response (2 rules) — forces ALL_RED on emergency; recovers to NORTH_SOUTH_GREEN on clearance
- `examples/traffic/state.json` — 10 state keys: queue counts (N/S/E/W), phase, cycle_time, cycle_timer, clearance, emergency, intersection_id
- `examples/traffic/config.json` — simulation parameters: seed, steps, delays, thresholds, durations, and inline documentation notes

### Added — Documentation

- `README.md` — one-page entry point; answers what it is and whether to keep reading
- `docs/manifesto.md` — problem statement and founding philosophy
- `docs/design.md` — design principles, state model, execution model, related work
- `docs/language.md` — formal language reference; EBNF grammar; safety principles; reserved keywords and function names

### Added — Repository

- GitHub organisation: `austerity-lang`
- Repository: `github.com/austerity-lang/austerity-dsl`
- MIT licence
- Folder structure: `/docs`, `/src`, `/examples/traffic`

### Design Decisions

- Python is the interpreter runtime for the MVP — not the language itself. Python reads and executes `.rules` files. The language and the runtime are deliberately separate. A C rewrite of the runtime is a future option; the language syntax remains unchanged.
- Zero third-party dependencies — standard Python 3 library only. The runtime installs and runs on any machine with a standard Python interpreter.
- Offline-first — no network assumed or required at any point.
- Audit log is a first-class output — it cannot be disabled.
- ASCII terminal output — no special terminal capabilities required; runs on any system from VT100 to modern SSH.
- Seeded randomness applies to environment simulation only — never inside rule evaluation. Same seed always produces same run.

### Known Issues

- **Queue extension rules fire every step on heavy traffic (G7/G8 interaction).**
  `extend_north_south_on_heavy_load` and `extend_east_west_on_heavy_load` fire on
  every step that the relevant queue exceeds the threshold, adding 10 steps to
  `cycle_timer` each time. If the queue never drains below the threshold, the green
  phase never ends. A ceiling condition (e.g. `AND cycle_timer < 60`) is the
  intended fix. Deferred to v0.2 rules revision.

- **Expression evaluation uses Python `eval()` with restricted context.**
  This is a pragmatic MVP choice. A full expression parser is the v0.2 path.
  Division by zero in THEN expressions is possible at runtime (G9).

- **Rule ordering is semantically significant with no static warning (G1).**
  `clearance_to_east_west_green` and `clearance_to_north_south_green` share
  identical WHEN conditions. The last-declared rule wins. This is correct and
  documented, but a static analysis warning would make it explicit. Planned for v0.2.

### Deferred to Future Versions

- `related_work.md` as standalone file — content insufficient for v0.1
- Multiline strings
- Block comments
- Unicode identifiers
- Digit separators in numeric literals (`1_000_000`)
- Collection types: `VECTOR`, `MATRIX`, `SERIES`
- Unit annotations: `[m/s]`
- Complex number literals: `2.5j`
- Bitwise operators: `&` `|` `^` `~` `<<` `>>`
- `IMPORT` / module system
- Graphical simulation output
- Continuous risk management framework (design.md section 12)
- All ten grammar-level risks G1–G10

---

## [0.0.1] — 2026-06-02

Project foundation. No working code yet.

### Added

- Project concept and name established: **Austerity**
- Problem statement defined: software designed for abundance excludes the majority of the world
- Core philosophy: constraint as a design requirement, not a limitation
- Design inspiration: BIC pen, Citroën 2CV — tools that endure by doing less, better
- Two founding pillars named: restraint by design; known risk over unknown risk
- GitHub organisation `austerity-lang` created
- Repository `austerity-dsl` created — public, MIT licence
- `Austerity_DSL.docx` — full manifesto and design document (Word format)

---

*Austerity DSL — github.com/austerity-lang/austerity-dsl*
