# Austerity — Language Reference

*Version 0.1 — 02 June 2026*

---

## Preamble

This document is the formal specification of the Austerity DSL. It defines
the complete syntax, grammar, type system and built-in mathematical
capabilities of the language.

It is written for two audiences:

- **Rule authors** — engineers, researchers, system operators and domain
  experts who write `.rules` files. The plain English explanations and
  examples are written for you.
- **Implementors** — developers building parsers, interpreters or tools
  for Austerity. The formal EBNF grammar is written for you.

Where the two descriptions conflict, the EBNF grammar takes precedence.
The prose is an aid to understanding, not a substitute for precision.

Version 0.1 defines a deliberately narrow language. Features marked
**[reserved]** are not implemented in this version but are syntactically
reserved for future use. Using a reserved feature in a v0.1 rule file
will produce a parse error with an explanatory message.

### A note on scope and roadmap

Austerity 0.1 operates exclusively on scalar state values — individual
numbers, booleans and strings. The primary planned extension for future
versions is the introduction of collection types: vectors, matrices and
time series. Every scientific and engineering domain that Austerity is
designed to serve — physics, chemistry, biology, geology, astronomy,
statistics — ultimately requires the ability to operate on collections of
values, not just individual ones. The reserved keywords and operators
throughout this document reflect that intent. They are not speculative
additions; they are markers of a deliberate roadmap, placed now so that
future versions of the language can grow without breaking existing rule
files.

### Design safety principles

The design of Austerity has been informed by a review of real software
failures that caused loss of life, loss of spacecraft and large-scale
infrastructure collapse. The following principles are not aspirational —
they are direct responses to documented failure modes in other systems.
Each principle is noted where it applies in the sections below.

**P1 — No implicit type conversion.**
The Ariane 5 rocket was destroyed in 1996 partly because a 64-bit float
was silently narrowed to a 16-bit integer, overflowing without warning.
Austerity never performs implicit numeric type narrowing. Widening is
permitted; narrowing requires an explicit operation.

**P2 — Sequential execution is a safety guarantee.**
The Therac-25 radiation therapy machine killed patients between 1985 and
1987 because a race condition in concurrent code allowed the machine to
enter a physically dangerous state. Austerity executes strictly
sequentially. There is no concurrency, no parallelism and no shared
mutable state between execution contexts. This is not a performance
limitation — it is a named safety property.

**P3 — Units are part of the data.**
The Mars Climate Orbiter was lost in 1999 because two engineering teams
used different unit systems with no mechanism to detect the mismatch. The
unit annotation syntax reserved in this document (`[m/s]`, `[K]`, `[Pa]`)
is designed to make this class of error impossible in future versions of
Austerity. A value will carry its unit as part of its type and operations
on incompatible units will be rejected at parse time.

**P4 — Austerity never fails silently.**
The 2003 northeast American and Canadian blackout affected 55 million
people because an alarm system failed without producing any output.
Operators were not notified. Every error condition in Austerity — parse
error, type mismatch, undefined key, version mismatch — produces an
explicit, human-readable message. A simulation that cannot start safely
does not start at all.

**P5 — Version mismatches are loud errors.**
Knight Capital lost $440 million in 45 minutes in 2012 because different
servers ran different versions of the same software with no mechanism to
detect the discrepancy. Every Austerity rule file declares its version as
its first line. A version mismatch between a rule file and the running
engine produces a clear error and halts execution.

**P6 — Floating point error accumulates.**
A US Patriot missile battery failed to intercept an incoming missile in
1991 because accumulated floating point rounding error caused a 0.34
second timing drift after 100 hours of continuous operation. Rule authors
running Austerity simulations over large numbers of steps should be aware
that floating point arithmetic accumulates rounding error. This is
documented in the numeric precision section below.

**P7 — Rounding behaviour is specified, not assumed.**
Euro currency conversion in 1999 produced systematic discrepancies because
different systems used different rounding rules with no coordination.
Austerity specifies the exact rounding behaviour of every rounding
function. These specifications are guaranteed to be consistent across all
platforms and versions.

**P8 — Undefined references are caught before execution.**
Austerity validates all identifiers in a rule file against the state
definition before the simulation begins. A rule that references a state
key that does not exist is a parse-time error, not a runtime condition.
The simulation will not start until all references are resolved.

**P9 — No reserved word may silently change meaning.**
A word reserved in one version of Austerity retains its reserved status
in all subsequent versions. Reserved words are never silently repurposed.
If a reserved word is promoted to active use, rule files that used it as
an identifier — which would have produced a parse error — remain invalid.
There is no scenario in which a valid rule file silently changes behaviour
due to a keyword promotion.

---

## 1. Lexical Rules

Lexical rules define the basic tokens of the language — the smallest
meaningful units that the parser works with. Before a rule file can be
parsed, it is first broken into a stream of tokens according to these
rules.

