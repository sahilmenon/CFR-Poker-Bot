"""Put the repo root on sys.path so ``scripts/*.py`` can ``import cfr_poker``."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
