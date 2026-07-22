"""Shared client-side login glue - real I/O, excluded from coverage,
verified by running it (same treatment as reference_client.py). Used by
both reference_client.py and the networked GUI client
(gui/network/network_gui_main.py) so the CLI login flow's wire sequence
(register? -> login -> session token) is written once, not duplicated
per client."""

import json

from kungfu_chess.server import protocol, schemas  # pragma: no cover
from kungfu_chess.server.cli_login_flow import CliLoginFlow  # pragma: no cover


async def _send_and_await(websocket, type_, payload):  # pragma: no cover
    await websocket.send(schemas.encode(schemas.make_envelope(type_, payload)))
    return json.loads(await websocket.recv())


async def perform_login(websocket):  # pragma: no cover
    """Drives CliLoginFlow's username -> password -> authenticated
    sequence over the wire, offering registration for a brand-new
    account. Returns the authenticated flow, or None if the user gave up
    after a failure."""
    flow = CliLoginFlow()
    flow.submit_username(input("Username: ").strip())
    # Plain input(), not getpass.getpass(): on Windows, getpass reads
    # directly from the console (msvcrt) rather than sys.stdin, so it
    # hangs forever under any redirected/piped stdin - unacceptable for a
    # client meant to be scriptable for the acceptance walkthrough.
    flow.submit_password(input("Password: ").strip())

    if input("New account? [y/N]: ").strip().lower().startswith("y"):
        response = await _send_and_await(
            websocket, protocol.REGISTER, {"username": flow.username, "password": flow.password})
        if response["type"] == protocol.ERROR:
            print(f"Registration failed: {response['payload']['code']}")
            return None
        print(f"Registered as {flow.username}.")

    response = await _send_and_await(
        websocket, protocol.LOGIN, {"username": flow.username, "password": flow.password})
    if response["type"] == protocol.ERROR:
        print(f"Login failed: {response['payload']['code']}")
        return None
    flow.mark_authenticated(response["payload"]["session_token"])
    return flow
