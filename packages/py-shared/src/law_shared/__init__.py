"""Shared Python utilities for the Law monorepo."""

from .env import load_env

load_env()

__all__ = ["load_env"]


def _patch_botocore_vendor() -> None:
    import importlib
    import sys
    import types

    try:
        urllib3_module = importlib.import_module("urllib3")
    except ModuleNotFoundError:
        return

    module = types.ModuleType("botocore.vendored.requests.law_shared")
    module.urllib3 = urllib3_module
    sys.modules.setdefault("botocore.vendored.requests.law_shared", module)
    sys.modules.setdefault("botocore.vendored.requests.law_shared.urllib3", urllib3_module)


_patch_botocore_vendor()