### 1.1 Source Files

Austerity source files use the `.rules` extension. Files must be encoded
in UTF-8. Line endings may be Unix style (`LF`), Windows style (`CR LF`),
or classic Mac style (`CR`) — the parser normalises all three to a single
newline before processing.

**Character set for identifiers:** identifiers in version 0.1 are
restricted to ASCII letters, digits and underscores. Unicode identifiers
— such as identifiers containing characters from non-Latin scripts — are
not supported in version 0.1. This restriction is documented rather than
apologised for: it simplifies the lexer, eliminates the risk of invisible
character confusion between look-alike Unicode code points and can be
revisited in a future version once the core language is stable. String
literal values may contain any valid UTF-8 character.

### 1.2 Version Declaration

Every Austerity rule file must begin with a version declaration as its
first non-comment, non-blank line. The version declaration specifies
which version of the Austerity language the file was written for.

```ebnf
version_declaration ::= "AUSTERITY" major "." minor
major               ::= digit { digit }
minor               ::= digit { digit }
```

Example:

```austerity
AUSTERITY 0.1
```

The engine checks the declared version before processing any other content
in the file. If the declared version is incompatible with the running
engine, the engine produces a clear error message and halts. It does not
attempt to parse or execute the file.

This is a direct response to the class of failure demonstrated by the
Knight Capital incident of 2012, in which different versions of software
running simultaneously produced catastrophic unintended behaviour with no
mechanism to detect the discrepancy. *(See design principle P5.)*

A rule file that omits the version declaration is a parse error. The
error message will read: *missing version declaration — every Austerity
rule file must begin with AUSTERITY followed by a version number.*

### 1.3 Whitespace

Whitespace — spaces and tab characters — is not significant between tokens
except in two contexts:

1. **Inside string literals**, where whitespace is part of the value.
2. **Inside THEN blocks**, where indentation is required (see section 1.11).

Outside these two contexts, any amount of whitespace between tokens is
legal and ignored. The following two expressions are equivalent:

```austerity
WHEN north_queue>10 AND phase="NORTH_SOUTH_GREEN"
WHEN north_queue > 10 AND phase = "NORTH_SOUTH_GREEN"
```

The second form is strongly recommended for readability.

**Tab and space mixing:** a file that uses both tab characters and space
characters for indentation within THEN blocks is a parse error. The error
message will read: *inconsistent indentation — this file mixes tab and
space characters. Use one consistently throughout the file.* This rule
applies within a single file only. Different files in the same project may
use different indentation characters.

### 1.4 Comments

A comment begins with the `#` character and extends to the end of the
current line. Comments are permitted:

- On a line by themselves.
- At the end of any line, after a complete token or statement.

Comments are not permitted inside string literals — a `#` character inside
a quoted string is treated as part of the string value.

```austerity
# This is a full-line comment.

RULE emergency_override          # This is an inline comment.
WHEN emergency = true
THEN
    phase       = "ALL_RED"      # Stops all traffic immediately.
    cycle_timer = 0              # No phase rotation while active.
END
```

Block comments spanning multiple lines are not supported in version 0.1.
Each line of a multi-line comment must begin with its own `#` character,
as shown in the rule file headers in the examples directory.

### 1.5 Keywords

The following words are reserved as language keywords. They may not be
used as identifiers or state key names. Keywords are case-sensitive and
must be written in uppercase exactly as shown.

**Active keywords — implemented in version 0.1:**

```
AUSTERITY
RULE    WHEN    THEN    END
AND     OR      NOT
CONST
```

**Reserved keywords — not implemented in version 0.1.**
Using any of these in a rule file will produce a parse error with a
message indicating the feature is reserved for a future version.

*Control and structure:*
```
IMPORT    FROM      AS        MODULE
FUNCTION  RETURN    MATCH     CASE
LIBRARY
```

*Future type system:*
```
TYPE      UNIT      COMPLEX
VECTOR    MATRIX    SERIES    HISTORY
```

*Reserved aggregate function names:*

The following identifiers are reserved as built-in function names for
future versions. They may not be used as state key names or rule names
in any version of Austerity.

```
sqrt    log     log2    log10   exp
sin     cos     tan     asin    acos    atan    atan2
floor   ceil    round   abs     sign
min     max     sum     mean    median  stdev   variance
```

**On reserved function name collision:**
A scientist writing a rule file might naturally want a state key called
`mean` — the mean temperature, the mean population. This is currently
forbidden because `mean` is reserved as a future aggregate function name.
The intended resolution when aggregate functions are introduced in a
future version is namespacing: `mean` as a bare identifier will be
permitted as a state key; `mean(...)` as a function call will invoke the
built-in. This resolution is documented here so that the reservation does
not create the impression of a permanent prohibition on common words.
*(See design principle P9.)*

