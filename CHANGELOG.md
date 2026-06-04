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

Planned for v0.2:

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
- Fix for queue extension rules firing every step on heavy traffic

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
