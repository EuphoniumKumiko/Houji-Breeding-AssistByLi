from __future__ import annotations

import json
from pathlib import Path

from yuxi.agents.toolkits import get_all_tool_instances
from yuxi.agents.toolkits.breeding.tools import (
    TARGET_GENE,
    _guard_advice,
    breeding_advice_generate,
    breeding_literature_evidence,
    breeding_metabolome_prepare,
    breeding_reference_prepare,
    breeding_transcriptome_deg,
    breeding_validation_plan,
    smoke_flavonoid_breeding_advice,
)


def _build_smoke_dir(base: Path) -> Path:
    data_dir = base / "smoke_case"
    (data_dir / "fq").mkdir(parents=True)
    (data_dir / "fq" / "sample1.fq.gz").write_bytes(b"fake-fastq")
    (data_dir / "genome.fa").write_text(">chr1\nATGC\n", encoding="utf-8")
    (data_dir / "genome.gff").write_text(f"chr1\tsrc\tgene\t1\t10\t.\t+\t.\tID={TARGET_GENE}\n", encoding="utf-8")
    (data_dir / "xiaomi_T2T_Annotation.smoke_genes.txt").write_text(
        f"{TARGET_GENE}\tflavonoid candidate\n",
        encoding="utf-8",
    )
    (data_dir / "sampleName_clientId.txt").write_text("sample1\tgroupA\n", encoding="utf-8")
    (data_dir / "run_smoke_de_pipeline.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (data_dir / "metabolome_raw_3372.tsv").write_text(
        "compound\tannotation\tpathway\nquercetin\tflavonoid\t黄酮\n",
        encoding="utf-8",
    )
    (data_dir / "significant_de_genes.tsv").write_text(
        "gene_id\tlog2FC\tpadj\nSi9g037800\t1.8\t0.001\n",
        encoding="utf-8",
    )
    (data_dir / "verified_literature_evidence.tsv").write_text(
        "\t".join([
            "gene_id",
            "trait",
            "doi",
            "title",
            "quoted_sentence",
            "source",
            "evidence_level",
            "note",
        ])
        + "\n"
        + "\t".join([
            TARGET_GENE,
            "黄酮相关",
            "10.3390/life11060578",
            "Comparative Analysis of Flavonoid Metabolites in Foxtail Millet (Setaria italica) with Different Eating Quality",
            "The yellow pigment mainly includes carotenoids (lutein and zeaxanthin) and flavonoids.",
            "publisher",
            "crop_trait_background",
            "谷子黄酮背景证据，不是 Si9g037800 直接功能验证。",
        ])
        + "\n"
        + "\t".join([
            TARGET_GENE,
            "黄酮相关",
            "10.1186/s12864-025-11780-x",
            "Targeted metabolomic and transcriptomic analyses provide insights into flavonoid biosynthesis in the grain of Foxtail millet",
            "Foxtail millet (Setaria italica L.), a traditional Chinese crop, is valued for its rich abundance of health-beneficial compounds (e.g., flavonoids).",
            "publisher",
            "pathway_background",
            "谷子黄酮生物合成背景证据，不是 Si9g037800 直接功能验证。",
        ])
        + "\n",
        encoding="utf-8",
    )
    return data_dir


def test_all_flavonoid_breeding_tools_registered():
    names = {tool.name for tool in get_all_tool_instances()}

    assert {
        "smoke_flavonoid_breeding_advice",
        "breeding_reference_prepare",
        "breeding_transcriptome_deg",
        "breeding_metabolome_prepare",
        "breeding_literature_evidence",
        "breeding_advice_generate",
        "breeding_validation_plan",
    }.issubset(names)


def test_smoke_tool_missing_data_dir_returns_error(tmp_path: Path):
    result = smoke_flavonoid_breeding_advice.invoke({
        "data_dir": str(tmp_path / "missing"),
        "out_dir": str(tmp_path / "out"),
        "run_transcriptome": False,
    })

    assert result["status"] == "error"
    assert "data_dir does not exist" in result["error"]
    assert result["artifacts"] == []


