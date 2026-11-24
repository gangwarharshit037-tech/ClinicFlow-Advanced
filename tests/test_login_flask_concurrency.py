import os
import subprocess
import sys


def test_success_preserves_overlapping_failed_login(tmp_path):
    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(tmp_path / "concurrent_login.db"),
        "ADMIN_PASSWORD": "ClinicFlowTestPassword2026!",
        "SECRET_KEY": "clinicflow-concurrent-login-test-key",
        "PUBLIC_DEMO_MODE": "false",
        "LIVE_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
    })

    code = r"""
import threading
from unittest.mock import patch
import app

client_ip = "192.0.2.10"
correct = "ClinicFlowTestPassword2026!"
entered = threading.Event()
release = threading.Event()
original_compare = app.hmac.compare_digest
results = {}


def controlled_compare(password, configured):
    if password == correct:
        entered.set()
        assert release.wait(timeout=10), "Timed out waiting for release"
    return original_compare(password, configured)


def successful_login():
    with app.app.test_client() as client:
        response = client.post(
            "/admin/login",
            json={"password": correct},
            environ_overrides={"REMOTE_ADDR": client_ip},
        )
        results["success"] = response.status_code


with patch.object(app.hmac, "compare_digest", side_effect=controlled_compare):
    worker = threading.Thread(target=successful_login)
    worker.start()

    try:
        assert entered.wait(timeout=10), "Successful login did not start"

        with app.app.test_client() as client:
            response = client.post(
                "/admin/login",
                json={"password": "IncorrectPassword123!"},
                environ_overrides={"REMOTE_ADDR": client_ip},
            )
            results["failure"] = response.status_code
    finally:
        release.set()
        worker.join(timeout=10)

assert not worker.is_alive(), "Login thread did not finish"
assert results["success"] == 200, results
assert results["failure"] == 401, results

# The failed request finished before the successful one.
# A successful login clears completed failures by design.
# Verify no in-flight reservations remain.
assert app.login_limiter._inflight.get(client_ip) is None

print("PASSED: Flask overlapping login requests")
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        "STDOUT:\n" + result.stdout
        + "\nSTDERR:\n" + result.stderr
    )



def test_failed_login_finishing_after_success_is_recorded(tmp_path):
    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(tmp_path / "opposite_order.db"),
        "ADMIN_PASSWORD": "ClinicFlowTestPassword2026!",
        "SECRET_KEY": "clinicflow-opposite-order-test-key",
        "PUBLIC_DEMO_MODE": "false",
        "LIVE_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
    })

    code = r"""
import threading
from unittest.mock import patch
import app

client_ip = "192.0.2.10"
correct = "ClinicFlowTestPassword2026!"
wrong = "IncorrectPassword123!"
entered = threading.Event()
release = threading.Event()
original_compare = app.hmac.compare_digest
results = {}


def controlled_compare(password, configured):
    if password == wrong:
        entered.set()
        assert release.wait(timeout=10), "Timed out waiting for release"
    return original_compare(password, configured)


def failed_login():
    with app.app.test_client() as client:
        response = client.post(
            "/admin/login",
            json={"password": wrong},
            environ_overrides={"REMOTE_ADDR": client_ip},
        )
        results["failure"] = response.status_code


with patch.object(app.hmac, "compare_digest", side_effect=controlled_compare):
    worker = threading.Thread(target=failed_login)
    worker.start()

    try:
        assert entered.wait(timeout=10), "Failed login did not start"

        with app.app.test_client() as client:
            response = client.post(
                "/admin/login",
                json={"password": correct},
                environ_overrides={"REMOTE_ADDR": client_ip},
            )
            results["success"] = response.status_code
    finally:
        release.set()
        worker.join(timeout=10)

assert not worker.is_alive(), "Login thread did not finish"
assert results["success"] == 200, results
assert results["failure"] == 401, results

# The failure finished after the success and must remain recorded.
assert len(app.login_limiter._attempts.get(client_ip, [])) == 1
assert app.login_limiter._inflight.get(client_ip) is None

print("PASSED: Failure after success remains recorded")
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        "STDOUT:\\n" + result.stdout
        + "\\nSTDERR:\\n" + result.stderr
    )
