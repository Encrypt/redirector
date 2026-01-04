from argparse import ArgumentParser
from functools import partial
from redirector import __version__
from redirector.core import Redirector

import signal
import sys
import traceback


def signal_handler(redirector, signum, frame):
    """Handler receiving signals.

    :returns: Nothing
    """

    if signum in (signal.SIGINT, signal.SIGTERM):
        redirector.stop()

    elif signum == signal.SIGHUP:
        redirector.reload()


def main():
    """Entrypoint of thr redirector command.
    This launches the program.

    :returns: 0 on success
    """

    # Parse the command line
    parser = ArgumentParser(description="Redirector -- The local DNS load balancer")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument("-c", "--config", type=str, required=True, help="Path to the configuration file")
    cmdline_args = vars(parser.parse_args())

    # Initialise Redirector
    redirector = Redirector(cmdline_args["config"])

    # Attach interrupts and raise exceptions
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, partial(signal_handler, redirector))

    try:

        # Initialise the program
        redirector.initialise()

        # Run the program
        redirector.run()

    except RuntimeError as e:
        if len(str(e)) != 0:
            print(e, file=sys.stderr)
        return 1

    except Exception:
        print("An unhandled exception occured.", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    return 0
