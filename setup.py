# This file serves as an entry point to PIP that uses hardcoded "setup.py" script.
# For development when whole project is checked out, setup_proxy.py and setup_gui.py explicitly need to be run directly.

# In case of PIP, only proxy or only gui is present in the egg file, so this delegates to it.
import os.path

current_dir = os.path.dirname(os.path.realpath(__file__))

is_core = os.path.isfile(current_dir + "/setup_proxy.py")
is_gui = os.path.isfile(current_dir + "/setup_gui.py")

if is_core and is_gui:
    raise Exception("This file should only be run by PIP during installation. "
                    "Please use setup_proxy.py or setup_gui.py")

if is_core:
    import setup_proxy
    exit(0)
elif is_gui:
    import setup_gui
    exit(0)

raise Exception("The distribution must contain either http-proxy or http-proxy-gui subproject")
