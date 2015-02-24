"""
Primary command line hook.
"""

from twisted.conch.stdio import runWithProtocol
from twisted.python.log import startLogging

from cockpit import Cockpit

# Demarre une ligne de commande
def main():
    startLogging(file('calamity.log', 'w'))
    runWithProtocol(Cockpit)