### 1.6 Identifiers

An identifier is a name given to a rule, a state key, or a constant.

**Formal definition:**

```ebnf
identifier ::= letter { letter | digit | "_" }
letter     ::= "a".."z" | "A".."Z"
digit      ::= "0".."9"
```

In plain English:

- An identifier must begin with a letter — uppercase or lowercase.
- After the first character, it may contain letters, digits and
  underscores in any combination.
- An identifier may not begin with a digit or an underscore.
- An identifier may not be a keyword or a reserved function name.

**Valid identifiers:**

```
north_queue
sensor_1
Junction14
cycle_time
CO2_level
temperature_K
H2O_pressure
```

Note that chemical formula style identifiers such as `CO2_level` and
`H2O_pressure` are valid and intentionally supported. The underscore
separates the formula component from a descriptive suffix, keeping the
identifier both recognisable and unambiguous to a domain expert.

**Invalid identifiers:**

```
1_sensor        # begins with a digit
_queue          # begins with an underscore
north-queue     # hyphens are not permitted
RULE            # reserved keyword
sqrt            # reserved function name
mean            # reserved function name
```

**Convention:** state keys and rule names use lowercase letters and
underscores only (`snake_case`). This is a convention, not a language
requirement, but it is strongly recommended. It keeps identifiers
visually distinct from keywords, which are always uppercase.

**Undefined identifier policy:** every identifier that appears in a rule
file must exist as a key in the state definition file, or as a declared
constant in a `CONST` block, before the simulation begins. The parser
validates all references at load time. A rule that references an undefined
identifier is a parse error. The simulation will not start. This policy
eliminates the null reference problem at its root — there is no mechanism
by which a rule can attempt to read a value that does not exist.
*(See design principle P8.)*

### 1.7 Integer Literals

An integer literal is a whole number, positive or negative.

```ebnf
integer_literal ::= [ "-" ] digit { digit }
```

Examples: `0`, `1`, `42`, `1000`, `-5`, `-273`

Austerity integers are arbitrary precision. They do not have a fixed
maximum value and will never silently overflow. This is a deliberate
safety property — fixed-size integer overflow has caused real system
failures including the Ariane 5 rocket explosion of 1996, in which an
unchecked integer overflow contributed to the destruction of a $500
million payload. *(See design principle P1.)*

Underscores as digit separators are not supported in version 0.1.
`1_000_000` is not valid; write `1000000`. This may be added in a
future version.

### 1.8 Float Literals

A float literal is a number with a decimal point and/or a scientific
notation exponent.

```ebnf
float_literal    ::= [ "-" ] decimal_part [ exponent_part ]
decimal_part     ::= digit { digit } "." { digit }
                   | "." digit { digit }
exponent_part    ::= ( "e" | "E" ) [ "+" | "-" ] digit { digit }
```

Examples: `3.14`, `-2.718`, `.5`, `1.5e10`, `3.2e-4`, `6.022E23`

All floating point values are stored and computed as 64-bit IEEE 754
double precision numbers. This provides approximately 15 to 17 significant
decimal digits of precision.

**Floating point accumulation warning:** floating point arithmetic
accumulates rounding error over repeated operations. This effect is
negligible over short simulations but can become significant over
thousands of steps. The Patriot missile failure of 1991 resulted from
a 0.34 second timing error caused by accumulated floating point drift
after 100 hours of continuous operation — a drift that was undetectable
at any single step but fatal in aggregate. Rule authors running long
simulations should be aware of this property and consider periodic
recalibration of computed values against ground truth inputs where
precision is critical. *(See design principle P6.)*

### 1.9 String Literals

A string literal is a sequence of characters enclosed in matching quote
characters.

```ebnf
string_literal  ::= '"' { string_char_dq } '"'
                  | "'" { string_char_sq } "'"
string_char_dq  ::= any character except '"' and newline
string_char_sq  ::= any character except "'" and newline
```

Both single and double quotes are supported. The opening and closing
quote must be the same character. This allows one style of quote to
appear unescaped inside a string delimited by the other:

```austerity
message = "He asked: 'how are you doing?'"
label   = 'Junction "Alpha" — North Approach'
```

Strings may not span multiple lines in version 0.1. A string that is
not closed before the end of the line is a parse error.

**Escape sequences** supported inside string literals:

| Sequence | Meaning              |
|----------|----------------------|
| `\\`     | Literal backslash    |
| `\n`     | Newline character    |
| `\t`     | Tab character        |
| `\'`     | Literal single quote |
| `\"`     | Literal double quote |

### 1.10 Boolean Literals

Boolean literals represent logical truth values.

```ebnf
boolean_literal ::= "true" | "false"
```

Boolean literals are always lowercase. `TRUE`, `False` and `True` are
not valid boolean literals — they would be parsed as identifiers and
would produce a type error if used in a boolean context.

