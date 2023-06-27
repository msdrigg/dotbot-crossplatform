import os
from lib import use_environ

def test_use_environ_set_nonexisting_environment():
    k = 'non-existing-env'
    v = 'value'
    assert os.getenv(k) is None
    with use_environ({k: v}):
        assert os.getenv(k) == v
    assert os.getenv(k) is None

def test_use_environ_set_existing_environment():
    k = 'non-existing-env'
    original_v = 'original_value'
    new_v = 'value'
    os.environ[k] = original_v

    assert os.getenv(k) == original_v
    with use_environ({k: new_v}):
        assert os.getenv(k) == new_v
    assert os.getenv(k) == original_v