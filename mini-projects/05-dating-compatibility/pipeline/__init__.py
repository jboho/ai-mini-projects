"""Dating compatibility fine-tuning pipeline.

Quiet the tokenizers fork warning and default torch to single-threaded OpenMP to
avoid the macOS faiss/torch-style segfaults seen elsewhere in this repo.
"""

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
