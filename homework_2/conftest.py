'''
Pytest configuration: make the smoke tests runnable from any directory.

Two things are needed before the test modules import our packages:
  1. `homework_1/` must be on sys.path so `tools` and `prompts` import.
  2. The working directory must be `homework_1/`, because prompts/registry.py
     starts a watchdog observer on the relative "prompts" folder at import time.
'''

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
