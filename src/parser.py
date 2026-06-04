# parser.py
# Austerity DSL - Version 0.1
#
# Reads a .rules file, validates it against the state definition,
# and returns a list of Rule objects ready for the engine to evaluate.
#
# Safety principles implemented here (from the language reference):
#
#   P4 - Never fails silently.
#        Every error produces a plain-English message with the file name,
#        line number, what was expected and a suggested fix.
#
#   P5 - Version mismatches are loud errors.
#        The first non-comment line must be 'AUSTERITY 0.1'.
#        A missing or wrong version declaration halts execution before
#        any rules are loaded.
#
#   P8 - Undefined references caught before execution.
#        All identifiers in WHEN conditions and THEN assignments are
#        validated against the state definition at parse time. A rule
#        that references an unknown key will never reach the engine.
#
# The parser works in two passes:
#
#   Pass 1 - Tokenisation.
#        The file is read line by line. Comments and blank lines are
#        stripped. Lines are tagged with their original line number
#        (for error messages) and grouped into raw rule blocks.
#
#   Pass 2 - Parsing.
#        Each raw rule block is parsed into a Rule object: a name,
#        a condition string and a list of assignment strings.
#        Identifiers are validated agains the state a this stage.
#
# The parser does not evaluate expressions. That is the engine's job.
# The parser's job is to check structure and identifiers - not to run
# the logic. This separation keeps both modules focused and testable.


# -----------------------------------------------------------------
# Data structure: Rule
# -----------------------------------------------------------------
# A Rule is a named container with two parts:
#
#   condition - the raw WHEN clause as a string, e.g.
#               "phase = \"NORTH_SOUTH_GREEN\" AND cycle_timer = 0"
#
#   assignments - a list of raw THEN assignment strings, e.g.
#                 ["phase = \"NORTH_SOUTH_YELLOW"", "cycle_timer = 5"]
#
# Keeping these as strings means the parser does minimal work and
# the engine has full control over evaluation. The parser validates
# structure and identifiers; the engine evaluates logic.

import re

class Rule:
    """
    A parse Austerity rule.

    Attributes
    ----------
    name : str
        The rule name as declared. Unique within a rule file.
    condition : str
        The raw WHEN clause. Validated for indentifier references.
        Evaluated by the engine at runtime.
    assignments : list of str
        The raw THEN assignment lines, in declaration order.
        Evaluated by the engine at runtime.
    source_line : int
        The line number of the RULE declaration in the source file.
        Used in engine-level error messages.
    """
    def __init__(self, name, condition, assignments, source_line):
        self.name        = name
        self.condition   = condition
        self.assignments = assignments
        self.source_line = source_line

    def __repr__(self):
        return (f"Rule(name={self.name!r}, "
                f"condition={self.condition!r}, "
                f"assignments={self.assignments!r})")


# ---------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------

def parse(rules_file, state):
    """
    Parse a .rules file and return a list of Rule objects.

    This is the only function the rest of the system needs to call.

    Parameters
    ----------
    rules_file : str
        Path to the .rules file to parse.
    state : dict
        The current state dictionary. Used to validate that all
        identifiers in rules refer to known keys.

    Returns
    -------
    list of Rule
        Rules in declaration order. The engine evaluates them in 
        this order. Declaration oder is semantically significant.

    Raises
    ------
    AusterityParseError
        If the file cannot be read, the version declaration is wrong,
        or any structural or identifier validation error is found.
        The error message includes the file name, line number, what
        was wrong and a suggested fix (P4).
    """
    raw_lines = _read_file(rules_file)
    tagged    = _tag_and_strip(raw_lines, rules_file)
    _check_version(tagged, rules_file)
    blocks    = _group_into_blocks(tagged, rules_file)
    rules     = _parse_blocks(blocks, state, rules_file)
    return rules
        

# ---------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------

class AusterityParseError(Exception):
    """
    Raised when the parser finds a problem in a .rules file.

    The message always includes:
    - the file name
    - the line number (where available)
    - what was wrong
    - what was expected
    - a suggested fix

    This implements safety principle P4: never fail silently.
    A parse error is always information enough to be acted on
    without access to the source code of the parser itself.
    """
    pass

# --------------------------------------------------------------
# Pass 1 - Read, tag, strip
# --------------------------------------------------------------

