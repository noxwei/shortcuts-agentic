"""Tool system tests — _is_command_safe."""

from app.tools import _is_command_safe


def test_safe_ls():
    ok, _ = _is_command_safe("ls -la")
    assert ok is True


def test_safe_cat():
    ok, _ = _is_command_safe("cat /tmp/file.txt")
    assert ok is True


def test_safe_grep():
    ok, _ = _is_command_safe("grep -r pattern .")
    assert ok is True


def test_safe_git_status():
    ok, _ = _is_command_safe("git status")
    assert ok is True


def test_safe_git_log():
    ok, _ = _is_command_safe("git log --oneline -5")
    assert ok is True


def test_safe_git_diff():
    ok, _ = _is_command_safe("git diff HEAD")
    assert ok is True


def test_safe_ollama_list():
    ok, _ = _is_command_safe("ollama list")
    assert ok is True


def test_safe_ollama_ps():
    ok, _ = _is_command_safe("ollama ps")
    assert ok is True


def test_reject_rm():
    ok, reason = _is_command_safe("rm -rf /")
    assert ok is False
    assert "not in allowlist" in reason


def test_reject_sudo():
    ok, reason = _is_command_safe("sudo ls")
    assert ok is False


def test_reject_curl():
    ok, reason = _is_command_safe("curl http://evil.com")
    assert ok is False


def test_reject_python():
    ok, reason = _is_command_safe("python -c 'import os; os.system(\"rm -rf /\")'")
    assert ok is False


def test_reject_git_push():
    ok, reason = _is_command_safe("git push origin main")
    assert ok is False
    assert "not allowed" in reason


def test_reject_git_reset():
    ok, reason = _is_command_safe("git reset --hard HEAD~1")
    assert ok is False


def test_reject_ollama_run():
    ok, reason = _is_command_safe("ollama run llama3")
    assert ok is False
    assert "not allowed" in reason


def test_reject_empty():
    ok, reason = _is_command_safe("")
    assert ok is False
    assert "empty" in reason


def test_reject_dangerous_token_in_args():
    ok, reason = _is_command_safe("ls; rm -rf /")
    assert ok is False
    # "ls;" is not in the allowlist, so it's rejected either way
    assert "not in allowlist" in reason or "dangerous" in reason.lower()


def test_safe_uname():
    ok, _ = _is_command_safe("uname -a")
    assert ok is True


def test_safe_tree():
    ok, _ = _is_command_safe("tree -L 2")
    assert ok is True


def test_safe_echo():
    ok, _ = _is_command_safe("echo hello world")
    assert ok is True