This is a deliberate design decision. Keywords are uppercase. Values are
lowercase. The distinction is consistent and visually unambiguous.

### 1.11 Indentation

Indentation — the leading whitespace at the start of a line — is
significant in exactly one context: **the body of a THEN block**.

Every assignment line inside a THEN block must be indented by at least
one space or tab relative to the `THEN` keyword. The parser does not
require a specific number of spaces or a specific indentation character,
but every assignment line must be indented consistently within the same
block. Mixing tabs and spaces within a file is a parse error.
*(See section 1.3 on tab and space mixing.)*

```austerity
RULE emergency_override
WHEN emergency = true
THEN
    phase       = "ALL_RED"    # indented — valid
    cycle_timer = 0            # indented — valid
END
```

```austerity
RULE emergency_override
WHEN emergency = true
THEN
phase = "ALL_RED"              # not indented — parse error
END
```

Recommendation: use four spaces for indentation. This is consistent with
Python and the majority of modern language style guides.

### 1.12 Type System Overview

Austerity 0.1 supports three scalar value types:

| Type    | Examples                        | Notes                          |
|---------|---------------------------------|--------------------------------|
| Integer | `0`, `42`, `-5`                 | Arbitrary precision, no overflow |
| Float   | `3.14`, `6.022E23`, `-2.718`   | 64-bit IEEE 754 double precision |
| Boolean | `true`, `false`                 | Lowercase only                 |
| String  | `"hello"`, `'world'`           | UTF-8, single line in v0.1    |

**Type safety rules:**

- A state key has a fixed type determined by its initial value in the
  state definition file. The type of a state key does not change during
  execution.
- Comparing a value of one type to a value of a different type in a WHEN
  condition is a parse error. There is no implicit coercion.
- Assigning a value of a different type to a state key in a THEN block
  is a parse error.
- Integer values assigned to float keys are widened automatically — this
  is safe and permitted. Float values assigned to integer keys require
  explicit truncation — this is not supported in v0.1 and is a parse
  error. *(See design principle P1.)*
- String concatenation using `+` is permitted between two string values.
  Adding a string to a number, or a number to a string, is a parse error.
  There is no implicit conversion of numbers to strings or strings to
  numbers.

These rules are strict by design. Silent type coercion has caused
real-world bugs in many languages — notably JavaScript, where `1 + "2"`
produces `"12"` rather than `3`. Austerity treats any mixed-type
operation as an error that must be resolved by the rule author before
the simulation runs. *(See design principle P1.)*

### 1.13 Operators

The following operator tokens are recognised by the lexer.

**Comparison operators** (used in WHEN conditions):

```
=    !=    >    <    >=    <=
```

**Arithmetic operators** (used in THEN expressions):

```
+    -    *    /    //    %    **
```

**Logical operators** (used in WHEN conditions, written as keywords):

```
AND    OR    NOT
```

**Grouping:**

```
(    )
```

**Reserved — bitwise operators** [reserved]:

The following operator tokens are reserved for future versions to support
low-level systems programming, hardware interfacing and bit manipulation.
They are not valid in version 0.1 and will produce a parse error if used
outside a string literal.

```
&    |    ^    ~    <<    >>
```

Note: `^` is reserved for bitwise XOR. Exponentiation uses `**` to avoid
any ambiguity with this future operator.

**Reserved — unit annotations** [reserved]:

```
[    ]
```

The square bracket tokens are reserved for a planned unit annotation
system that will allow numeric values to carry physical units:

```austerity
velocity    = 340.0 [m/s]      # reserved syntax — not valid in v0.1
temperature = 293.15 [K]       # reserved syntax — not valid in v0.1
```

This reservation is a direct response to the Mars Climate Orbiter failure
of 1999, in which the absence of any mechanism to carry unit information
alongside numeric values led to the loss of a $327 million spacecraft.
When implemented, unit annotations will allow the engine to reject
operations on incompatible units at parse time. *(See design principle P3.)*

Using square brackets outside of a string literal in version 0.1 will
produce a parse error with the message: *unit annotations are reserved
for a future version of Austerity — remove the square brackets or
upgrade to a version that supports them.*

**Reserved — complex number literals** [reserved]:

The imaginary unit suffix `j` is reserved for future complex number
support, consistent with Python and electrical engineering convention:

```austerity
impedance = 3.0 + 2.5j         # reserved syntax — not valid in v0.1
```

---

## 2. Grammar

This section defines the complete formal grammar of Austerity 0.1 using
Extended Backus-Naur Form (EBNF). It is organised top-down, from the
largest structure (a complete rule file) to the smallest (a literal value).
Every production rule is followed by a plain English explanation, examples
of valid and invalid usage and where applicable, a note on the risk
rationale behind the design choice.

