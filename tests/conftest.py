import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

# app.py creates module-level singletons (store, USERS_FILE, EVENTS_LOG) at
# import time, keyed off the current working directory and environment. Set
# both up before anything imports app, so tests never touch real dev data.
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only")
os.environ.setdefault("VECTOR_BACKEND", "local")

_TEST_DIR = tempfile.mkdtemp(prefix="face_auth_tests_")
os.chdir(_TEST_DIR)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TEST_DIR, ignore_errors=True)
