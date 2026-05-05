"""Shortcut generator tests — Haiku generation, compilation, self-repair, endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


# --- Unit tests for shortcut_gen module ---


class TestGeneratedShortcut:
    def test_safe_name_basic(self):
        from app.shortcut_gen import GeneratedShortcut
        s = GeneratedShortcut(id="abc", name="Check My Plex", description="test")
        assert s.safe_name == "check-my-plex"

    def test_safe_name_special_chars(self):
        from app.shortcut_gen import GeneratedShortcut
        s = GeneratedShortcut(id="abc", name="What's the Weather?!", description="test")
        assert "?" not in s.safe_name
        assert "'" not in s.safe_name

    def test_safe_name_long(self):
        from app.shortcut_gen import GeneratedShortcut
        s = GeneratedShortcut(id="abc", name="a " * 100, description="test")
        assert len(s.safe_name) <= 50

    def test_cherri_path(self):
        from app.shortcut_gen import GeneratedShortcut, OUTPUT_DIR
        s = GeneratedShortcut(id="abc", name="Test", description="test")
        assert s.cherri_path == OUTPUT_DIR / "test.cherri"

    def test_shortcut_path(self):
        from app.shortcut_gen import GeneratedShortcut, OUTPUT_DIR
        s = GeneratedShortcut(id="abc", name="Test", description="test")
        assert s.shortcut_path == OUTPUT_DIR / "test.shortcut"


class TestRunHaiku:
    @patch("app.shortcut_gen.asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_strips_markdown_fences(self, mock_exec):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(
            b"```cherri\n#define name Test\n#define glyph gear\n```",
            b"",
        ))
        mock_exec.return_value = mock_proc

        from app.shortcut_gen import _run_haiku
        result = await _run_haiku("make a test shortcut")
        assert result.startswith("#define name Test")
        assert "```" not in result

    @patch("app.shortcut_gen.asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_raises_on_cli_failure(self, mock_exec):
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error: not found"))
        mock_exec.return_value = mock_proc

        from app.shortcut_gen import _run_haiku
        with pytest.raises(RuntimeError, match="Claude CLI failed"):
            await _run_haiku("test")

    @patch("app.shortcut_gen.asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_clean_output_no_fences(self, mock_exec):
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(
            b"#define name Clean\n#define glyph star\n",
            b"",
        ))
        mock_exec.return_value = mock_proc

        from app.shortcut_gen import _run_haiku
        result = await _run_haiku("make a clean shortcut")
        assert result == "#define name Clean\n#define glyph star"


class TestCompileCherri:
    async def test_missing_cherri_binary(self, tmp_path):
        from app.shortcut_gen import GeneratedShortcut, _compile_cherri
        import app.shortcut_gen as mod

        # Point to nonexistent binary
        original = mod.CHERRI_BIN
        mod.CHERRI_BIN = tmp_path / "nonexistent"

        s = GeneratedShortcut(id="abc", name="Test", description="test")
        # Write a fake cherri file
        s.cherri_path.parent.mkdir(parents=True, exist_ok=True)
        s.cherri_path.write_text("#define name Test")

        result = await _compile_cherri(s)
        assert result is False
        assert "not found" in s.compile_error

        mod.CHERRI_BIN = original

    async def test_missing_source_file(self):
        from app.shortcut_gen import GeneratedShortcut, _compile_cherri
        s = GeneratedShortcut(id="abc", name="nonexistent-file", description="test")
        result = await _compile_cherri(s)
        assert result is False
        assert "not found" in s.compile_error

    async def test_safety_check_directory(self, tmp_path):
        """Verify we refuse to compile if the target resolves to a directory."""
        from app.shortcut_gen import GeneratedShortcut, _compile_cherri
        import app.shortcut_gen as mod

        # Create a directory with the same name as the expected .cherri file
        original_dir = mod.OUTPUT_DIR
        mod.OUTPUT_DIR = tmp_path

        s = GeneratedShortcut(id="abc", name="Test", description="test")
        # Make the cherri_path point to a directory
        s.cherri_path.mkdir(parents=True, exist_ok=True)

        # _compile_cherri should check .is_file() and fail
        result = await _compile_cherri(s)
        assert result is False

        mod.OUTPUT_DIR = original_dir


class TestGenerateShortcut:
    @patch("app.shortcut_gen._compile_cherri", new_callable=AsyncMock)
    @patch("app.shortcut_gen._run_haiku", new_callable=AsyncMock)
    async def test_happy_path(self, mock_haiku, mock_compile):
        mock_haiku.return_value = "#define name Test\n#define glyph gear\n#define color blue"
        mock_compile.return_value = True

        from app.shortcut_gen import generate_shortcut, OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        s = await generate_shortcut("make a test shortcut")
        assert s.status == "done"
        assert s.cherri_source.startswith("#define")

    @patch("app.shortcut_gen._compile_cherri", new_callable=AsyncMock)
    @patch("app.shortcut_gen._run_haiku", new_callable=AsyncMock)
    async def test_compile_fail_then_repair_succeeds(self, mock_haiku, mock_compile):
        mock_haiku.side_effect = [
            "#define name Broken",
            "#define name Fixed\n#define glyph gear",
        ]
        mock_compile.side_effect = [False, True]

        from app.shortcut_gen import generate_shortcut, OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        s = await generate_shortcut("make a broken shortcut")
        assert s.status == "done"
        assert "Fixed" in s.cherri_source

    @patch("app.shortcut_gen._compile_cherri", new_callable=AsyncMock)
    @patch("app.shortcut_gen._run_haiku", new_callable=AsyncMock)
    async def test_compile_fail_repair_also_fails(self, mock_haiku, mock_compile):
        mock_haiku.side_effect = [
            "#define name Broken",
            "#define name StillBroken",
        ]
        mock_compile.side_effect = [False, False]

        from app.shortcut_gen import generate_shortcut, OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        s = await generate_shortcut("impossible shortcut")
        assert s.status == "failed"

    @patch("app.shortcut_gen._run_haiku", new_callable=AsyncMock)
    async def test_haiku_generation_fails(self, mock_haiku):
        mock_haiku.side_effect = RuntimeError("CLI not found")

        from app.shortcut_gen import generate_shortcut, OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        s = await generate_shortcut("test")
        assert s.status == "failed"
        assert "Haiku generation failed" in s.compile_error


# --- API endpoint tests ---


async def test_generate_endpoint_returns_202(client, auth_headers):
    with patch("app.main._run_shortcut_gen", new_callable=AsyncMock):
        resp = await client.post(
            "/v1/shortcuts/generate",
            json={"description": "check my plex unwatched count"},
            headers=auth_headers,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "shortcut_id" in data
    assert data["status"] == "generating"


async def test_generate_endpoint_requires_auth(client):
    resp = await client.post("/v1/shortcuts/generate", json={"description": "test"})
    assert resp.status_code in (401, 403)


async def test_generate_endpoint_missing_description(client, auth_headers):
    resp = await client.post("/v1/shortcuts/generate", json={}, headers=auth_headers)
    assert resp.status_code == 422


async def test_shortcut_not_found(client, auth_headers):
    resp = await client.get("/v1/shortcuts/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


async def test_shortcut_detail_returns_fields(client, auth_headers):
    from app.shortcut_gen import GeneratedShortcut, _shortcuts
    s = GeneratedShortcut(id="test123", name="Test", description="a test", status="done", cherri_source="#define name Test")
    _shortcuts["test123"] = s

    resp = await client.get("/v1/shortcuts/test123", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test123"
    assert data["status"] == "done"
    assert data["cherri_source"].startswith("#define")

    del _shortcuts["test123"]


async def test_download_not_ready(client, auth_headers):
    from app.shortcut_gen import GeneratedShortcut, _shortcuts
    s = GeneratedShortcut(id="dl-test", name="NotReady", description="test", status="generating")
    _shortcuts["dl-test"] = s

    resp = await client.get("/v1/shortcuts/dl-test/download", headers=auth_headers)
    assert resp.status_code == 400

    del _shortcuts["dl-test"]


async def test_download_not_found(client, auth_headers):
    resp = await client.get("/v1/shortcuts/nope/download", headers=auth_headers)
    assert resp.status_code == 404


async def test_list_shortcuts_empty(client, auth_headers):
    from app.shortcut_gen import _shortcuts
    _shortcuts.clear()
    resp = await client.get("/v1/shortcuts", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["shortcuts"] == []


async def test_list_shortcuts_with_entries(client, auth_headers):
    from app.shortcut_gen import GeneratedShortcut, _shortcuts
    _shortcuts.clear()
    _shortcuts["a"] = GeneratedShortcut(id="a", name="Alpha", description="test", status="done")
    _shortcuts["b"] = GeneratedShortcut(id="b", name="Beta", description="test2", status="failed")

    resp = await client.get("/v1/shortcuts", headers=auth_headers)
    data = resp.json()
    assert len(data["shortcuts"]) == 2

    _shortcuts.clear()


async def test_list_shortcuts_requires_auth(client):
    resp = await client.get("/v1/shortcuts")
    assert resp.status_code in (401, 403)
