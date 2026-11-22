import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "message, expected",
    [
        ("clinic hours", "Demo clinic hours: 9 AM to 6 PM."),
        ("What are your opening hours?", "Demo clinic hours: 9 AM to 6 PM."),
        ("doctors", "Available doctors:"),
        ("Which doctors are available?", "Available doctors:"),
        ("booking", "Use the demo booking form"),
        ("How can I book an appointment?", "Use the demo booking form"),
        ("cancellation", "Contact the demo clinic receptionist"),
        ("How do I cancel my appointment?", "Contact the demo clinic receptionist"),
        ("", "Please type a question."),
        ("What is the weather?", "Public demo: please ask"),
    ],
)
def test_public_demo_chatbot(tmp_path, message, expected):
    env = os.environ.copy()
    env.update({
        "DATABASE_PATH": str(tmp_path / "chatbot_test.db"),
        "PUBLIC_DEMO_MODE": "true",
        "LIVE_MODE": "false",
        "ENABLE_SCHEDULER": "false",
        "REMINDER_SEND_ENABLED": "false",
        "WHATSAPP_OUTBOUND_ENABLED": "false",
        "WHATSAPP_STATUS_STORAGE_ENABLED": "false",
        "SECRET_KEY": "chatbot-test-secret",
        "ADMIN_PASSWORD": "ChatbotTestPassword2026!",
    })

    code = """
import app

with app.app.test_client() as client:
    response = client.post(
        "/api/chat",
        json={"message": MESSAGE},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert EXPECTED in data["reply"], data
"""

    code = (
        "MESSAGE = " + repr(message) + "\n"
        + "EXPECTED = " + repr(expected) + "\n"
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