**EBNF notation used in this section:**

| Notation       | Meaning                                      |
|----------------|----------------------------------------------|
| `::=`          | is defined as                                |
| `" "`          | literal terminal token                       |
| `< >`          | non-terminal — defined elsewhere             |
| `{ }`          | zero or more repetitions                     |
| `[ ]`          | optional — zero or one occurrence            |
| `( \| )`       | alternatives — one of these must match       |
| `"a".."z"`     | character range                              |

Where a production rule carries a known risk that version 0.1 does not
fully resolve, it is marked **[risk: under review]** and a plain English
explanation of the risk and the planned mitigation is provided.

---

### 2.1 File Structure

A complete Austerity rule file consists of a version declaration, an
optional block of constant definitions and one or more rule definitions.

```ebnf
rule_file       ::= version_declaration
                    [ const_block ]
                    { rule_definition }
                    EOF

version_declaration ::= "AUSTERITY" major "." minor newline
major               ::= digit { digit }
minor               ::= digit { digit }
```

**Plain English:**

Every rule file begins with exactly one version declaration. This is the
first non-blank, non-comment line in the file. After the version
declaration, an optional `CONST` block may appear, defining named
constants available to all rules in the file. After the `CONST` block,
one or more rule definitions follow. The file ends at EOF.

**Valid:**

```austerity
AUSTERITY 0.1

# Optional constants block, then rules.

CONST
    pi = 3.14159265358979
END

RULE example_rule
WHEN sensor_value > 100
THEN
    status = "HIGH"
END
```

**Invalid — missing version declaration:**

```austerity
RULE example_rule
WHEN sensor_value > 100
THEN
    status = "HIGH"
END
```

Error: *missing version declaration — every Austerity rule file must
begin with AUSTERITY followed by a version number, e.g. AUSTERITY 0.1*

**Invalid — no rules defined:**

```austerity
AUSTERITY 0.1

CONST
    pi = 3.14159265358979
END
```

Error: *rule file contains no rules — at least one RULE definition is
required.*

**Risk note — empty rule files:** a file with a version declaration but
no rules is syntactically almost valid by a naive parser. The grammar
makes `{ rule_definition }` mean zero or more, which would permit an
empty file. This is tightened to one or more here explicitly. An empty
rule file produces no decisions and no audit entries — it is not a
meaningful Austerity program and accepting it silently would be a form
of silent failure. *(See design principle P4.)*

**Risk note — rule ordering:** rules are evaluated in declaration order.
The order in which rules appear in the file is therefore semantically
significant — two files with the same rules in different orders may
produce different simulation outcomes. Version 0.1 has no mechanism to
detect or warn about ordering sensitivity. This is an identified risk.
Static analysis tooling to detect order-sensitive rule sets is deferred
to the v0.2 risk management framework. **[risk: under review — v0.2]**

---

### 2.2 CONST Block

A `CONST` block declares named constants that are available to all rules
in the file. Constants are assigned once at parse time and cannot be
modified during execution.

```ebnf
const_block       ::= "CONST" newline
                      { const_declaration }
                      "END" newline

const_declaration ::= indent identifier "=" literal newline
```

**Plain English:**

The `CONST` keyword opens the block. Each line inside the block declares
one constant: an indented identifier, an equals sign and a literal value.
The block closes with `END`. Constants may be integers, floats, booleans,
or strings. A constant may not be assigned an expression — only a literal
value — because expressions may reference state keys that do not exist at
parse time.

Only one `CONST` block is permitted per file and it must appear before
any `RULE` definitions. This constraint ensures that constants are always
defined before they are referenced.

**Valid:**

```austerity
CONST
    pi              = 3.14159265358979
    gravity         = 9.80665
    speed_of_light  = 299792458
    site_name       = "Junction_14"
    active          = true
END
```

**Invalid — expression as constant value:**

```austerity
CONST
    circumference = 2 * pi * radius    # parse error — expressions not permitted
END
```

Error: *constant values must be literals — expressions and state key
references are not permitted in CONST declarations.*

**Invalid — constant assigned in THEN block:**

```austerity
RULE bad_rule
WHEN sensor > 10
THEN
    pi = 3.0    # parse error — pi is a constant
END
```

Error: *'pi' is a constant and cannot be assigned in a THEN block —
constants are read-only for the lifetime of the simulation.*

**Risk note — constant expression evaluation:** limiting constants to
literals only is a deliberate safety constraint. Allowing expressions in
constants would require the parser to evaluate them at parse time, which
introduces a class of parse-time arithmetic errors — division by zero,
type mismatches in expressions — before the simulation even begins.
Literals are safe: their value and type are unambiguous. The constraint
is strict in v0.1 and may be relaxed in a future version once a
parse-time expression evaluator with full error handling is in place.
**[risk: under review — v0.2]**

