from argparse import ArgumentParser
from functools import partial
from redirector import __version__
from redirector.core import Redirector

import logging
import signal
import sys
import traceback


def signal_handler(redirector: Redirector, signum: int, frame) -> None:
    """Handler receiving signals.

    :param redirector: Redirector instance to control
    :param signum: Signal number received
    :param frame: Current stack frame
    """
    if signum in (signal.SIGINT, signal.SIGTERM):
        redirector.stop()

def main() -> int:
    """Entrypoint of the redirector command.
    This launches the program.

    :returns: 0 on success, 1 on error
    """
    # Parse the command line
    parser = ArgumentParser(description="Redirector -- The local DNS load balancer")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "-c", "--config", type=str, required=True, help="Path to the configuration file"
    )
    cmdline_args = vars(parser.parse_args())

    # Initialise Redirector
    try:
        redirector = Redirector(cmdline_args["config"])
    except Exception as e:
        print(f"Failed to initialize Redirector: {e}", file=sys.stderr)
        return 1

    # Attach interrupts and raise exceptions
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, partial(signal_handler, redirector))

    try:
        # Initialise the program
        redirector.initialise()

        # Run the program
        redirector.run()

    except RuntimeError as e:
        if str(e):
            print(f"Runtime error: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"An unhandled exception occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    return 0
