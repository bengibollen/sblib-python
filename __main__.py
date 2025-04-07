import sys
import os

# Add the directory containing ldmudefuns to sys.path
sys.path.append(os.path.dirname(__file__))

from ldmudefuns.startup import startup

startup()

print("Python Efuns loaded.")