---

### 2.3 Rule Definition

A rule definition is the primary unit of logic in an Austerity rule file.

```ebnf
rule_definition ::= "RULE" identifier newline
                    when_clause
                    then_clause
                    "END" newline
```

**Plain English:**

A rule begins with the keyword `RULE` followed by its name — a unique
identifier. The name is followed by a newline. The rule body consists of
exactly one `WHEN` clause and exactly one `THEN` clause, in that order.
The rule closes with `END` on its own line.

Rule names must be unique within a file. Two rules with the same name
is a parse error. The name appears in the audit log every time the rule
fires, so it must be descriptive and unambiguous.

**Valid:**

```austerity
RULE emergency_override
WHEN emergency = true
THEN
    phase       = "ALL_RED"
    cycle_timer = 0
END
```

**Invalid — duplicate rule name:**

```austerity
RULE check_pressure
WHEN pressure > 100
THEN
    alert = true
END

RULE check_pressure        # parse error — name already defined
WHEN pressure > 200
THEN
    alert = true
END
```

Error: *duplicate rule name 'check_pressure' at line 8 — rule names
must be unique within a file. The name was first defined at line 1.*

**Invalid — THEN before WHEN:**

```austerity
RULE bad_order
THEN                       # parse error — WHEN must come before THEN
    status = "ACTIVE"
WHEN sensor > 0
END
```

Error: *unexpected THEN at line 2 — expected WHEN clause before THEN
clause in rule 'bad_order'.*

**Risk note — rule name collisions across files:** in version 0.1, each
rule file is a self-contained unit. Rule name uniqueness is enforced
within a single file. If a future version introduces multiple rule files
loaded together (via an `IMPORT` mechanism), rule name collisions across
files will require a namespacing strategy. This is an identified risk for
the multi-file feature. **[risk: under review — v0.2]**

**Risk note — rules with no effect:** it is possible to write a rule
whose `WHEN` condition can never be satisfied given the initial state and
the other rules in the file — a permanently dead rule. Version 0.1 does
not detect this. A dead rule wastes evaluation time and may indicate a
logic error in the rule set. Static analysis for unreachable rules is
deferred to the v0.2 risk management framework.
**[risk: under review — v0.2]**

---

### 2.4 WHEN Clause

The `WHEN` clause defines the condition under which a rule fires.

```ebnf
when_clause     ::= "WHEN" condition newline

condition       ::= or_condition

or_condition    ::= and_condition { "OR" and_condition }

and_condition   ::= not_condition { "AND" not_condition }

not_condition   ::= "NOT" not_condition
                  | atom_condition

atom_condition  ::= "(" condition ")"
                  | comparison

comparison      ::= operand comparator operand

comparator      ::= "=" | "!=" | ">" | "<" | ">=" | "<="

operand         ::= identifier
                  | literal
```

**Plain English:**

The `WHEN` keyword is followed by a condition expression on the same
line. A condition is a boolean expression composed of comparisons joined
by `AND`, `OR` and `NOT`, with parentheses for explicit grouping.

**Operator precedence** (highest to lowest, matching standard boolean
logic and mathematical convention):

1. `NOT` — applies to the immediately following condition
2. `AND` — joins two conditions, both must be true
3. `OR` — joins two conditions, at least one must be true

Parentheses override precedence. When in doubt, use parentheses — a rule
file should be readable by someone who does not know the precedence table.

**Valid:**

```austerity
WHEN pressure > 100

WHEN temperature > 80 AND humidity < 30

WHEN NOT emergency = true

WHEN (north_queue > 10 OR south_queue > 10) AND phase = "NORTH_SOUTH_GREEN"

WHEN sensor_a > 0 AND (sensor_b = true OR sensor_c > 5)
```

**Invalid — comparison between incompatible types:**

```austerity
WHEN north_queue = "high"    # parse error — north_queue is numeric
```

Error: *type mismatch in condition at line N — 'north_queue' is of type
integer but is being compared to a string literal. Use a numeric value
for comparison.*

**Invalid — bare identifier without comparison:**

```austerity
WHEN emergency               # parse error — boolean keys need explicit comparison
```

Error: *incomplete condition at line N — 'emergency' must be compared
explicitly: WHEN emergency = true*

**Risk note — bare boolean identifiers:** some languages allow a boolean
identifier to appear alone in a condition — `WHEN emergency` meaning
`WHEN emergency = true`. Austerity does not permit this. Requiring the
explicit `= true` or `= false` removes a class of readability ambiguity:
a non-programmer reading `WHEN emergency` cannot know with certainty
whether it means "when emergency is active" or "when the emergency key
exists." Explicit comparisons are unambiguous. This is a deliberate
constraint aligned with the declarative logic principle. *(See design
principle P4.)*

