"""Part 15, acceptance criterion 8 / Part 4's forbidden-imports rule,
extended by Master Plan v2 Section 5: server/ must never import the
domain layers (model/rules/realtime) or persistence/sqlite directly -
only through application/. Checked by parsing the actual source text
rather than the live import graph, so this fails loudly on a violation
instead of only failing transitively deep inside an unrelated test.
Scans every module under server/ (not just websocket_gateway.py) so new
server modules (auth wiring, matchmaking, rooms) are covered
automatically without a parallel mechanism."""

import ast
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2] / "kungfu_chess" / "server"

GATEWAY_PATH = SERVER_DIR / "websocket_gateway.py"

FORBIDDEN_MODULE_PREFIXES = (
    "kungfu_chess.model",
    "kungfu_chess.rules",
    "kungfu_chess.realtime",
    "kungfu_chess.persistence.sqlite",
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


def _violations(path):
    source = path.read_text(encoding="utf-8")
    imported = _imported_module_names(source)
    return [
        name for name in imported
        if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_MODULE_PREFIXES)
    ]


class TestWebSocketGatewayImportBoundaries:
    def test_never_imports_model_rules_or_realtime_directly(self):
        violations = _violations(GATEWAY_PATH)

        assert violations == [], (
            f"server/websocket_gateway.py must only reach the domain layers "
            f"through application/, but imports: {violations}")


class TestServerPackageImportBoundaries:
    def test_no_server_module_imports_domain_layers_or_sqlite_directly(self):
        offenders = {}
        for path in SERVER_DIR.glob("*.py"):
            violations = _violations(path)
            if violations:
                offenders[path.name] = violations

        assert offenders == {}, (
            f"server/ modules must only reach model/rules/realtime/"
            f"persistence.sqlite through application/, but found: {offenders}")
