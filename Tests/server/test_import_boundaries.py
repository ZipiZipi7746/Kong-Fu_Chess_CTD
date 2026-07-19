"""Part 15, acceptance criterion 8 / Part 4's forbidden-imports rule: the
WebSocket gateway must never import the domain layers directly - only
through application/. Checked by parsing the actual source text rather
than the live import graph, so this fails loudly on a violation instead
of only failing transitively deep inside an unrelated test."""

import ast
from pathlib import Path

GATEWAY_PATH = (
    Path(__file__).resolve().parents[2]
    / "kungfu_chess" / "server" / "websocket_gateway.py"
)

FORBIDDEN_MODULE_PREFIXES = (
    "kungfu_chess.model",
    "kungfu_chess.rules",
    "kungfu_chess.realtime",
)


def _imported_module_names(source):
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


class TestWebSocketGatewayImportBoundaries:
    def test_never_imports_model_rules_or_realtime_directly(self):
        source = GATEWAY_PATH.read_text(encoding="utf-8")
        imported = _imported_module_names(source)

        violations = [
            name for name in imported
            if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_MODULE_PREFIXES)
        ]

        assert violations == [], (
            f"server/websocket_gateway.py must only reach the domain layers "
            f"through application/, but imports: {violations}")