**Risk note — condition complexity:** version 0.1 imposes no limit on
the depth of nested parentheses or the number of `AND`/`OR` clauses in
a condition. A deeply nested condition is syntactically valid but
practically unreadable and difficult to audit. A linting tool that warns
when condition complexity exceeds a configurable threshold is deferred to
the v0.2 risk management framework. **[risk: under review — v0.2]**

**Risk note — floating point equality:** comparing a float state key
with `=` is syntactically valid but carries an inherent numerical risk.
Due to the properties of IEEE 754 arithmetic, two floats that are
mathematically equal may not compare as equal after a series of
operations. For example, a computed value that should be exactly `1.0`
may be stored as `0.9999999999999998`. Using `=` to test float equality
is therefore unreliable in practice. Version 0.1 permits it but the
language reference recommends using range comparisons instead:

```austerity
# Risky — float equality
WHEN temperature = 100.0

# Safer — range comparison
WHEN temperature >= 99.99 AND temperature <= 100.01
```

A parser warning for float equality comparisons is deferred to the v0.2
risk management framework. **[risk: under review — v0.2]**

---

### 2.5 THEN Clause

The `THEN` clause defines the state mutations that occur when a rule fires.

```ebnf
then_clause     ::= "THEN" newline
                    assignment { assignment }
                    
assignment      ::= indent identifier "=" expression newline
```

**Plain English:**

The `THEN` keyword appears on its own line, followed by one or more
assignment lines. Each assignment line must be indented. An assignment
names a state key on the left of the equals sign and an expression on
the right. At least one assignment is required — a `THEN` block with no
assignments is a parse error.

The target of an assignment must be a state key — not a constant and not
a new identifier. Assigning to a key that does not exist in the state
definition is a parse error. *(See design principle P8.)*

**Valid:**

```austerity
THEN
    phase       = "ALL_RED"
    cycle_timer = 0
```

```austerity
THEN
    cycle_timer = cycle_timer + 10
```

```austerity
THEN
    pressure    = base_pressure * correction_factor
    status      = "ADJUSTED"
    updated     = true
END
```

**Invalid — empty THEN block:**

```austerity
RULE empty_action
WHEN sensor > 0
THEN
END
```

Error: *empty THEN block in rule 'empty_action' at line N — at least
one assignment is required.*

**Invalid — assigning to a constant:**

```austerity
THEN
    pi = 3.0    # parse error — pi is a constant
```

Error: *'pi' is a constant and cannot be assigned — constants are
read-only for the lifetime of the simulation.*

**Invalid — assigning to an undefined key:**

```austerity
THEN
    new_key = 42    # parse error — new_key not in state definition
```

Error: *undefined state key 'new_key' at line N — only keys defined in
the state file may be assigned in a THEN block.*

**Risk note — self-referential assignments:** an assignment such as
`cycle_timer = cycle_timer + 10` reads the current value of `cycle_timer`
and writes a new value. In Austerity's execution model, all assignments
within a single THEN block are applied sequentially, top to bottom,
within the same step. This means a later assignment in the same THEN
block sees the value written by an earlier assignment in the same block.

This is explicit and documented behaviour. It is also a source of
potential confusion: the order of assignments within a THEN block is
semantically significant in cases where one assignment reads a key that
a previous assignment has already written. Version 0.1 documents this
behaviour but does not warn about it. A linting tool that detects
intra-block read-after-write dependencies is deferred to the v0.2 risk
management framework. **[risk: under review — v0.2]**

**Risk note — inter-rule state mutation:** when multiple rules fire in
the same step and write to the same key, the last-declared rule wins.
This is the documented conflict resolution policy. The risk is that a
rule author may not be aware that another rule writes to the same key,
leading to silent overwrites. Version 0.1 documents this but does not
warn about it. Static analysis to detect shared-key write conflicts
between rules is deferred to the v0.2 risk management framework.
**[risk: under review — v0.2]**

---

### 2.6 Expressions

An expression appears on the right-hand side of an assignment in a THEN
block. It produces a value of a specific type, which must match the type
of the target state key.

```ebnf
expression      ::= additive_expression

additive_expression
                ::= multiplicative_expression
                    { ( "+" | "-" ) multiplicative_expression }

multiplicative_expression
                ::= unary_expression
                    { ( "*" | "/" | "//" | "%" ) unary_expression }

unary_expression
                ::= "-" unary_expression
                  | power_expression

power_expression
                ::= primary_expression [ "**" unary_expression ]

primary_expression
                ::= "(" expression ")"
                  | identifier
                  | literal
```

**Plain English:**

Expressions follow standard mathematical operator precedence:

1. Parentheses — evaluated first
2. Unary minus — negation of a value
3. `**` — exponentiation, right-associative
4. `*`, `/`, `//`, `%` — multiplication, division, integer division, modulo
5. `+`, `-` — addition and subtraction, left-associative

