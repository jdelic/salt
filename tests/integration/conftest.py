"""
    tests.integration.conftest
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Integration tests PyTest configuration/fixtures
"""
import pytest


@pytest.fixture(scope="package", autouse=True)
def bridge_pytest_and_runtests(bridge_pytest_and_runtests, salt_master, salt_minion):
    yield bridge_pytest_and_runtests
