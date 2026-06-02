# Austerity DSL

**A declarative, rule-based domain-specific language for resource-constrained autonomous systems.**

Version 0.1 — 02 June 2026 
[github.com/austerity-lang/austerity-dsl](https://github.com/austerity-lang/austerity-dsl)

---

## What It Is

Austerity is a minimal DSL for writing autonomous decision logic that must run reliably
on constrained hardware, with minimal connectivity, and with minimal supervision. 
It is designed for the environments that modern software stacks have left behind: 
legacy institutional systems, edge deployments without reliable infrastructure, 
and any context where predictability and longevity matter more than raw capability.

It is built on two principles.

**Restraint by design.** Austerity does more with less — by choice, not by accident. 
It has no dependencies, assumes no network, and is designed to run on hardware that 
has not been updated in a decade. Constraint is not a limitation to be overcome. 
It is a design requirement to be respected.

**Known risk over unknown risk.** Every design decision in Austerity is documented with its
rationale and its known limitations. Risks that cannot be resolved in the current version 
are explicitly named and assigned to a future version. Organisations deploying Austerity
receive a documented risk profile, not just a system whose failure modes are discovered
 after the fact.

---

## What It Looks Like

Austerity rule files are plain text. The syntax is designed to be readable by engineers, 
system operators and domain experts who are not software developers.

```austerity
AUSTERITY 0.1

RULE emergency_override
WHEN emergency = true
THEN
    phase       = "ALL_RED"
    cycle_timer = 0
END

RULE heavy_north_traffic
WHEN north_queue > 10 AND phase = "NORTH_SOUTH_GREEN"
THEN
    cycle_timer = cycle_timer + 10
END

RULE emergency_recovery
WHEN emergency = false AND phase = "ALL_RED" AND clearance = false
THEN
    phase       = "NORTH_SOUTH_GREEN"
    cycle_timer = cycle_time
END
```

Rules are evaluated in declaration order. State is a flat key-value store. The same input 
always produces the same output. Every step is written to a human-readable audit log.

---

## What It Is Not

Austerity is not a general-purpose programming language. It does not compete with Python, 
Rust or C. It has no loops, no functions, no recursion and no network stack. These are not oversights
 — they are boundaries, placed deliberately so that the language can do one thing correctly 
 and be trusted to keep doing it.

It is not an AI tool. It is not cloud-native. It is not designed for the data centre, 
though it will run there. It is designed for the places infrastructure does not reliably reach.

---

## Documentation

| Document | Contents |
|---|---|
| [Manifesto](docs/manifesto.md) | The philosophy, the problem, and the two founding principles |
| [Design Document](docs/design.md) | Architecture, execution model, safety principles, and design decisions |
| [Language Reference](docs/language.md) | Complete EBNF grammar, type system, operator behaviour, and risk register |

---

## Current Status

Version 0.1 is in active development. The language specification is complete. 
The MVP implementation, a Python interpreter for `.rules` files with a traffic intersection simulation,
is in progress.

The repository currently contains:

- Complete language specification and grammar in `/docs`
- Traffic intersection example rules, state, and configuration in `/examples/traffic`
- Python interpreter source files in `/src` (in progress)

This project is an exploration, documented carefully and built in public. Contributions, questions
 and critical feedback are welcome.

---

## Repository Structure

```text
austerity-dsl/
  README.md
  LICENSE
  /docs
    manifesto.md
    design.md
    language.md
  /examples
    traffic/
      intersection.rules
      state.json
      config.json
  /src
    parser.py
    engine.py
    runner.py
    logger.py
```

---

*MIT License — [github.com/austerity-lang/austerity-dsl](https://github.com/austerity-lang/austerity-dsl)*
