"""Policy tests: automated Gemini cannot touch production or existing test files."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("nazaret_autonomous_agent", ROOT/"automation"/"autonomous_agent.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


@pytest.mark.parametrize("path", [
    "src/nazaret_quant/engine.py", "src/nazaret_quant/ledger.py",
    "src/nazaret_quant/strategies.py", "src/nazaret_quant/registry.py",
    "src/nazaret_quant/cli.py", "src/nazaret_quant/data.py",
    "src/nazaret_quant/b3_cotahist.py", "src/nazaret_quant/research.py",
    ".github/workflows/autonomous-research.yml", "automation/autonomous_agent.py",
    "config/hypotheses.yaml", "docs/CONTINUIDADE.md", "docs/STATUS.md",
    "../secrets.txt", "src/nazaret_quant/../engine.py",
    "tests/test_core.py", "tests/test_b3_cotahist.py",
])
def test_sensitive_path_not_editable(path):
    assert not agent.allowed(path)


@pytest.mark.parametrize("path", [
    "src/nazaret_quant/research_blocks.py",
    "src/nazaret_quant/quality_checks.py",
    "tests/test_research_blocks.py",
    "tests/test_quality_checks.py",
    "tests/test_b3_qa_coverage.py",
    "docs/RESEARCH_NOTE_bootstrap.md",
])
def test_research_path_allowed(path):
    assert agent.allowed(path)


def test_code_needs_new_test():
    with pytest.raises(ValueError, match="novos testes"):
        agent.validate({"changes":[
            {"path":"src/nazaret_quant/research_causal.py","content":"def f():\n    return True\n"}
        ]})


def test_cannot_overwrite_existing_test():
    with pytest.raises(ValueError, match="reescrever testes"):
        agent.validate({"changes":[
            {"path":"tests/test_research_policy.py","content":"def test_x():\n    assert True\n"}
        ]})


def test_cannot_write_core_logic_even_with_companion_test():
    with pytest.raises(ValueError, match="proibido"):
        agent.validate({"changes":[
            {"path":"src/nazaret_quant/ledger.py","content":"pass\n"},
            {"path":"tests/test_research_alibi.py","content":"def test_ok():\n    assert True\n"}
        ]})


def test_backslash_separators_denied_even_inside_allowed_name():
    assert not agent.allowed("docs/RESEARCH_NOTE_unsafe\\name.md")
