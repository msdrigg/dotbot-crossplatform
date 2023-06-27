import os
from contextlib import contextmanager


def is_powershell(s):
    return s.lower() in { 'ps', 'pwsh', 'powershell' }


@contextmanager
def use_environ(environ_dict):
    old_environments = {k: os.getenv(k)  for k in environ_dict}
    for k, v in environ_dict.items():
        os.environ[k] = v
    yield
    for k, v in old_environments.items():
        if v is None:
            del os.environ[k]
        else:
            os.environ[k] = v