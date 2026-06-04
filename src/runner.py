# runner.py
# Austerity DSL - Version 0.1
#
# Entry point for the Austerity runtime.
#
# The runner wires everything together:
#   - Loads the config file
#   - Loads the state file
#   - Calls the parser to load and validate the rules
#   - Initialises the logger
#   - Runs the simulation step loop
#   - Produces terminal output each step
#     Calls the engine for rule evaluation each step
#   - Generates simulated environment updates each step
#   - Writes the audit log via the logger
#   - Offers to run again with a new seed when complete
#
# Terminal output philosophy
# --------------------------
# Output is old-school ASCII: line by line, scrolling, no screen
# clearing. Each step prints sequentially with a configurable delay.
# Queue lengths are shown as ASCII bar charts. This format was chosen
# because it matches the philosophy of the project - it runs on any
# terminal, from a VT100 to a modern SSH session, without special
# libraries or terminal capabilities.
#
# Usage
# -----
#   python runner.py examples/traffic/config.json
#
# The config file path is the only required argument. Everything else
# (rules file, state file, log file, seed, steps) is read from config.

import sys
import json
import time
import random
import os


def main():
    """
    Entry point. Reads the config path from the command line,
    then runs the simulation.
    """
    if len(sys.argv) < 2:
        print("Usage: python runner.py <config.json>")
        print("  Example: python runner.py examples/traffic/config.json")
        sys.exit(1)

    config_path = sys.argv[1]
    config      = _load_config(config_path)

    # Welcome banner
    _print_banner()

    # Offer the user a chance to change the seed or quit
    seed = _startup_prompt(config)
    if seed is None:
        print("Exiting. Goodbye.")
        return
    
    config['seed'] = seed

    # Run the simulation. Offer to run again when done.
    while True:
        _run_simulation(config)

        again = _run_again_prompt(config)
        if not again:
            print()
            print("Goodbye.")
            break
        # If running again, a new seed was set in config by the prompt


# ----------------------------------------------------------------------
# Simulation lifecycle
# ----------------------------------------------------------------------

def _run_simulation(config):
    """
    Run one complete simulation: load state and rules, step loop,
    write log, print summary.
    """
    # Import here rather than at top level so that import errors
    # point clearly to the missing file, not to runner.py itself.
    from parser import parse, AusterityParseError
    from engine import evaluate_step, apply_environment_update, AusterityEngineError
    from logger import Logger

    # Resolve file paths relative to the config file's directory.
    # This allows the config to use relative paths like
    # "examples/traffic/intersection.rules" regardless of where
    # the runner is launched from.
    config_dir  = os.path.dirname(os.path.abspath(sys.argv[1]))
    rules_path  = os.path.join(config_dir, '..', '..', config['rules_file'])
    state_path  = os.path.join(config_dir, '..', '..', config['state_file'])
    log_path    = os.path.join(config_dir, '..', '..', config['log_file'])

    # Normalise paths (resolve '..' components)
    rules_path = os.path.normpath(rules_path)
    state_path = os.path.normpath(state_path)
    log_path   = os.path.normpath(log_path)

    # Ensure the log directory exists
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # Load state
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except FileNotFoundError:
        _fatal(f"State file not found: '{state_path}'")
    except json.JSONDecodeError as e:
        _fatal(f"State file '{state_path}' is not valid JSON: {e}") 

    # Parse rules
    try:
        rules = parse(rules_path, state)
    except AusterityParseError as e:
        _fatal(str(e))

    # Initialise logger
    log = Logger(log_path, config, state)

    # Initialise random number generator with the seed.
    # The seed is logged in the header (already done by Logger),
    # so any run can be reproduced by using the same seed.
    rng = random.Random(config['seed'])

    steps       = config.get('steps', 50)
    delay_ms    = config.get('step_delay_ms', 500)
    delay_secs  = delay_ms / 1000.0

    print()
    print(f"  Simulation  : {config.get('description', '')}")
    print(f"  Seed        : {config['seed']}")
    print(f"  Steps       : {steps}")
    print(f"  Log         : {log_path}")
    print()
    print("  " + "-" * 60)
    print()

    steps_run = 0

    try:
        for step in range(1, steps + 1):
            steps_run = step

            # --- Environment update ---
            # Generate simulated sensor changes and apply them to state.
            # This happens before rule evaluation each step.
            env_updates = _generate_environment_update(state, rng, config)
            state = apply_environment_update(state, env_updates)

            # --- Rule evaluation ---
            try:
                state, fired_rules = evaluate_step(rules, state)
            except AusterityEngineError as e:
                log.write_footer(steps_run, reason=f"engine error: {e}")
                log.close()
                _fatal(str(e))

            # --- Terminal output ---
            _print_step(step, state, fired_rules)

            # --- Audit log ---
            log.write_step(step, fired_rules, state)

            # --- Step delay ---
            if delay_secs > 0:
                time.sleep(delay_secs)

    except KeyboardInterrupt:
        print()
        print(" [Interrupted by user]")
        log.write_footer(steps_run, reason="interrupted by user")
        log.close()
        return
    
    log.write_footer(steps_run, reason="run complete")
    log.close()

    #Summary 
    print()
    print("  " + "-" * 60)
    print(f"    Run complete. {steps_run} steps executed.")
    print(f"    Full audit log written to: {log_path}")


# -------------------------------------------------------------
# Environment
# -------------------------------------------------------------

