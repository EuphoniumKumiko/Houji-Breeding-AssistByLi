from __future__ import annotations

from pathlib import Path

from yuxi.agents.toolkits.breeding.tools import (
    TARGET_GENE,
    _guard_advice,
    smoke_flavonoid_breeding_advice,
)


def test_smoke_tool_missing_data_dir_returns_error(tmp_path: Path):
    result = smoke_flavonoid_breeding_advice.invoke({
        "data_dir": str(tmp_path / "missing"),
        "out_dir": str(tmp_path / "out"),
        "run_transcriptome": False,
    })

    assert result["status"] == "error"
    assert "data_dir does not exist" in result["error"]
    assert result["artifacts"] == []


def test_smoke_advice_guard_required_terms_pass():
    advice = "\n".join([
        f"核心基因：{TARGET_GENE}",
        "建议扩大群体并检测黄酮含量。",
        "真实 DOI：待文献检索补充",
        "引用原文：待文献检索补充",
    ])

    result = _guard_advice(advice)

    assert result["passed"] is True
    assert result["checks"]["contains_target_gene"] is True
    assert result["checks"]["contains_population"] is True
    assert result["checks"]["contains_flavonoid"] is True


def test_smoke_advice_guard_rejects_missing_required_terms():
    result = _guard_advice("候选建议：后续验证。")

    assert result["passed"] is False
    assert any(TARGET_GENE in err for err in result["errors"])
    assert any("群体" in err for err in result["errors"])
    assert any("黄酮" in err for err in result["errors"])


def test_smoke_guard_does_not_fabricate_doi_placeholder():
    advice = "\n".join([
        f"{TARGET_GENE} 可作为黄酮相关候选线索。",
        "后续需要在群体中验证。",
        "真实 DOI：待文献检索补充",
        "引用原文：待文献检索补充",
    ])

    result = _guard_advice(advice)

    assert result["passed"] is True
    assert result["unsupported_dois"] == []
    assert result["checks"]["has_literature_placeholder"] is True


def test_smoke_guard_allows_explicit_smoke_boundary():
    advice = "\n".join([
        f"{TARGET_GENE} 是黄酮相关候选线索。",
        "后续需要在群体中验证。",
        "本结果来自 smoke 测试流程，不是生产级全基因组结论。",
        "真实 DOI：待文献检索补充",
        "引用原文：待文献检索补充",
    ])

    result = _guard_advice(advice)

    assert result["passed"] is True
    assert result["checks"]["claims_production_grade"] is False


def test_smoke_guard_rejects_boundary_overclaims():
    advice = "\n".join([
        f"{TARGET_GENE} 是黄酮相关候选基因。",
        "已完成群体验证，已完成湿实验验证。",
        "真实 DOI：待文献检索补充",
        "引用原文：待文献检索补充",
    ])

    result = _guard_advice(advice)

    assert result["passed"] is False
    assert result["checks"]["claims_population_validation_completed"] is True
    assert result["checks"]["claims_wet_lab_completed"] is True
