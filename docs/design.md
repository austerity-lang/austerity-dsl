# Austerity — Design Document

*Version 0.1 — 2026*

---

## 1. Purpose and Scope

Austerity is a domain-specific language for expressing rule-based autonomous
decision logic. Its primary purpose is to allow a system to monitor a set of
state variables and respond to changes in that state by applying declarative
rules. It does so without requiring human intervention, without requiring
network access, and with minimal computational overhead.

The scope of version 0.1 is deliberately narrow:

- A defined state model (key-value pairs with typed values).
- A rule syntax with conditional evaluation (`WHEN`) and state mutation (`THEN`).
- A deterministic execution loop.
- A structured audit log of all state changes and rule firings.

Austerity does not, in this version, address real-time hardware control,
distributed coordination, machine learning inference or general-purpose
computation. These are explicitly out of scope — not because they are
unimportant, but because a focused version 0.1 that does a few things
correctly is more valuable than an ambitious version 0.1 that does many
things poorly.

---

## 2. Design Principles

### 2.1 Stability over constant maintenance

Every design decision should prioritise the ability of an Austerity system
to run with minimal intervention over extended periods. This means avoiding
dependencies on external services, minimising the surface area of the
runtime, and favouring explicit over implicit behaviour.

This is not a claim that the system will never change. Bug fixes, compliance
updates and deliberate improvements are expected and welcome. The goal is to
minimise the *frequency and urgency* of intervention — a system should be
able to run for months without someone needing to touch it, not because it
is frozen, but because it is stable.

### 2.2 Determinism over flexibility

Given the same initial state and the same rule set, an Austerity execution
must produce identical results every time. This is non-negotiable.
Determinism is what makes a system trustworthy and debuggable without live
access. A rule-based system that behaves differently on Tuesday than it did
on Monday is not a rule-based system — it is a source of uncertainty.

### 2.3 Sequential execution as a safety guarantee

Austerity executes strictly sequentially. There is no concurrency, no
parallelism, and no shared mutable state between execution contexts. Each
step completes fully before the next begins.

This is not a performance limitation — it is a named safety property. The
Therac-25 radiation therapy machine killed patients between 1985 and 1987
because concurrent software tasks accessed shared state without
synchronisation, allowing the machine to enter physically dangerous
configurations that were supposed to be impossible. Sequential execution
eliminates this entire class of failure. For safety-critical deployments,
the absence of race conditions is more valuable than the presence of
parallelism.

If Austerity grows to support concurrency or distributed execution in future
versions, that boundary is where this safety guarantee ends, and where new
safety mechanisms must be introduced to replace it.

### 2.4 Explicit resource usage

The language should make resource consumption visible. There are no hidden
allocations, no background threads, no lazy evaluation. Every operation has
a predictable cost. Systems running on constrained hardware cannot absorb
surprise.

### 2.5 Declarative logic first

Rules describe what should happen, not how to make it happen. The execution
engine is responsible for the *how*. This separation keeps rule files
readable by non-programmers and auditable by domain experts who are not
software engineers. A rule file should be something a municipal engineer,
a hospital administrator or a field technician can read and verify.

### 2.6 Human-readable state and decisions

At any point in execution, the full system state must be readable and
interpretable by a human without specialist tooling. Logs exist in many
systems — what distinguishes Austerity's audit log is its intended
audience. It is not designed for a developer with a log analysis platform.
It is designed to be opened in a plain text editor by the person responsible
for the system, with no software beyond the operating system required to
make sense of it.

### 2.7 Austerity never fails silently

Every error condition — parse error, type mismatch, undefined key, version
mismatch, indentation inconsistency — produces an explicit, human-readable
message. A simulation that cannot start safely does not start at all.

The 2003 northeast American and Canadian blackout affected 55 million people
because a power station alarm system failed without producing any output.
Operators were not notified of a developing fault. By the time the fault
became visible through other means, the cascade had begun and could not be
stopped. Silent failures are more dangerous than loud ones. Austerity is
designed to be loud.

