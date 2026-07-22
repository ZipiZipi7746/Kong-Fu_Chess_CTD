"""Centralized networking configuration - the single place "where the
server lives" is defined. server_main.py imports this to bind; every
client (reference_client.py, network_gui_main.py) imports it to dial -
previously these were three independent hardcoded copies of the same
host/port that could silently drift apart.
"""

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8765
SERVER_URL = f"ws://{DEFAULT_HOST}:{DEFAULT_PORT}"
