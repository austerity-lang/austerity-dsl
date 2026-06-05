# engine.py
# Austerity DSL - Version 0.1
#
# Evaluates rules against state and applies mutations.
#
# This is the execution core of the Austerity runtime. It takes the
# list of Rule objects produced by the parser and a current state dict,
# evaluates each rule's condition and applies the mutations from rules
# that fire. It returns the updated state and the names of rules that
# fired - both are needed by the runner and the logger.
#
# What the engine is responsible for:
#
#   - Evaluating WHEN conditions against current state
#   - Evaluating THEN expressions and applying mutations
#   - Enforcing conflict resolution: last-declared rule wins
#   - Clamping cycle_timer at zero after environment updates
#   - Producing a list of fired rule names, in firing order
#
# What the engine is NOT responsible for:
#
#   - Reading files (the parser's job)
#   - Writing logs (the logger's job)
#   - Simulating environment changes (the runner's job)
#   - Driving the step loop (the runner's job)
#
# On expression evaluation
# ------------------------
# The engine uses Python's eval() to evaluate conditions and
# expressions. This is a pragmatic choice for the MVP. eval() gives
# us full arithmetic and comparison support without writing an
# expression parser from scratch.
#
# The risk: eval() can execute arbitrary Python code. We mitigate this
# by passing a restricted globals dict with __builtins__ disabled,
# and a carefully constructed locals dict built only from the current
# state. This is documented as a known limitation (grammar risk G9 is
# related: division by zero is possible at runtime). A full expression
# parser is the v0.2 path.
#
# On boolean representation
# -------------------------
# Austerity uses lowercase 'true' and 'false'. Python uses 'True' and
# 'False'. Before evaluating any expression, we translate Austerity
# booleans to Python booleans in the evaluation context. In state
# values, Python bools are used internally; they are formatted as
# 'true'/'false' by the logger.
import re

class AusterityEngineError(Exception):
    """
    Raised when the engine encounters a runtime error.

    Includes the rule name and a plain-English explanation. (P4)
    """
    pass


def evaluate_step(rules, state):
    """
    Evaluate all rules against the current state and return the
    updated state and the list of rules that fired.

    This is the main entry point for the engine. It is called once
    per simulation step by the runner, after the environment update
    has been applied.

    Rules are evaluated in declaration order. All rules whose
    conditions are true are collected. Their mutations are then
    applied in declaration order. If two rules write the same key,
    the later-declared rule's value wins - this is the documented
    conflict resolution behaviour.

    Paramaters
    ----------
    rules : list of Rule
        The parsed rules, in declaration order.
    state : dict
        The current state. This dict is NOT modified in place.
        A new dict is returned. The caller always works with the
        returned state after calling this function.

    Returns
    -------
    updated_state : dict
        The state after all rule mutations have been applied.
    fired_rule_names : list of str
        The names of rules that fired, in the order they fired.
        May be empty if no conditions were true this step.
    """
    # Work on a copy so the original state is not modified in place.
    # This makes the function predictable and testable: the same
    # inputs always produce the same outputs, with no side effects.
    working_state = state.copy()
    fired_names   = []
    
    for rule in rules:
        if _condition_is_true(rule, working_state):
            fired_names.append(rule.name)
            _apply_assignments(rule, working_state)

    return working_state, fired_names


def apply_environment_update(state, updates):
    """
    Apply environment changes (simulated sensor values) to state,
    then clamp cycle_timer at zero.

    Environment updates represent the passage of time and changes
    in the physical world - queue lengths fluctuating, emergency
    flags changing. They are applied before rule evaluation each step.

    The cycle_timer countdown is an environment update: it represents
    the passage of simulated time. It is not a rule. Rules react when
    cycle_timer reaches zero; they do not decrement it.

    After every environment update, cycle_timer is clamped at zero..
    It must never go negative. This is a hard invariant of the system.

    Parameters
    ----------
    state : dict
        The current state. Modified in place (unlike evaluate_step,
        which returns a copy). Environment updates are lower-level
        than rule evaluation.
    updates : dict
        Key-value pairs to apply to state. Only keys that exist in 
        state are applied; unknown keys raise an error.

    Returns
    -------
    dict
        The updated state (same object as input, returned for
        convenience so callers can chain calls if needed).
    """
    for key, value in updates.items():
        if key not in state:
            raise AusterityEngineError(
                f"Environment update references unknown state key '{key}'.\n"
                f"  Known state keys: {sorted(state.keys())}\n"
                f"  Fix: Only update keys that are defined in the state file."
            )
        state[key] = value

    # Clamp cycle_timer at zero. This is non-negotiable.
    # The engine never allows cycle_timer to go negative.
    if 'cycle_timer' in state:
        if state['cycle_timer'] < 0:
            state['cycle_timer'] = 0

    return state 


