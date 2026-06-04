# logger.py
# Austerity DSL - Version 0.1
#
# Writes the audit log for a simulation run.
#
# The audit log is a first-class output of the Austerity runtime.
# It cannot be disabled. Every step is recorded: the step number,
# a timestamp, the full state snapshot and the list of rules that
# fired. The log is plain text, readable with any text editor,
# requiring no tooling or programming knowledge to interpret.
#
# Design note: the looger holds the file open for the entire run.
# This is intentional. Opening and closing a file on every step
# has real overhead on constrained hardware. One open, many writes,
# one close is the correct pattern here.
#
# Usage:
#   log = Logger(path="run.log", config=config_dict, state=initial_state)
#   log.write_step(step=1, fired_rules=["rule_a"], state=current_state)
#   log.close()

import datetime

# The separator line used throughout the log.
# A fixed-width ASCII line - readable, unambiguous, no special characters.
SEPARATOR = "-" * 72

class Logger:
    """
    Opens a log file and writes structured plain-text audit entries.
    
    Parameters
    ----------
    path : str
        File path for the log output. Created if it does not exist.
        Overwritten if it does - each run produces a fresh log.
    config : dict
        The full config dictionary. Written to the log header so the
        log is self-contained: you can understand any run from the
        log file alone, without needing the config file beside it.
    initial_state : dict
        The state at the start of the run, before any rules fire.
        Written to the log header as the baseline reference.
    """

    def __init__(self, path, config, initial_state):
        # Open the file in write mode. 'w' creates the file if it doesn't.
        # exist and overwrites it if it does. Each run is a fresh log.
        # encoding='utf-8' is explicit - we never assume a default encoding
        # on constrained or legacy systems.
        self._file = open(path, 'w', encoding='utf-8')
        self._write_header(config, initial_state)

    def _write_header(self, config, initial_state):
        """
        Write the run header. This is the first thing in every log file.

        The header records everything needed to understand and reproduce
        the run: the simulation identity, the random seed, all config
        parameters and the initial state. A reader with only this file
        should be able to understand exactly what ran and why.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._writeln(SEPARATOR)
        self._writeln("Austerity DSL - AUDIT LOG")
        self._writeln(SEPARATOR)
        self._writeln(f"Simulation ID : {config.get('simulation_id', 'unknown')}")
        self._writeln(f"Description   : {config.get('description', '')}")
        self._writeln(f"Started       : {now}")
        self._writeln(f"Random seed   : {config.get('seed', 'not set')}")
        self._writeln(f"Steps planned : {config.get('steps', 'unknown')}")
        self._writeln(f"Step delay    : {config.get('step_delay_ms', 0)} ms")
        self._writeln(f"Rules file    : {config.get('rules_file', 'unknown')}")
        self._writeln(f"State file    : {config.get('state_file', 'unknown')}")
        self._writeln("")

        self._writeln("INITIAL STATE")
        self._writeln(SEPARATOR)
        self._write_state_block(initial_state)
        self._writeln("")
        self._writeln("BEGIN SIMULATION")
        self._writeln(SEPARATOR)
        self._writeln("")

        # Flush immediately after the header. If the run crashes on step 1,
        # the header will still be on disk. This matters on constrained 
        # hardware where writes may be buffered aggressively.
        self._file.flush()
    
    def write_step(self, step, fired_rules, state):
        """
        Write one audit entry for a completed execution step.

        Called by the runner after every step, regardless of whether
        and rules fired. A step where no rules fire is still auditable:
        the full state is recorded and 'no rules fired' is stated
        explicitly - not silently ommited.

        Parameters
        ----------
        step : int
            The step number, starting from 1.
        fired_rules : list of str
            The names of rules that fired this step, in the order they fired.
            May be an empty list.
        state : dict
            The full state after all mutations for this step have been applied.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._writeln(f"STEP {step}   [{now}]")
        self._writeln(SEPARATOR)

        # Rules fired - explicit even when none did. Silence would be
        # ambiguous: did noting fire, or did the logger fail?
        if fired_rules:
            self._writeln(f"Rules fired   : {', '.join(fired_rules)}")
        else:
            self._writeln("Rules fired:   : (none)")
        
        self._writeln("")
        self._writeln("State snapshot:")
        self._write_state_block(state)
        self._writeln("")

        # Flush after every step. On constrained or unstable hardware,
        # an unflushed buffer is data loss waiting to happen.
        self._file.flush()
    
    def write_footer(self, total_steps, reason="run complete"):
        """
        Write the closing section of the log.

        Called by the runner when the simulation ends - whether it
        completed normally, was stopped early or encountered an error.
        The reason paramater makes the end of every run explicit and
        unambigous in the log.

        Parameters
        ----------
        total_steps : int
            How many steps actually executed.
        reason : str
            Why the run ended. Default is 'run complete'.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._writeln(SEPARATOR)
        self._writeln("END OF SIMULATION")
        self._writeln(SEPARATOR)
        self._writeln(f"Ended            : {now}")
        self._writeln(f"Steps rund       : {total_steps}")
        self._writeln(f"Reason           : {reason}")
        self._writeln(SEPARATOR)
        self._file.flush()
    
    def close(self):
        """
        Close the log file.

        Always call this when the run ends. Python will eventually close
        the file when the object is garbage collected, but on constrained
        systems with limited file handles, explicit close is the right
        discipline.
        """
        self._file.close()

    # ----------------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------------

    def _writeln(self, text=""):
        """Write a line of text followed by a newline."""
        self._file.write(text + "\n")

    def _write_state_block(self, state):
        """
        Write the full state as aligned key = value pairs.

        The alignment is cosmetic but important: a human scanning a log
        for a specific key should be able to find it instantly. We
        compute the longest key name and pad all others to match.

        Boolean values are written as 'true' / 'false' (Austerity 
        convention) rather than Python's 'True' / 'False'.
        """
        if not state:
            self._writeln("  (empty state)")
            return
        
        # Find the longest key for alignment
        max_key_len = max(len(k) for k in state)
        
        for key, value in state.items():
            # Format the value according to its type.
            # Booleans must come before the int check - in Python,
            # bool is a subclass of int, so isinstance(True, int) is True.
            if isinstance(value, bool):
                formatted = "true" if value else "false"
            elif isinstance(value, float):
                # Avoid scientific notation in the log - it's harder to
                # read at a glance. Format to 6 decimal places maximum,
                # stripping trailing zeros.
                formatted = f"{value:.6f}".rstrip('0').rstrip('.')
            else:
                formatted = str(value)
            
            padding = max_key_len - len(key)
            self._writeln(f"  {key} {' ' * padding} = {formatted}")