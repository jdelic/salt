import time

import packaging.version
import psutil

## DGM import pytest
from pytestskipmarkers.utils import platform

## DGM @pytest.fixture
## DGM def salt_systemd_setup(
## DGM     salt_call_cli,
## DGM     install_salt,
## DGM ):
## DGM     """
## DGM     Fixture to set systemd for salt packages to enabled and active
## DGM     Note: assumes Salt packages already installed
## DGM     """
## DGM     # ensure known state, enabled and active
## DGM     test_list = ["salt-minion"]
## DGM     for test_item in test_list:
## DGM         test_cmd = f"systemctl enable {test_item}"
## DGM         ret = salt_call_cli.run("--local", "cmd.run", test_cmd)
## DGM         assert ret.returncode == 0
## DGM
## DGM         test_cmd = f"systemctl restart {test_item}"
## DGM         ret = salt_call_cli.run("--local", "cmd.run", test_cmd)
## DGM         assert ret.returncode == 0
## DGM
## DGM         time.sleep(10)
## DGM
## DGM         test_cmd = f"systemctl show -p UnitFileState {test_item}"
## DGM         ret = salt_call_cli.run("--local", "cmd.run", test_cmd)
## DGM         test_enabled = ret.stdout.strip().split("=")[1].split('"')[0].strip()
## DGM         print(
## DGM             f"DGM salt_systemd_setup UnitFileState '{test_item}', test_enabled '{test_enabled}', ret '{ret}'",
## DGM             flush=True,
## DGM         )
## DGM         assert ret.returncode == 0


def _get_running_named_salt_pid(process_name):

    # need to check all of command line for salt-minion, salt-master, for example: salt-minion
    #
    # Linux: psutil process name only returning first part of the command '/opt/saltstack/'
    # Linux: ['/opt/saltstack/salt/bin/python3.10 /usr/bin/salt-minion MultiMinionProcessManager MinionProcessManager']
    #
    # MacOS: psutil process name only returning last part of the command '/opt/salt/bin/python3.10', that is 'python3.10'
    # MacOS: ['/opt/salt/bin/python3.10 /opt/salt/salt-minion', '']

    pids = []
    for proc in psutil.process_iter():
        cmdl_strg = " ".join(str(element) for element in proc.cmdline())
        print(
            f"DGM _get_running_named_salt_pid, process_name '{process_name}', command line string '{cmdl_strg}', proc cmdline '{proc.cmdline()}'",
            flush=True,
        )
        if process_name in cmdl_strg:
            pids.append(proc.pid)

    return pids


## DGM def test_salt_downgrade_minion(salt_call_cli, install_salt, salt_systemd_setup):
def test_salt_downgrade_minion(salt_call_cli, install_salt):
    """
    Test an downgrade of Salt Minion.
    """
    print(
        f"DGM test_salt_downgrade_minion, install_salt prev_version, '{install_salt.prev_version}'",
        flush=True,
    )
    is_downgrade_to_relenv = packaging.version.parse(
        install_salt.prev_version
    ) >= packaging.version.parse("3006.0")

    print(
        f"DGM test_salt_downgrade_minion, install_salt prev_version, '{install_salt.prev_version}', is_downgrade_to_relenv '{is_downgrade_to_relenv}'",
        flush=True,
    )
    if is_downgrade_to_relenv:
        original_py_version = install_salt.package_python_version()

    # Verify current install version is setup correctly and works
    ret = salt_call_cli.run("test.version")
    assert ret.returncode == 0
    assert packaging.version.parse(ret.data) == packaging.version.parse(
        install_salt.artifact_version
    )

    # Test pip install before a downgrade
    dep = "PyGithub==1.56.0"
    install = salt_call_cli.run("--local", "pip.install", dep)
    assert install.returncode == 0

    # Verify we can use the module dependent on the installed package
    repo = "https://github.com/saltstack/salt.git"
    use_lib = salt_call_cli.run("--local", "github.get_repo_info", repo)
    assert "Authentication information could" in use_lib.stderr

    # Verify there is a running minion by getting its PID
    salt_name = "salt"
    if platform.is_windows():
        process_name = "salt-minion.exe"
    else:
        process_name = "salt-minion"

    old_minion_pids = _get_running_named_salt_pid(process_name)
    print(
        f"DGM test_salt_downgrade_minion, old_minion_pids  '{old_minion_pids}'",
        flush=True,
    )
    assert old_minion_pids

    # Downgrade Salt to the previous version and test
    install_salt.install(downgrade=True)

    time.sleep(60)  # give it some time

    # earlier versions od Salt 3006.x did not preserve systemd settings, hence ensure restart
    # pylint: disable=pointless-statement
    print("DGM test_salt_downgrade_minion, post-downgraded", flush=True)
    ## DGM salt_systemd_setup
    # ensure known state, enabled and active
    test_list = ["salt-minion"]
    for test_item in test_list:
        test_cmd = f"systemctl enable {test_item}"
        ret = salt_call_cli.run("--local", "cmd.run", test_cmd)
        assert ret.returncode == 0

        test_cmd = f"systemctl restart {test_item}"
        ret = salt_call_cli.run("--local", "cmd.run", test_cmd)
        assert ret.returncode == 0

        time.sleep(10)

        test_cmd = f"systemctl show -p UnitFileState {test_item}"
        ret = salt_call_cli.run("--local", "cmd.run", test_cmd)
        test_enabled = ret.stdout.strip().split("=")[1].split('"')[0].strip()
        print(
            f"DGM salt_systemd_setup UnitFileState '{test_item}', test_enabled '{test_enabled}', ret '{ret}'",
            flush=True,
        )
        assert ret.returncode == 0
    print("DGM test_salt_downgrade_minion, post-salt_systemd_setup", flush=True)

    time.sleep(60)  # give it some time

    print("DGM test_salt_downgrade_minion, done-downgraded", flush=True)

    # Verify there is a new running minion by getting its PID and comparing it
    # with the PID from before the upgrade
    new_minion_pids = _get_running_named_salt_pid(process_name)
    print(
        f"DGM test_salt_downgrade_minion, new_minion_pids  '{new_minion_pids}'",
        flush=True,
    )
    assert new_minion_pids
    assert new_minion_pids != old_minion_pids

    bin_file = "salt"
    if platform.is_windows():
        if not is_downgrade_to_relenv:
            bin_file = install_salt.install_dir / "salt-call.bat"
        else:
            bin_file = install_salt.install_dir / "salt-call.exe"
    elif platform.is_darwin() and install_salt.classic:
        bin_file = install_salt.bin_dir / "salt-call"

    ret = install_salt.proc.run(bin_file, "--version")
    assert ret.returncode == 0
    assert packaging.version.parse(
        ret.stdout.strip().split()[1]
    ) < packaging.version.parse(install_salt.artifact_version)

    if is_downgrade_to_relenv:
        new_py_version = install_salt.package_python_version()
        if new_py_version == original_py_version:
            # test pip install after a downgrade
            use_lib = salt_call_cli.run("--local", "github.get_repo_info", repo)
            assert "Authentication information could" in use_lib.stderr