# -----------------------------------------------------------------
# Private: condition evaluation
# -----------------------------------------------------------------

def _condition_is_true(rule, state):
    """
    Evaluate the WHEN condition of a rule against the current state.

    Returns True if the condition is satisfied, False otherwise.
    Raises AusterityEngineError if the condition cannot be evaluated
    (e.g. a division by zero, or a type error).

    The condition is a string like:
        'phase = "NORTH_SOUTH_GREEN" AND cycle_timer = 0'
        'north_queue > 10 AND emergency = false'

    We translate this into a Python expression and evaluate it using
    eval() with a restricted context built from the current state.

    Translation rules:
    - Austerity '='  becomes Python '=='
    - Austerity 'AND' becomes Python 'and'
    - Austerity 'OR'  becomes Python 'or'
    - Austerity 'NOT' becomes Python 'not'
    - Austerity 'true' / 'false' are injected as Python True / False
      into the evaluation context
    """
    python_expr = _translate_condition(rule.condition)
    context     = _build_eval_context(state)
    
    try:
        result = eval(python_expr, {"__builtins__": {}}, context)
    except ZeroDivisionError:
        raise AusterityEngineError(
            f"Rule '{rule.name}' (line {rule.source_line}): "
            f"division by zero in WHEN condition.\n"
            f"  Condition: {rule.condition}\n"
            f"  This is grammar risk G9. Consider adding a guard condition."
        )
    except Exception as e:
        raise AusterityEngineError(
            f"Rule '{rule.name}' (line {rule.source_line}): "
            f"could not evaluate WHEN condition.\n"
            f"  Condition:  {rule.condition}\n"
            f"  Detail:     {e}\n"
            f"  Translated: {python_expr}"
        )
    
    # The result must be a boolean. If a condition accidentally
    # evaluates to a non-boolean (e.g. a number), we reject it.
    if not isinstance(result, bool):
        raise AusterityEngineError(
            f"Rule '{rule.name}' (line {rule.source_line}): "
            f"WHEN condition did not evaluate to true or false.\n"
            f"  Condition:  {rule.condition}\n"
            f"  Result:     {result!r} (type: {type(result).__name__})\n"
            f"  Fix: Ensure the condition uses a comparison operator "
            f"(=, !=, <, >, <=, >=)."
        )
    
    return result


def _translate_condition(condition):
    """
    Translate an Austerity condition string into a Python expression
    suitable for eval().

    Austerity uses '=' for equality comparison. Python uses '=='.
    We replace standalone '=' with '==' while leaving '!=', '<=',
    and '>=' untouched

    Austerity keywords AND / OR / NOT become Python and / or / not.
    These are whole-word replacements only - we must not replace 'AND'
    inside an identifier like 'bandwidth'. We use word-boundary logic.
    """


    expr = condition

    # Replace single '=' with '==' - but not '!=', '<='. '>='. '=='
    # Strategy: replace '==' with a placeholder, do the = -> == replacement,
    # then restore the placeholder. This avoids double-replacing '=='.
    expr = expr.replace('==', '\x00DBLEQ\x00')
    expr = expr.replace('!=', '\x00NEQ\x00')
    expr = expr.replace('<=', '\x00LEQ\x00')
    expr = expr.replace('>=', '\x00GEQ\x00')
    expr = expr.replace('=', '==')
    expr = expr.replace('\x00DBLEQ\x00', '==')
    expr = expr.replace('\x00NEQ\x00',   '!=')
    expr = expr.replace('\x00LEQ\x00',   '<=')
    expr = expr.replace('\x00GEQ\x00',   '>=')

    # Replace whole-word AND / OR / NOT with Python equivalents.
    # \b is a word boundary in regex.
    expr = re.sub(r'\bAND\b', 'and', expr)
    expr = re.sub(r'\bOR\b',  'or',  expr)
    expr = re.sub(r'\bNOT\b', 'not', expr)

    return expr


# -------------------------------------------------------------------
# Private: assignment evaluation
# -------------------------------------------------------------------

def _apply_assignments(rule, state):
    """
    Apply the THEN assignments of a rule to the state.

    Assignments are applied sequentially, top to bottom, within
    the rule. Each assignment may read from the state as it stands
    after previous assignments in the same THEN block - this is
    the documented intra-block read-after-write behaviour (G7).

    If two rules in the same step both assign to the same key,
    the last rule to fire wins - this is enforced by the order of
    calls from evaluate step, which processes rules in declaration
    order. The last assignment to a key in the step is the winner.

    After all assignments, cycle_timer is clamped at zero.
    A rule that substracts from cycle_timer (e.g. reduce_cycle_on_low_traffic)
    must not be able to push the timer negative. This mirrors the 
    same guarantee in appy_environment_update
    """
    for assignment in rule.assignments:
        _apply_single_assignment(rule, assignment, state)

    # Clamp cycle_timer at zero after all assignments.
    # Rules that substract form cycle_timer (e.g. reduce_cycle_on_low_traffic)
    # must not be able to pus the timer negative.
    if 'cycle_timer' in state and state['cycle_timer'] < 0:
        state['cycle_timer'] = 0


