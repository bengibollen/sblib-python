import sys
import os

# Add the repository root so the private sblib package can be imported.
sys.path.append(os.path.dirname(__file__))

from sblib.startup import startup

startup()

print("Python Efuns loaded.")