An identifier in an expression refers to the current value of a state
key or a declared constant. A literal is a fixed value written directly
in the rule file.

**Operator behaviour by type:**

| Operator | Integer | Float | String | Boolean |
|----------|---------|-------|--------|---------|
| `+`      | add     | add   | concatenate | error |
| `-`      | subtract | subtract | error | error |
| `*`      | multiply | multiply | error | error |
| `/`      | float divide | float divide | error | error |
| `//`     | integer divide | integer divide | error | error |
| `%`      | modulo  | modulo | error | error |
| `**`     | power   | power | error | error |

Note that `/` always produces a float result, even when both operands are
integers. `4 / 2` produces `2.0`, not `2`. Use `//` when an integer
result is required. This is a deliberate design choice to prevent silent
loss of fractional parts in division. *(See design principle P1.)*

**Valid:**

```austerity
cycle_timer = cycle_timer + 10

pressure    = base_pressure * 1.05

area        = pi * radius ** 2

label       = "Sensor_" + sensor_id

remainder   = total_count % batch_size

average     = total / count          # produces a float
```

**Invalid — type mismatch in expression:**

```austerity
label = sensor_count + "_units"    # parse error — integer + string
```

Error: *type mismatch in expression at line N — cannot apply '+' to
integer 'sensor_count' and string "_units". Use explicit conversion
when implemented, or restructure the expression.*

**Invalid — division by a literal zero:**

```austerity
ratio = value / 0    # parse error — division by zero literal
```

Error: *division by zero at line N — the divisor is the literal value 0.
If this is intentional, use a state key that you control to avoid
accidental zero division.*

**Risk note — division by zero at runtime:** the grammar catches division
by the literal `0` at parse time. However, division by a state key whose
value becomes zero at runtime cannot be caught at parse time. For example,
`ratio = total / count` is valid syntax, but if `count` reaches zero
during simulation, the engine will encounter a runtime division by zero
error. In version 0.1 the engine raises a clear error message and halts.

A future mitigation is a guard expression syntax — a way to specify a
safe fallback value when a denominator is zero. This is deferred.
**[risk: under review — v0.2]**

**Risk note — integer division truncation:** the `//` operator truncates
toward negative infinity, consistent with Python's behaviour. This means
`-7 // 2` produces `-4`, not `-3`. Rule authors accustomed to C-style
truncation toward zero may find this surprising. This behaviour is
documented here explicitly and is consistent and guaranteed across all
platforms. *(See design principle P7.)*

**Risk note — exponentiation with large exponents:** the `**` operator
on integers with large exponents produces arbitrarily large integers —
Austerity integers do not overflow. However, very large integers consume
proportionally more memory and slow down arithmetic operations. A rule
that computes `2 ** 10000` is syntactically valid but impractical. A
warning for exponentiation with a literal exponent above a configurable
threshold is deferred to the v0.2 risk management framework.
**[risk: under review — v0.2]**

---

### 2.7 Summary of Risk Items Identified in the Grammar

The following table consolidates all risks identified during the drafting
of this grammar. Each item is marked for review in the v0.2 design cycle.

| ID | Location | Risk description | Planned mitigation |
|----|----------|------------------|--------------------|
| G1 | §2.1 | Rule ordering is semantically significant; no warning for order-sensitive rule sets | Static analysis tool — v0.2 |
| G2 | §2.2 | Constants limited to literals; parse-time expression evaluation deferred | Relaxed CONST expressions with full type checking — v0.2 |
| G3 | §2.3 | Dead rules (conditions never satisfiable) not detected | Reachability analysis tool — v0.2 |
| G4 | §2.3 | Rule name collisions across multiple files not yet defined | Namespacing strategy — v0.2 multi-file feature |
| G5 | §2.4 | No limit on condition complexity; deeply nested conditions unreadable | Complexity linting tool — v0.2 |
| G6 | §2.4 | Float equality comparison unreliable due to IEEE 754 properties | Parser warning for float `=` comparisons — v0.2 |
| G7 | §2.5 | Intra-block read-after-write dependencies silently significant | Linting tool for intra-block dependencies — v0.2 |
| G8 | §2.5 | Inter-rule shared-key write conflicts silently resolved by ordering | Static conflict detection tool — v0.2 |
| G9 | §2.6 | Runtime division by zero on state key denominators not preventable at parse time | Guard expression syntax — v0.2 |
| G10 | §2.6 | Large integer exponentiation may cause memory or performance issues | Exponent threshold warning — v0.2 |

This table is the seed of the v0.2 risk management framework described in
design document section 12. It will be reviewed and extended at the start
of the v0.2 design cycle.

---

*Austerity — Version 0.1 — [github.com/austerity-lang/austerity-dsl](https://github.com/austerity-lang/austerity-dsl)*