def _apply_single_assignment(rule, assignment, state):
    """
    Evaluate one assignment line and update state.

    An assignment looks like:
        phase       = "NORTH_SOUTH_YELLOW"
        cycle_timer = cycle_timer + 10
        clearance   = false

    We split on the first '=' to get the target key and the
    right-hand side expression. The expresion is evaluated in 
    the current state context.

    Type safety: the assigned value must be compatible with the
    type of the existing state value. We enforce this to prevent
    accidental type corruption - e.g. assigning a string to a 
    key that was initialised as a number.
    """
    # Split on first '=' only. This correctly handles expressions
    # like 'cycle_timer = cycle_timer + 10' where '=' appears once.
    parts = assignment.split('=', 1)
    if len(parts) != 2:
        raise AusterityEngineError(
            f"Rule '{rule.name}': malformed assignment: {assignment!r}\n"
            f"  Fix: Assignments must be in the form 'key = expression'."
        )
    
    target_key = parts[0].strip()
    rhs        = parts[1].strip()

    # Evaluate the right-hand side
    context = _build_eval_context(state)

    try:
        new_value = eval(rhs, {"__builtins__": {}}, context)
    except ZeroDivisionError:
        raise AusterityEngineError(
            f"Rule '{rule.name}': division by zero in assignment: {assignment!r}\n"
            f"  This is grammar risk G9. Consider adding a guard condition."
        )
    except Exception as e:
        raise AusterityEngineError(
            f"Rule '{rule.name}': could not evaluate assignment: {assignment!r}\n"
            f"  Detail: {e}"
        )
    
    # Type compatibility check.
    # We allow the new value to be the same type as the existing value,
    # pr a compatible numeric type (int <-> float is permitted because
    # arithmetic on integers can produce floats, e.g. cycle_timer + 0.5).
    existing_value = state[target_key]
    _check_type_compatibility(target_key, existing_value, new_value, rule)

    state[target_key] = new_value
    

def _check_type_compatibility(key, existing, new_value, rule):
    """
    Enfore type safety on assignments.

    Permitted:
    - Same type (int -> float, float -> float, str -> str, bool -> bool )
    - int -> float or float -> int (numeric types are compatible)

    Not permitted:
    - str -> int, bool -> str, etc.

    This implements a lightweight version of P1 (no implicit type
    conversion). We do not convert silently - we raise an error.

    Note: bool must be checked before int because in Python,
    bool is a subclass of int. isinstance(True, int) is True.
    We treat bool as its own type for this check.
    """
    def type_name(v):
        if isinstance(v, bool):
            return 'boolean'
        elif isinstance(v, int):
            return 'integer'
        elif isinstance(v, float):
            return 'float'
        elif isinstance(v, str):
            return 'string'
        else:
            return type(v).__name__
        
    existing_type = type_name(existing) 
    new_type      = type_name(new_value)

    # Exact match - always fine
    if existing_type == new_type:
        return
    
    # Numeric compatibility - int and float may be assigned to each other
    if existing_type in ('integer', 'float') and new_type in ('integer', 'float'):
        return
    
    raise AusterityEngineError(
        f"Rule '{rule.name}': type error assigning to '{key}'.\n"
        f"  State has '{key}' as {existing_type} (value: {existing!r})\n"
        f"  Assignment would set it to {new_type} (value: {new_value!r})\n"
        f"  Austerity does not permit implicit type conversion. (P1)\n"
        f"  Fix: Ensure the expression produces a {existing_type} value."
    )


# -------------------------------------------------------------------------
# Private: evaluation context
# -------------------------------------------------------------------------

def _build_eval_context(state):
    """
    Build the context dictionary for eval().

    This dict is passed as the 'locals' argument to eval(). It
    contains the current state values, plus 'true' and 'false' as
    Python booleans.

    'true' and 'false' are injected explicitly because Austerity
    uses lowercase booleans. Without this injection, eval() would
    not recognise them (Python uses 'True' and 'False').

    The 'globals' argument to eval() will be {"__builtins__": {}},
    which disables access to Python builtins. This prevents rules
    from calling arbitrary Python functions.

    State values are copied in directly. String values will be
    compared correctly because eval() handles quoted string literals
    in the expression (e.g. phase == "NORTH_SOUTH_GREEN") against
    unquoted string values in the context (e.g. phase = "NORTH_SOUTH_GREEN").
    """
    context = {}
    context.update(state)           #  all state keys become val variables
    context['true'] = True          # Austerity 'true'  -> Python True
    context['false'] = False        # Austerity 'false' -> Python False
    return context