def _generate_environment_update(state, rng, config):
    """
    Generate simulated sensor updates for one step.

    This simulates the environment changing around the intersection:
    vehicles arriving and departing, emergency events. In a real
    deployment this function would be replaced by actual sensor reads.

    The simulation logic:
    - Each queue has a chance to grow (vehicles arriving) and a chance
      to shrink (vehicles clearing when the light is green for them).
    - Emergency events are rare and last a few steps.
    - cycle_timer counts down by 1 each step - this is the passage
      of simulated time.

    All randomness is channelled through 'rng', which was seeded at
    the start of the run. This ensures reproducibility: the same seed
    always produces the same sequence of environment updates.
    """
    updates ={}

    # --- Decrement cycle_timer ---
    # This is the heartbeat of the simulation. cycle_timer counts down
    # by 1 each step. Rules react when it reaches zero.
    current_timer = state.get('cycle_timer', 0)
    updates['cycle_timer'] = max(0, current_timer - 1)

    # --- Queue simulation ---
    phase = state.get('phase', '')

    # Arrival rate: 0-3 vehicles per step per direction (random)
    # Departure rate: faster when the light is green for that direction

    for direction in ['north', 'south', 'east', 'west']:
        queue_key   = f'{direction}_queue'
        current     = state.get(queue_key, 0)

        # Vehicles arrive regardless of phase
        arrivals    = rng.randint(0,3)

        # Vehicles depart only when the light is green for this direction
        if direction in ('north', 'south') and phase == 'NORTH_SOUTH_GREEN':
            departures = rng.randint(2, 5)
        elif direction in ('east', 'west') and phase == 'EAST_WEST_GREEN':
            departures = rng.randint(2 ,5)
        else: 
            departures = 0

        new_queue = max(0, current + arrivals - departures)
        updates[queue_key] = new_queue

    # --- Emergency simulation ---
    # A 2% chance per step of an emergency starting.
    # Once active, a 30% chance per step of it clearing.
    current_emergency = state.get('emergency', False)
    if current_emergency:
        if rng.random() < 0.30:
            updates['emergency'] = False
    else:
        if rng.random() < 0.02:
            updates['emergency'] = True
        
    return updates
    

# -----------------------------------------------------------------
# Terminal output
# -----------------------------------------------------------------

def _print_step(step, state, fired_rules):
    """
    Print one step's output to the terminal.

    Format:
     STEP 12   |  phase: NORTH_SOUTH_GREEN  |  timer: 33
     N [===========  ] 8    S [====     ] 5
     E [===          ] 3    W [==       ] 2
     Rules: north_south_green_to_yellow

    The queue bars give an immediate visual sense of load without
    requiring the reader to parse numbers. Each '=' represents one
    vehicle (capped at the bar width).
    """
    phase       = state.get('phase', '?')
    timer       = state.get('cycle_timer', '?')
    emergency   = state.get('emergency', False)
    clearance   = state.get('clearance', False)

    # Phase display with emergency flag
    phase_display = phase
    if emergency:
        phase_display = phase + "  *** EMERGENCY ***"
    elif clearance:
        phase_display = phase + "  (clearance)"

    print(f" STEP {step:>3}  |  {phase_display:<40}   timer: {timer}")

    # Queue bars
    bar_width = 10
    for row in [('north', 'south'), ('east', 'west')]:
        parts = []
        for direction in row:
            count = state.get(f'{direction}_queue', 0)
            bars  = min(count, bar_width)
            bar   = '=' * bars + ' ' * (bar_width - bars)
            parts.append(f" {direction[0].upper()} [{bar}] {count:>3}")
        print(''.join(parts))

    # Fired rules
    if fired_rules:
        print(f"  -> {', '.join(fired_rules)}")
    print()

# -----------------------------------------------------------------
# Prompts
# -----------------------------------------------------------------

def _print_banner():
    """Print the startup banner."""
    print()
    print("  =======================================")
    print("    AUSTERITY DSL  —  Version 0.1        ")
    print("    Traffic Intersection Simulator       ")
    print("  ====================================== ")
    print()


def _startup_prompt(config):
    """
    Ask the user whether to proceed and optionally change the seed.
    
    Returns the seed to use, or None if the user chose to quit.
    """
    default_seed = config.get('seed', 42)

    print(f"  Seed: {default_seed}  (change seed for different run)")
    print()
    print("  [Y] Run with this seed")
    print("  [S] Enter a different seed")
    print("  [N] Quit")
    print()

    while True:
        choice = input("  Your choice: ").strip().upper()
        if choice in ('Y', ''):
            return default_seed
        elif choice == 'S':
            while True:
                raw = input("  Enter seed (integer): ").strip()
                try:
                    return int(raw)
                except ValueError:
                    print(" Please enter a whole number.")
        elif choice == 'N':
            return None
        else:
            print("     Please enter Y, S, or N.")


def _run_again_prompt(config):
    """
    Offer to run again with a new seed after completion.

    Returns True if the user wants to run again (config is updated
    with the new seed). Returns False if the user is done.
    """
    print()
    print(" [Y] Run again with a new seed")
    print(" [N] Quit")
    print()

    while True:
        choice = input("    Your choice: ").strip().upper()
        if choice == 'Y':
            while True:
                raw = input("   Enter new seed (or press Enter for random):  ").strip()
                if raw == '':
                    new_seed = random.randint(0, 999999)
                    print(f"    Using random seed: {new_seed}")
                    config['seed'] = new_seed
                    return True
                try:
                    config['seed'] = int(raw)
                    return True
                except ValueError:
                    print("     Please enter a whole number, or press Ender for random.")
        elif choice == 'N':
            return False
        else:
            print("     Please enter Y or N.")


# -----------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------

def _load_config(path):
    """Load and return the config JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        _fatal(f"Config file not found: '{path}'")
    except json.JSONDecodeError as e:
        _fatal(f"Config file '{path} is not valid JSON: {e}")


def _fatal(message):
    """Print an error and exit."""
    print()
    print(" ERROR:", message)
    print()
    sys.exit(1)


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

if __name__ == '__main__':
    main()
