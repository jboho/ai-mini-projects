"""pytest configuration: guard the faiss/spaCy OpenMP runtime conflict.

Set before any test module imports faiss or spaCy so the two bundled OpenMP
runtimes don't segfault when loaded into the same process.
"""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
