"""RAG PDF QA system package.

faiss and sentence-transformers/torch each bundle their own OpenMP runtime;
importing both into one process can segfault on macOS unless duplicate runtimes
are tolerated. Set the guard here so it applies to every entrypoint before
either is imported. See https://github.com/facebookresearch/faiss/issues/2126
"""

import os

# faiss and torch each bundle an OpenMP runtime; running faiss index ops after
# torch on macOS segfaults unless duplicate runtimes are tolerated AND OpenMP is
# single-threaded. Must be set before faiss/torch import. See faiss issue #2126.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