def test_reference_prepare_finds_target_gene(tmp_path: Path):
    data_dir = _build_smoke_dir(tmp_path)

    result = breeding_reference_prepare.invoke({
        "data_dir": str(data_dir),
        "out_dir": str(tmp_path / "reference_out"),
    })

    assert result["status"] == "completed"
    assert result["gene_found_in_gff"] is True
    assert result["gene_found_in_annotation"] is True


def test_transcriptome_deg_run_pipeline_false_reads_existing_result(tmp_path: Path):
    data_dir = _build_smoke_dir(tmp_path)

    result = breeding_transcriptome_deg.invoke({
        "data_dir": str(data_dir),
        "out_dir": str(tmp_path / "transcriptome_out"),
        "run_pipeline": False,
    })

    assert result["status"] == "completed"
    assert result["target_gene_found"] is True
    assert Path(result["significant_de_genes_path"]).exists()


def test_metabolome_prepare_detects_flavonoid_keywords(tmp_path: Path):
    data_dir = _build_smoke_dir(tmp_path)

    result = breeding_metabolome_prepare.invoke({
        "data_dir": str(data_dir),
        "out_dir": str(tmp_path / "metabolome_out"),
    })

    assert result["status"] == "completed"
    assert result["flavonoid_related"] is True
    assert "黄酮" in result["matched_terms"] or "flavonoid" in result["matched_terms"]


def test_literature_evidence_reads_real_doi_and_quote(tmp_path: Path):
    data_dir = _build_smoke_dir(tmp_path)

    result = breeding_literature_evidence.invoke({
        "data_dir": str(data_dir),
        "out_dir": str(tmp_path / "literature_out"),
    })

    assert result["status"] == "completed"
    assert len(result["entries"]) == 2
    assert result["entries"][0]["doi"] == "10.3390/life11060578"
    assert "flavonoids" in result["entries"][0]["quoted_sentence"]


def test_advice_generate_contains_required_terms_and_real_evidence(tmp_path: Path):
    data_dir = _build_smoke_dir(tmp_path)

    result = breeding_advice_generate.invoke({
        "data_dir": str(data_dir),
        "out_dir": str(tmp_path / "advice_out"),
    })

    advice = result["advice_markdown"]
    assert result["status"] in {"completed", "completed_with_warnings"}
    assert TARGET_GENE in advice
    assert "群体" in advice
    assert "黄酮" in advice
    assert "10.3390/life11060578" in advice
    assert "引用原文" in advice
    assert "不是 Si9g037800 直接功能验证" in advice
    assert result["guard_result"]["passed"] is True


def test_validation_plan_contains_population_trait_and_markers(tmp_path: Path):
    result = breeding_validation_plan.invoke({
        "out_dir": str(tmp_path / "validation_out"),
    })

    plan = result["validation_plan"]
    assert result["status"] == "completed"
    assert "群体" in plan
    assert "黄酮" in plan
    assert "SNP/InDel/KASP/CAPS" in plan
    assert "不是已完成的群体验证" in plan


def test_smoke_flavonoid_breeding_advice_old_entrypoint_still_works(tmp_path: Path):
    data_dir = _build_smoke_dir(tmp_path)

    result = smoke_flavonoid_breeding_advice.invoke({
        "data_dir": str(data_dir),
        "out_dir": str(tmp_path / "smoke_out"),
        "run_transcriptome": False,
    })

    advice = result["advice_markdown"]
    assert result["status"] in {"completed", "completed_with_warnings"}
    assert TARGET_GENE in advice
    assert "群体" in advice
    assert "黄酮" in advice
    assert "10.3390/life11060578" in advice
    assert result["guard_result"]["passed"] is True
    guard_path = Path(tmp_path / "smoke_out" / "guard_result.json")
    assert json.loads(guard_path.read_text(encoding="utf-8"))["passed"] is True


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