def _read_file(path):
    """
    Read the file and return its lines. Raises a clear error if
    the file cannot be opened (wrong path, permissions, etc.).
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except FileNotFoundError:
        raise AusterityParseError(
            f"File not found: '{path}'\n"
            f"  Check that the path in your config file is correct."
        )
    except PermissionError:
        raise AusterityParseError(
            f"Permission denied reading: '{path}'\n"
            f"  Check that the file is readable by the current user."
        )
    

def _tag_and_strip(raw_lines, filename):
    """
    Strip comments and blank lines. Tag each remaining line with
    its original line number (1-indexed, as editors display them).

    Returns a list of (line_numer, text) tuples. The text has
    been stripped of leading/trailing whitespace and inline comments.

    Why preserve line numbers? Because error messages must say
    'line 42' - not 'somehwere in the file'. A developer debugging
    a rules file on a legacy system may only have a basic text editor
    with line numbers. (P4)
    """
    tagged = []
    for i, raw in enumerate(raw_lines, start=1):
        # Strip inline comments: everyting from # to end of line.
        # This handels lines like: cycle_timer = 5  # reset timer
        if '#' in raw:
            raw = raw[:raw.index('#')]

        line = raw.strip()

        # Skip blank lines (including lines that were entirely comments).
        if not line:
            continue

        tagged.append((i, line))

    return tagged

def _check_version(tagged, filename):
    """
    Verify that the first non-comment line is the version declaration.

    Safety principle P5: version mismatches are loud errors. A file
    without the correct version declaration may have been written for
    a different version of the language. Executing it silently could
    produce incorrect behaviour. We halt before loading any rules.

    The expected declaration is: AUSTERITY 0.1
    """
    if not tagged:
        raise AusterityParseError(
            f"File '{filename}' is empty or contains only comments.\n"
            f"  Every Austerity rule file must begin with: AUSTERITY 0.1"
        )
    
    line_no, first_line = tagged[0]

    if first_line !="AUSTERITY 0.1":
        raise AusterityParseError(
            f"File '{filename}', line {line_no}: version declaration missing or incorrect.\n"
            f"  Found    : {first_line!r}\n"
            f"  Expected : 'AUSTERITY 0.1'\n"
            f"  Fix      :  Make 'AUSTERITY 0.1' the first non-comment line of your file"
        )
    

# -----------------------------------------------------------------------
# Pass 1 - Group into raw blocks
# -----------------------------------------------------------------------

def _group_into_blocks(tagged, filename):
    """
    Group the tagged lines into raw rule blocks.

    A block is everything from a RULE declaration to its matching END.
    Returns a list of blocks, where each block is a list of
    (line_number, text) tuples.

    We skip the version declaration line (index 0) - it has already
    been validated and has no further role in parsing.

    Errors caught here:
    - END without a preceding RULE
    - RULE without a closing END (detected at end of file)
    - Nested RULE declarations (not supported in v0.1.)
    """
    blocks      = []
    current     = None      # the block we're currently building, or None

    # Skip the version declaration (index 0)
    for line_no, line in tagged[1:]:
        if line.startswith("RULE "):
            if current is not None:
                # We hit a new RULE before the previous one had END.
                raise AusterityParseError(
                    f"File '{filename}', line {line_no}: "
                    f"found 'RULE' before previous rule was closed with 'END'.\n"
                    f"  The previous rule starting at line {current[0][0]} "
                    f"is missing its 'END' keyword.\n"
                    f"  Fix: Add 'END' after the last assignment of that rule."
                )
            current = [(line_no, line)]
        
        elif line == "END":
            if current is None:
                raise AusterityParseError(
                    f"File '{filename}', line {line_no}: "
                    f"found 'END' with no matching 'RULE'.\n"
                    f"Fix: Remove this 'END', or add a 'RULE ... WHEN ... THEN' block before it."
                )
            current.append((line_no, line))
            blocks.append(current)
            current = None
        
        else:
            if current is None:
                raise AusterityParseError(
                    f"File '{filename}', line {line_no}: "
                    f"unexpected content outside a RULE block: {line!r}\n"
                    f"  Fix: All content must appear inside a RULE / WHEN / THEN / END block."
                )
            current.append((line_no, line))

    # If we're still inside a block when the file ends, the last rule is unclosed.
    if current is not None:
        raise AusterityParseError(
            f"File '{filename}': rule '{current[0][1]}' (line {current[0] [0]}) "
            f"has no closing 'END'.\n"
            f"  Fix: Add 'END' after the last assignment of this rule."
        )
    
    if not blocks:
        raise AusterityParseError(
            f"File '{filename}' contains no rules.\n"
            f"  An Austerity rule file must contain at least one RULE block."
        )
    
    return blocks

# ------------------------------------------------------------------
# Pass 2 - Parse blocks into Rule objects
# ------------------------------------------------------------------

def _parse_blocks(blocks, state, filename):
    """
    Parse each raw block into a Rule object.

    For each block this function:
    1. Extracts the rule name from the RULE line.
    2. Finds and validates the WHEN line.
    3. Finds and validates the THEN line and the assignments below it.
    4. Validates all identifiers in the condition and assignments
       against the state definition (P8).
    5. Checks for duplicate rule names.
    
    Returns a list of Rule objects in declaration order.
    """
    rules      = []
    seen_names = set()  # for duplicate name detection

    for block in blocks:
        rule = _parse_single_block(block, state, filename)

        if rule.name in seen_names:
            raise AusterityParseError(
                f"File '{filename}', line {rule.source_line}: "
                f"duplicate rule name '{rule.name}'.\n"
                f"  Rule names must be unique within a file.\n"
                f"  Fix: Rename one of the rules named '{rule.name}'."
            )
        
        seen_names.add(rule.name)
        rules.append(rule)
    
    return rules

def _parse_single_block(block, state, filename):
    """
    Parse one raw block (list of tagged lines) into a Rule object.
    
    Expected structure:
        RULE <name>
        WHEN <condition>
        THEN
            <key> = <value or expression
            ...
        END
    """
    # Extract lines with their numbers for error reporting
    lines = block   # list of (line_no, text)

    # --- RULE line ---
    rule_line_no, rule_line = lines[0]
    # We already know it starts with "RULE " (checked in _group_into_blocks)
    parts = rule_line.split(None, 1)    # split on first whitespace, max 2 parts
    if len(parts) < 2 or not parts[1].strip():
        raise AusterityParseError(
            f"File '{filename}', line {rule_line_no}: "
            f"'RULE' keyword with no name.\n"
            f"  Fix: Write 'RULE my_rule_name' with a valid identifier after RULE."
        )
    rule_name = parts[1].strip()
    _validate_identifier(rule_name, rule_line_no, filename, context="rule name")

    # --- Find WHEN and THEN positions ---
    when_idx  = None
    then_idx  = None
    
    for i, (line_no, line) in enumerate(lines):
        if line.startswith("WHEN") or line == "WHEN":
            when_idx = i
        elif line == "THEN":
            then_idx = i

    if when_idx is None:
        raise AusterityParseError(
            f"File '{filename}', line {rule_line_no}: "
            f"rule '{rule_name}' has no WHEN clause.\n"
            f"  Fix: Add 'WHEN <condition>' between RULE and THEN."
        )
    
    if then_idx is None:
        raise AusterityParseError(
            f"File '{filename}', line {rule_line_no}: "
            f"rule '{rule_name}' has no THEN block.\n"
            f"  Fix: Add 'THEN' followed by at least one assignment."
        )
    
    if then_idx <= when_idx:
        raise AusterityParseError(
            f"File '{filename}', line {rule_line_no}: "
            f"rule '{rule_name}' has no THEN before WHEN.\n"
            f"  Fix: RULE must be followed by WHEN, then THEN, then END."
        )
    
    # --- WHEN clause ---
    when_line_no, when_line = lines[when_idx]
    # The condition is everything after "WHEN "
    condition = when_line[5:].strip() if when_line.startswith("WHEN ") else ""

    if not condition:
        raise AusterityParseError(
            f"File '{filename}', line {when_line_no}: "
            f"rule '{rule_name}' has an empty WHEN clause.\n"
            f"  Fix: Provide a condition, e.g. 'WHEN phase = \"ALL_RED\"'."
    )

    # Validate identifiers in the condition against state
    _validate_condition_identifiers(condition, state, when_line_no, rule_name, filename)

    # --- THEN assignments ---
    # Everything between THEN and END (exclusive), skipping END itself
    assignment_lines = lines[then_idx + 1 : -1]  # -1 excludes END

    if not assignment_lines:
        raise AusterityParseError(
            f"File '{filename}', line {rule_line_no}: "
            f"rule '{rule_name}' has an empty THEN block.\n"
            f"  Fix: Add at least one assignment inside THEN / END."
        )

    assignments = []
    for line_no, line in assignment_lines:
        # Each assignment must contain '='
        if '=' not in line:
            raise AusterityParseError(
                f"File '{filename}', line {line_no}: "
                f"expected an assignment (key = value) in THEN block of rule '{rule_name}'.\n"
                f"  Found: {line!r}\n"
                f"  Fix: Each line in a THEN block must be in the form 'key = expression'."
            )
        assignments.append(line)

        # Validate the target key (left side of =) against state (P8)
        target_key = line.split('=', 1) [0].strip()
        _validate_identifier(target_key, line_no, filename, context="assignment target")
        if target_key not in state:
            raise AusterityParseError(
                f"File '{filename}', line {line_no}: "
                f"rule '{rule_name}' assigns to '{target_key}', "
                f"which is not defined in the state.\n"
                f"  Known state keys: {sorted(state.keys())}\n"
                f"  Fix: Add '{target_key}' to your state file, "
                f"or correct the spelling in the rule."
            ) 
    
    return Rule(
        name        = rule_name,
        condition   = condition,
        assignments = assignments,
        source_line = rule_line_no,
    )

# --------------------------------------------------------------------
# Identifier validation helpers
# --------------------------------------------------------------------

def _validate_identifier(name, line_no, filename, context="identifier"):
    """
    Check that a name is a valid Austerity identifier.

    Rules (from the language reference):
    - Must start with a letter (a-z or A-Z)
    - May contain letters, digits and underscores
    - snake_case is the convention

    We do not check against reserved words here - that is a v0.2
    concern. In v0.1, reserved words are only reserved in syntax
    position (RULE, WHEN, THEN, END, AND, OR, NOT, AUSTERITY).
    """
    if not name:
        raise AusterityParseError(
            f"File '{filename}', line {line_no}: "
            f"empty {context}.\n "
            f"  Fix: Provide a non-empty name starting with a letter."
        ) 

    if not name[0].isalpha():
        raise AusterityParseError(
            f"File '{filename}', line {line_no}: "
            f"{context} '{name}' must start with a letter.\n "
            f"  Fix: Rename it to start with a-z or A-Z."
        ) 
    
    for ch in name:
        if not (ch.isalnum() or ch == '_'):
            raise AusterityParseError(
                f"File '{filename}', line {line_no}: "
                f"{context} '{name}' contains invalid character '{ch}'.\n "
                f"  Identifiers may only contain letters, digits and underscores.\n"
                f"  Fix: Remove or replace '{ch}'."
        )

# These are the keywords that appear inside WHEN conditions and THEN
# expressions. We exclude them from identifier validation - thy are 
# syntax, not state references.
_CONDITION_KEYWORDS = {'AND', 'OR', 'NOT', 'true', 'false'}

def _validate_condition_identifiers(condition, state, line_no, rule_name, filename):
    """
    Extract identifiers from a condition string and check each one
    against the state definition. (Safety principle P8.)

    This is a conservative approach: we tokenise the condition roughly
    by splitting on operators and whitespace, then check any token that
    looks like an identifier (starts with a letter, not a keyword, not 
    a string literal, not a number).

    This will not catch every possible error - expression parsing is
    the engine's job - but it catches the most common mistake: a typo
    in a state key name that would otherwise silently never fire.
    """
    # Remove string literals to avoid treating their contents as identifiers.
    # We replace quoted strings with a placeholder before tokenising.
    cleaned = _strip_string_literals(condition)

    # Split on common operator characters and whitespace to get tokens
    tokens = re.split(r'[\s\(\)=!<>+\-*/]+', cleaned)

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Skip numbers (integer or float)
        try:
            float(token)
            continue
        except ValueError:
            pass

        # Skip known keywords
        if token in _CONDITION_KEYWORDS:
            continue

        # Skip anything that doesn't look like an identifier
        if not token[0].isalpha():
            continue

        # This looks like an identifier - validate it exists in state
        if token not in state:
            raise AusterityParseError(
                f"File '{filename}', line {line_no}: "
                f"rule '{rule_name}' references '{token}' in its WHEN clause,\n "
                f"but '{token} is not defined in the state.\n "
                f"  Known state keys: {sorted(state.keys())}'\n "
                f"  Fix: Add '{token}' to your state file, "
                f"or correct the spelling in the rule."
        )

def _strip_string_literals(text):
    """
    Replace quoted string content with a placeholder so that words
    inside strings are not mistakenly treated as identifiers.

    Handles both single and double quoted strings.
    Examples:
        'phase = "NORTH_SOUTH_GREEN"'   -> 'phase = ""'
        "label = 'hello world'"         -> "label = ''"
    """
    result  = []
    i       = 0
    while i < len(text):
        ch = text[i]
        if ch in ('"', "'"):
            quote_char = ch
            result.append(ch)
            i += 1
            # Skip everything until the closing quote
            while i < len(text) and text[i] != quote_char:
                i += 1
            # Append the closing quote if present
            if i < len(text):
                result.append(text[i])
                i += 1
        else:
            result.append(ch)
            i += 1
    return ''.join(result)

