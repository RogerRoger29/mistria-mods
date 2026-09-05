import sys

if sys.version_info < (3, 11):
    sys.exit("Mistria Mods needs Python 3.11 or newer (this is %d.%d)."
             % sys.version_info[:2])

"""Mistria Mods."""

# Bump this for every release; the app compares it against GitHub.
VERSION = "1.2.1"