Every error message produced by the parser or engine must:

- State what went wrong, in plain English.
- State where it went wrong — file name, line number, and column where
  available.
- State what was expected instead.
- Where possible, suggest a corrective action.

This is a requirement for implementors, not a recommendation. Error messages
that require software engineering expertise to interpret have already failed
the user who needs to act on them.

### 2.8 Version declarations are mandatory

Every rule file declares its target version as its first line. The engine
validates this declaration before processing any other content. A version
mismatch is a hard error that halts execution immediately.

Knight Capital lost $440 million in 45 minutes in 2012 because different
servers ran different versions of the same trading software simultaneously,
with no mechanism to detect the discrepancy. The version declaration in
Austerity is the direct response to this class of failure. It costs one
line per file and prevents an entire category of silent incompatibility.

### 2.9 No implicit type conversion

Austerity never performs implicit type coercion. A numeric value is never
silently converted to a string. A float is never silently narrowed to an
integer. A boolean is never silently interpreted as a number.

The Ariane 5 rocket was destroyed in 1996 partly because a 64-bit floating
point number was silently narrowed to a 16-bit integer without any warning
or error. The value overflowed. The inertial reference system crashed. The
rocket self-destructed 37 seconds after launch with a $500 million payload
aboard. Implicit type narrowing is not a convenience feature — it is a
fault waiting to be triggered.

Mixed-type comparisons in WHEN conditions and mixed-type assignments in THEN
blocks are parse errors in Austerity. They are caught before the simulation
begins.

### 2.10 Minimal dependencies

The MVP implementation targets Python 3 with no third-party libraries. The
goal is a runtime that can be installed and run on a machine with only a
standard Python interpreter — the kind of machine that has not been updated
since 2012. If it cannot run there, it has already excluded the people it
was designed to serve.

### 2.11 Connectivity is optional, not assumed

Austerity does not require a network connection to function. If one is
available, it may be used. If one is not, the system continues to operate
correctly. This means every feature must degrade gracefully in the absence
of connectivity — not that connectivity is forbidden or undesirable.

This matters because many real deployment environments — traffic controllers,
remote monitoring stations, institutional systems in underserved regions —
have intermittent or unreliable network access. Austerity must serve them
without modification.

---

## 3. State Model

The state in an Austerity system is a flat key-value store. Keys are
identifiers. Values are one of four types: integer, float, boolean or string.

State is initialised from a configuration file (JSON in the MVP) and
persists across execution steps in memory. All state mutations are performed
exclusively by rule execution. No external writes are permitted during a
simulation run.

Every key in the state definition has a fixed type determined by its initial
value. Types do not change during execution. The parser validates all rule
file references against the state definition at load time — a rule that
references a key not present in the state definition is a parse error.
*(See language reference section 1.6 on the undefined identifier policy.)*

Example state definition:

```json
{
  "intersection_id": "Junction_14",
  "north_queue":     12,
  "south_queue":     3,
  "east_queue":      8,
  "west_queue":      1,
  "phase":           "NORTH_SOUTH_GREEN",
  "cycle_time":      45,
  "cycle_timer":     45,
  "clearance":       false,
  "emergency":       false
}
```

The flat structure is a deliberate constraint. Nested state introduces
complexity in both evaluation and inspection. A flat store is easier to
log, easier to reason about, and easier to initialise from a simple file.
This constraint may be revisited in future versions, but any relaxation of
it will require an explicit justification against these trade-offs.

---

## 4. Rule Syntax

A rule consists of three parts: a name, a condition (`WHEN`) and one or
more state mutations (`THEN`). Rules are evaluated in declaration order.
Each rule whose condition is satisfied fires and mutates state. Subsequent
rules are evaluated against the updated state within the same step.

```austerity
AUSTERITY 0.1

RULE <name>
WHEN <condition>
THEN
    <key> = <value>
    <key> = <expression>
END
```

