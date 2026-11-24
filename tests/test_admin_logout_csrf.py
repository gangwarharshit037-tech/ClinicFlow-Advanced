"""Regression tests for admin logout CSRF protection."""

import os
import subprocess
import sys
import textwrap


def test_admin_logout_csrf_protection():
    script = textwrap.dedent("""
        import os

        os.environ["LIVE_MODE"] = "false"
        os.environ["ENABLE_SCHEDULER"] = "false"
        os.environ["ADMIN_PASSWORD"] = "temporary-local-test-password-2026"

        from app import app

        with app.test_client() as client:
            login = client.post(
                "/admin/login",
                json={"password": "temporary-local-test-password-2026"},
                environ_overrides={"REMOTE_ADDR": "192.0.2.205"},
            )
            assert login.status_code == 200

            missing = client.post("/admin/logout")
            assert missing.status_code == 403
            assert client.get("/admin").status_code == 200

            invalid = client.post(
                "/admin/logout",
                headers={"X-CSRF-Token": "invalid-token"},
            )
            assert invalid.status_code == 403
            assert client.get("/admin").status_code == 200

            with client.session_transaction() as sess:
                csrf = sess["csrf"]

            valid = client.post(
                "/admin/logout",
                headers={"X-CSRF-Token": csrf},
            )
            assert valid.status_code == 200
            assert client.get("/admin", follow_redirects=False).status_code == 302
    """)

    env = os.environ.copy()
    env["LIVE_MODE"] = "false"
    env["ENABLE_SCHEDULER"] = "false"

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, (
        result.stdout + "\n" + result.stderr
    )
