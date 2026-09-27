import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "plugin.video.appi" / "resources" / "lib" / "subtitle_service.py"


def test_service_startup_avoids_settings_migration_and_eager_overlay():
    source = SERVICE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # The Kodi-startup service must not rewrite add-on settings during startup.
    assert "languages.migrate_preferences(ADDON)" not in source

    run_node = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run"
    )
    while_index = next(
        index for index, node in enumerate(run_node.body)
        if isinstance(node, ast.While)
    )
    startup_statements = run_node.body[:while_index]
    startup_text = "\n".join(
        ast.unparse(node) for node in startup_statements
    )

    # Creating Kodi GUI controls is deferred until buffered playback is active.
    assert "BufferOverlay()" not in startup_text