Conditions support comparison operators (`=`, `>`, `<`, `>=`, `<=`, `!=`),
logical connectives (`AND`, `OR`, `NOT`), and parentheses for grouping.
Standard boolean operator precedence applies: `NOT` binds most tightly,
then `AND`, then `OR`. Explicit parentheses are always recommended over
reliance on precedence — a rule file should be readable by someone who
does not know the precedence table.

Values on the right-hand side of assignments may be literals or arithmetic
expressions involving existing state keys.

Example rules for the traffic control demo:

```austerity
AUSTERITY 0.1

RULE heavy_north_traffic
WHEN north_queue > 10 AND phase = "NORTH_SOUTH_GREEN"
THEN
    cycle_timer = cycle_timer + 10
END

RULE emergency_override
WHEN emergency = true
THEN
    phase       = "ALL_RED"
    clearance   = false
    cycle_timer = 0
END

RULE emergency_recovery
WHEN emergency = false AND phase = "ALL_RED" AND clearance = false
THEN
    phase       = "NORTH_SOUTH_GREEN"
    cycle_timer = cycle_time
END
```

Rule names use underscores and lowercase by convention. They are
identifiers, not strings — they appear in the audit log and should be
descriptive enough to be meaningful without additional context.

---

## 5. Execution Model

Austerity executes in discrete steps. Each step follows this sequence:

1. **Environment update** — external inputs or simulated sensor values are
   applied to state. The `cycle_timer` is decremented by one, clamped at
   zero. Randomness, if any, is applied here only — never inside rule
   evaluation.
2. **Rule evaluation** — rules are evaluated in declaration order against
   current state.
3. **State mutation** — all matching rules update state values.
4. **Audit log write** — the full state snapshot and list of fired rules
   are written to the log.

This cycle repeats until a configured number of steps is reached or the
process is terminated. The step granularity (simulated time per step) is
defined in the configuration file.

**Rule conflict resolution:** if two rules write to the same key in the
same step, the rule declared *last* takes precedence. This is explicit and
documented behaviour, not a silent default. Rule authors who need a
specific outcome should order their rules accordingly. Future versions may
introduce explicit priority declarations as an alternative.

---

## 6. Randomness Policy

Simulated environments require variability. Austerity supports seeded
randomness for environment updates only — never within rule evaluation.
This ensures that:

- The same seed always produces the same simulation run.
- Different seeds produce different scenarios for testing.
- Rule behaviour is always deterministic for a given state, regardless
  of how that state was reached.

The seed is declared in the configuration file and written to the audit
log at the start of every run. A simulation run is only reproducible if
the seed is known — logging it is therefore not optional.

---

## 7. Audit and Logging

Every execution step produces a log entry containing: the step number,
the timestamp, the full state snapshot and the list of rules that fired.
Logs are written in structured plain text to a file defined in the
configuration.

The design goal is readability without tooling. Many systems produce logs
— Austerity's logs are specifically designed for the person responsible
for the system, not for the developer who built it. A system administrator
with a text editor and no programming knowledge should be able to open the
log file and understand what the system decided at each step, and which
rule drove that decision.

The audit log is a first-class output of the system. It is the record of
what the system decided and why — and for systems running with minimal
supervision, that record is essential. Disabling the audit log is not
supported. A system that cannot be inspected after the fact cannot be
trusted.

Example log entry:

```text
--- STEP 12 | 2026-01-15 09:04:33 ---
STATE:
  intersection_id  = Junction_14
  north_queue      = 11
  south_queue      = 2
  east_queue       = 5
  west_queue       = 1
  phase            = NORTH_SOUTH_GREEN
  cycle_time       = 45
  cycle_timer      = 60
  clearance        = false
  emergency        = false
RULES FIRED:
  heavy_north_traffic
---
```

---

## 8. MVP Demo: Traffic Control Simulation

The first public demonstration of Austerity simulates an autonomous traffic
intersection controller operating without network connectivity on minimal
hardware.

