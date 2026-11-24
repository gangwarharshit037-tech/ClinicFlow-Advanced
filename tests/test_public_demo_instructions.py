import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "demo_mode, check",
    [
        ("true", "panel"),
        ("false", "panel"),
        ("true", "details"),
        ("false", "details"),
    ],
)
def test_public_demo_instructions(tmp_path, demo_mode, check):
    env = os.environ.copy()

    env.update({
        "DATABASE_PATH": str(tmp_path / "demo_test.db"),
        "PUBLIC_DEMO_MODE": demo_mode,
        "LIVE_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "SECRET_KEY": "demo-instructions-test-secret",
        "ADMIN_PASSWORD": "DemoInstructionsTest2026!",
    })

    code = """
import app

with app.app.test_client() as client:
    response = client.get("/")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    if CHECK == "panel":
        if DEMO_MODE == "true":
            assert 'id="demo-guide"' in html
            assert "Try the ClinicFlow Demo" in html
            assert "Do not enter real personal or medical information" in html
        else:
            assert 'id="demo-guide"' not in html
            assert "Try the ClinicFlow Demo" not in html

    elif CHECK == "details":
        if DEMO_MODE == "true":
            assert 'id="fill-demo"' in html
            assert "Use Demo Details" in html
            assert 'placeholder="Demo Patient"' in html
            assert 'placeholder="+12025550123"' in html
        else:
            assert 'id="fill-demo"' not in html
            assert "Use Demo Details" not in html
            assert 'placeholder="Your full name"' in html
            assert 'placeholder="+919876543210"' in html
"""

    code = (
        "DEMO_MODE = " + repr(demo_mode) + "\n"
        + "CHECK = " + repr(check) + "\n"
        + code
    )

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
