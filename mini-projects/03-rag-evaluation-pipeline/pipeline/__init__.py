"""RAG evaluation pipeline package.

faiss and spaCy/torch each bundle their own OpenMP runtime; importing both into
one process segfaults on macOS unless duplicate runtimes are tolerated. Set the
guard here so it applies to every entrypoint (CLI and tests) before either is
imported. See https://github.com/facebookresearch/faiss/issues/2126
"""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
