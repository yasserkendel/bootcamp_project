"""
conftest.py — placed at the module2/ root.

Tells pytest to add the PARENT of module2/ to sys.path,
so that `from module2.xxx import yyy` resolves correctly
regardless of which directory you run pytest from.
"""

import sys
from pathlib import Path

# Insert the directory that CONTAINS the module2/ folder
# e.g. if your layout is:  bootcamp_project/modules/module2/
# this inserts:             bootcamp_project/modules/
sys.path.insert(0, str(Path(__file__).parent.parent))