The simulation models a four-way intersection with per-direction vehicle
queue counts. Rules govern phase switching, cycle time adjustment, clearance
intervals between phase transitions, and emergency vehicle response. The
system runs for a configurable number of steps, producing a complete audit
log of every decision made.

This demo was chosen because:

- Traffic control is universally understood — it requires no domain
  expertise to evaluate.
- It is a real legacy hardware problem: municipal traffic systems worldwide
  run on decades-old embedded controllers.
- It demonstrates offline autonomy, determinism, type safety, and
  human-readable logging in a single concrete scenario.
- It is politically and commercially neutral.

---

## 9. Related Work

| System | Approach | Strength | Austerity difference |
|---|---|---|---|
| CLIPS | Rule-based, NASA-origin | Proven, deterministic | Modern tooling, clearer philosophy, explicit resource focus |
| Drools | Enterprise rule engine | Powerful, expressive | Far too heavyweight; Java-dependent |
| Prolog | Logic programming | Elegant declarative model | Alien syntax; minimal modern adoption |
| Datalog | Declarative queries | Renaissance in databases | Not designed for autonomous control loops |
| Ada | Systems language | Aerospace-grade reliability | General-purpose; steep learning curve |

The closest relative is CLIPS. Austerity differs not in mechanism but in
philosophy and focus: where CLIPS is a general-purpose rule engine,
Austerity is deliberately scoped, deliberately minimal in its dependencies,
and designed from the outset for constrained and intermittently-connected
environments with a formal safety foundation informed by documented
real-world failures.

---

## 10. Non-Goals

The following are explicitly outside the scope of Austerity version 0.1:

- Real-time hardware control or interrupt handling.
- Robotics or physical actuator interfaces.
- Machine learning inference or model integration.
- Distributed or networked execution.
- A new operating system or kernel.
- General-purpose computation (loops, functions, recursion).
- Concurrent or parallel execution.

These boundaries are not permanent. They are deliberate constraints that
allow version 0.1 to be completed, published and validated before scope
expands. A small thing done well is a more honest foundation than a large
thing done partially.

Note that concurrent and parallel execution is listed explicitly here —
not because it is undesirable in principle, but because introducing it
requires new safety mechanisms to replace the sequential execution safety
guarantee described in section 2.3. It is not a feature to be added
casually.

---

## 11. Repository Structure

The repository is live at
[github.com/austerity-lang/austerity-dsl](https://github.com/austerity-lang/austerity-dsl).

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

## 12. Deferred — Continuous Risk Management Framework (v0.2)

The safety principles documented in this version were arrived at through
a retrospective review of historical software failures. Examining what
went wrong in other systems and encoding the lessons as design constraints
in Austerity. This approach is valuable but inherently backward-looking.

Version 0.2 should introduce a forward-looking complement: a continuous
risk management framework built into the language and its tooling. The
intent is to treat risk assessment not as a one-time design activity but
as an ongoing property of the system — one that can be evaluated
automatically as rule files evolve.

Concretely, this might include:

- A formal risk profile for each rule — documenting what state keys it
  touches, what conditions can trigger it, and what the consequences of
  an unexpected firing would be.
- Static analysis tooling that detects rule conflicts, unreachable rules,
  and state keys that are written but never read, or read but never written.
- A simulation stress-testing mode that systematically varies the random
  seed and initial state to explore edge cases automatically, reporting
  any steps where rule behaviour is surprising or conflicting.
- A versioned changelog requirement — when a rule file is modified, the
  change must be accompanied by a risk annotation explaining what changed
  and why the change is safe.

This framework would position Austerity not just as a language with a safe
foundation, but as a language with active, ongoing safety assurance — a
meaningful differentiator in safety-critical deployment contexts. The
historical incidents reviewed during the development of version 0.1 are
the foundation; the v0.2 risk framework is the structure built on top of it.

*This section is a deferred design intent, not a specification. It will be
developed into a formal proposal at the start of the v0.2 design cycle.*

---

*Austerity — Version 0.1 — [github.com/austerity-lang/austerity-dsl](https://github.com/austerity-lang/austerity-dsl)*
