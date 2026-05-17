from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from yuxi.agents.toolkits.registry import tool

DEFAULT_DATA_DIR = "/mnt/yuxi-breeding-data/smoke_test_minimal"
DEFAULT_OUT_DIR = "/tmp/yuxi_runs/smoke_flavonoid_breeding_advice"
TARGET_GENE = "Si9g037800"

REQUIRED_FILES = {
    "genome_fa": "genome.fa",
    "genome_gff": "genome.gff",
    "annotation": "xiaomi_T2T_Annotation.smoke_genes.txt",
    "sample_map": "sampleName_clientId.txt",
    "metabolome": "metabolome_raw_3372.tsv",
    "pipeline_script": "run_smoke_de_pipeline.sh",
}
VERIFIED_LITERATURE_EVIDENCE_FILE = "verified_literature_evidence.tsv"

DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
POPULATION_VALIDATED_PATTERN = re.compile(
    r"(?:已完成|完成|completed|validated).{0,20}(?:群体|population).{0,20}(?:验证|validation)|"
    r"(?:群体|population).{0,20}(?:验证|validation).{0,20}(?:已完成|完成|completed|validated)",
    re.IGNORECASE,
)
WET_LAB_VALIDATED_PATTERN = re.compile(
    r"(?:已完成|完成|completed|validated).{0,20}(?:湿实验|wet[- ]?lab)|"
    r"(?:湿实验|wet[- ]?lab).{0,20}(?:已完成|完成|completed|validated)",
    re.IGNORECASE,
)
PRODUCTION_CLAIM_PATTERN = re.compile(
    r"(?:生产级|production[- ]?grade|全基因组结论|whole[- ]?genome conclusion|可直接用于育种)",
    re.IGNORECASE,
)


class SmokeFlavonoidBreedingAdviceInput(BaseModel):
    """Input schema for the smoke flavonoid breeding-advice tool."""

    data_dir: str = Field(default=DEFAULT_DATA_DIR, description="Smoke test data directory.")
    trait: str = Field(default="黄酮相关", description="Trait focus for the breeding advice.")
    out_dir: str = Field(default=DEFAULT_OUT_DIR, description="Directory for run outputs and artifacts.")
    run_transcriptome: bool = Field(default=True, description="Whether to run run_smoke_de_pipeline.sh.")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _validate_inputs(data_dir: Path) -> tuple[dict[str, Path], list[str]]:
    paths = {name: data_dir / rel for name, rel in REQUIRED_FILES.items()}
    missing = [str(path) for path in paths.values() if not path.exists()]

    fq_dir = data_dir / "fq"
    fastqs = sorted(fq_dir.glob("*.fq.gz")) if fq_dir.exists() else []
    if not fastqs:
        fastqs = sorted(data_dir.glob("*.fq.gz"))
    if not fastqs:
        missing.append(str(fq_dir / "*.fq.gz"))

    paths["fq_dir"] = fq_dir
    return paths, missing


def _resolve_smoke_data_dir(data_dir: Path) -> Path:
    """Resolve one common tarball layout: data_dir/single_payload_dir/files."""
    _, missing = _validate_inputs(data_dir)
    if not missing:
        return data_dir

    child_dirs = [path for path in data_dir.iterdir() if path.is_dir()]
    if len(child_dirs) != 1:
        return data_dir

    child = child_dirs[0]
    _, child_missing = _validate_inputs(child)
    if not child_missing:
        return child
    return data_dir


def _find_significant_de_genes(data_dir: Path, out_dir: Path) -> Path | None:
    candidates = [
        data_dir / "significant_de_genes.tsv",
        out_dir / "significant_de_genes.tsv",
    ]
    for base in (data_dir, out_dir):
        candidates.extend(sorted(base.rglob("significant_de_genes.tsv")) if base.exists() else [])

    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _load_verified_literature_evidence(data_dir: Path, trait: str) -> list[dict[str, str]]:
    evidence_path = data_dir / VERIFIED_LITERATURE_EVIDENCE_FILE
    if not evidence_path.exists():
        return []

    entries: list[dict[str, str]] = []
    with evidence_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            gene_id = (row.get("gene_id") or "").strip()
            trait_value = (row.get("trait") or "").strip()
            doi = (row.get("doi") or "").strip()
            quoted_sentence = (row.get("quoted_sentence") or "").strip()
            if gene_id != TARGET_GENE:
                continue
            if "黄酮" not in trait_value and "黄酮" not in trait:
                continue
            if not doi or not quoted_sentence:
                continue
            entries.append(
                {
                    "gene_id": gene_id,
                    "trait": trait_value,
                    "doi": doi,
                    "title": (row.get("title") or "").strip(),
                    "quoted_sentence": quoted_sentence,
                    "source": (row.get("source") or "").strip(),
                    "evidence_level": (row.get("evidence_level") or "").strip(),
                    "note": (row.get("note") or "").strip(),
                }
            )
    return entries


def _run_transcriptome_pipeline(data_dir: Path, out_dir: Path, run_log: Path) -> dict[str, Any]:
    script = data_dir / REQUIRED_FILES["pipeline_script"]
    de_out_dir = out_dir / "de_pipeline_out"
    command = [
        "bash",
        str(script),
        "--fa",
        "genome.fa",
        "--gff",
        "genome.gff",
        "--fq-dir",
        "fq",
        "--sample-map",
        "sampleName_clientId.txt",
        "--outdir",
        str(de_out_dir),
        "--threads",
        "8",
    ]
    result: dict[str, Any] = {
        "attempted": True,
        "returncode": None,
        "command": command,
        "stdout_tail": "",
        "stderr_tail": "",
        "error": "",
    }
    try:
        completed = subprocess.run(
            command,
            cwd=str(data_dir),
            text=True,
            capture_output=True,
            timeout=1800,
            check=False,
        )
        result["returncode"] = completed.returncode
        result["stdout_tail"] = completed.stdout[-4000:]
        result["stderr_tail"] = completed.stderr[-4000:]
        run_log.write_text(
            "\n".join([
                f"command: {' '.join(command)}",
                f"cwd: {data_dir}",
                f"returncode: {completed.returncode}",
                "",
                "=== stdout ===",
                completed.stdout,
                "",
                "=== stderr ===",
                completed.stderr,
            ]),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 - must return structured tool error
        result["error"] = str(exc)
        run_log.write_text(f"Pipeline execution failed before completion: {exc}\n", encoding="utf-8")
    return result


def _lookup_gene_in_text(path: Path, gene_id: str) -> dict[str, Any]:
    matches: list[str] = []
    if not path.exists():
        return {"found": False, "matches": matches}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if gene_id in line:
                matches.append(line.rstrip("\n")[:500])
                if len(matches) >= 5:
                    break
    return {"found": bool(matches), "matches": matches}


def _inspect_metabolome(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "columns": [], "row_count_sampled": 0, "flavonoid_related": False, "matched_terms": []}

    matched_terms: set[str] = set()
    columns: list[str] = []
    sampled_rows = 0
    keywords = ("黄酮", "flavonoid", "flavone", "flavonol", "anthocyan", "isoflav")
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            columns = next(reader)
        except StopIteration:
            columns = []
        header_text = "\t".join(columns).lower()
        for kw in keywords:
            if kw.lower() in header_text:
                matched_terms.add(kw)
        for row in reader:
            sampled_rows += 1
            row_text = "\t".join(row).lower()
            for kw in keywords:
                if kw.lower() in row_text:
                    matched_terms.add(kw)
            if sampled_rows >= 20:
                break

    return {
        "exists": True,
        "columns": columns,
        "row_count_sampled": sampled_rows,
        "flavonoid_related": bool(matched_terms),
        "matched_terms": sorted(matched_terms),
    }


def _inspect_de_support(path: Path | None, gene_id: str) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"available": False, "supports_target_gene": False, "matches": []}

    matches: list[dict[str, str]] = []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames:
            for row in reader:
                if gene_id in "\t".join(str(v) for v in row.values()):
                    matches.append({k: str(v) for k, v in row.items()})
                    if len(matches) >= 5:
                        break
    if not matches:
        text_matches = _lookup_gene_in_text(path, gene_id)["matches"]
        matches = [{"line": line} for line in text_matches]

    return {"available": True, "supports_target_gene": bool(matches), "matches": matches}


def _build_advice_markdown(
    *,
    trait: str,
    significant_de_path: Path | None,
    de_support: dict[str, Any],
    gff_hit: dict[str, Any],
    annotation_hit: dict[str, Any],
    metabolome_summary: dict[str, Any],
    literature_evidence: list[dict[str, str]],
) -> str:
    de_sentence = (
        f"转录组结果文件 `{significant_de_path}` 中检出 {TARGET_GENE}，"
        "可作为 smoke 范式下的候选转录组证据。"
        if de_support.get("supports_target_gene")
        else (
            f"当前 `significant_de_genes.tsv` 未检出 {TARGET_GENE}；"
            "建议仍需如实标记为待进一步验证的候选线索。"
        )
    )
    if not de_support.get("available"):
        de_sentence = "当前尚未获得 `significant_de_genes.tsv`，不能判断转录组是否支持 Si9g037800。"

    ref_sentences = []
    if gff_hit.get("found"):
        ref_sentences.append(f"`genome.gff` 中找到 {TARGET_GENE} 相关记录。")
    else:
        ref_sentences.append(f"`genome.gff` 中未找到 {TARGET_GENE}，不能编造基因位置。")
    if annotation_hit.get("found"):
        ref_sentences.append(f"`xiaomi_T2T_Annotation.smoke_genes.txt` 中找到 {TARGET_GENE} 相关注释记录。")
    else:
        ref_sentences.append(
            f"`xiaomi_T2T_Annotation.smoke_genes.txt` 中未找到 {TARGET_GENE}，不能编造功能注释。"
        )

    metabolome_sentence = (
        "代谢组原始表中出现黄酮相关字段或名称，可作为黄酮相关背景证据，"
        "但不能证明基因到代谢物的因果关系。"
        if metabolome_summary.get("flavonoid_related")
        else (
            "代谢组原始表暂未在表头或前 20 行样本中识别到明确黄酮关键词；"
            "仍只能作为待解析的背景输入。"
        )
    )

    literature_lines = ["## 文献证据"]
    if literature_evidence:
        evidence = literature_evidence[0]
        literature_lines.extend(
            [
                f"真实 DOI：{evidence['doi']}",
                f"引用原文：{evidence['quoted_sentence']}",
            ]
        )
        if evidence.get("title"):
            literature_lines.append(f"文献标题：{evidence['title']}")
        if evidence.get("source"):
            literature_lines.append(f"证据来源：{evidence['source']}")
        if evidence.get("evidence_level"):
            literature_lines.append(f"证据等级：{evidence['evidence_level']}")
    else:
        literature_lines.extend(
            [
                "真实 DOI：待文献检索补充",
                "引用原文：待文献检索补充",
            ]
        )

    return "\n".join([
        "# Smoke 黄酮育种建议",
        "",
        "## 性状目标",
        f"当前性状输入为：{trait}。本轮建议围绕黄酮相关性状展开，"
        "且仅代表 smoke 测试范式下的初步建议。",
        "",
        "## 候选基因与参考信息",
        f"核心关注基因：{TARGET_GENE}。",
        *[f"- {line}" for line in ref_sentences],
        "",
        "## 转录组证据",
        de_sentence,
        "",
        "## 代谢组证据",
        metabolome_sentence,
        "代谢组证据只能作为黄酮相关背景证据，不能写成湿实验验证或因果验证。",
        "",
        *literature_lines,
        "",
        "## 育种建议",
        f"- 将 {TARGET_GENE} 作为黄酮相关候选基因线索之一，"
        "但根据转录组和注释证据强弱动态调整优先级。",
        "- 构建或扩大群体，系统采集基因型数据和黄酮含量表型。",
        "- 在群体中开展候选基因/候选位点与黄酮含量的关联分析。",
        "- 在获得可靠候选变异后，再开展 KASP/CAPS 或其他标记转化与验证设计。",
        "",
        "## 边界",
        "本结果来自 smoke 测试流程，不是生产级全基因组结论。",
        "当前只提出群体构建、表型测定、关联分析和标记验证计划，"
        "这些验证仍待后续执行。",
    ])


def _guard_advice(advice: str, *, known_dois: set[str] | None = None) -> dict[str, Any]:
    known_dois = known_dois or set()
    production_wording = bool(PRODUCTION_CLAIM_PATTERN.search(advice))
    explicit_smoke_boundary = (
        "不是生产级全基因组结论" in advice
        or "非生产级" in advice
        or "not production-grade" in advice.lower()
    )
    checks = {
        "contains_target_gene": TARGET_GENE in advice,
        "contains_population": "群体" in advice,
        "contains_flavonoid": "黄酮" in advice,
        "has_literature_placeholder": (
            "真实 DOI：待文献检索补充" in advice and "引用原文：待文献检索补充" in advice
        ),
        "claims_population_validation_completed": bool(POPULATION_VALIDATED_PATTERN.search(advice)),
        "claims_wet_lab_completed": bool(WET_LAB_VALIDATED_PATTERN.search(advice)),
        "claims_production_grade": production_wording and not explicit_smoke_boundary,
    }

    doi_matches = DOI_PATTERN.findall(advice)
    unsupported_dois = [doi for doi in doi_matches if doi not in known_dois]
    checks["has_unsupported_doi"] = bool(unsupported_dois)

    errors: list[str] = []
    warnings: list[str] = []
    if not checks["contains_target_gene"]:
        errors.append(f"Advice must contain {TARGET_GENE}.")
    if not checks["contains_population"]:
        errors.append("Advice must contain 群体.")
    if not checks["contains_flavonoid"]:
        errors.append("Advice must contain 黄酮.")
    if checks["has_unsupported_doi"]:
        errors.append(f"Advice contains DOI not backed by retrieved literature: {unsupported_dois}.")
    if checks["claims_population_validation_completed"]:
        errors.append("Advice appears to claim completed population validation.")
    if checks["claims_wet_lab_completed"]:
        errors.append("Advice appears to claim completed wet-lab validation.")
    if checks["claims_production_grade"]:
        warnings.append("Advice contains production-grade wording; smoke results must remain preliminary.")
    if not checks["has_literature_placeholder"] and not doi_matches:
        warnings.append("No real DOI found; placeholder should be shown.")

    return {
        "passed": not errors,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "unsupported_dois": unsupported_dois,
    }


@tool(
    category="breeding",
    tags=["育种", "黄酮", "smoke"],
    display_name="Smoke 黄酮育种建议",
    args_schema=SmokeFlavonoidBreedingAdviceInput,
)
def smoke_flavonoid_breeding_advice(
    data_dir: str = DEFAULT_DATA_DIR,
    trait: str = "黄酮相关",
    out_dir: str = DEFAULT_OUT_DIR,
    run_transcriptome: bool = True,
) -> dict[str, Any]:
    """Run the smoke flavonoid breeding-advice workflow and return guarded advice."""
    data_path = Path(data_dir).expanduser().resolve()
    out_path = Path(out_dir).expanduser().resolve()

    if not data_path.exists() or not data_path.is_dir():
        return {
            "status": "error",
            "error": f"data_dir does not exist or is not a directory: {data_path}",
            "advice_markdown": "",
            "significant_de_genes_path": "",
            "metabolome_path": "",
            "guard_result": {"passed": False, "errors": ["missing data_dir"]},
            "artifacts": [],
        }
    data_path = _resolve_smoke_data_dir(data_path)

    paths, missing = _validate_inputs(data_path)
    if missing:
        return {
            "status": "error",
            "error": "Required smoke input files are missing.",
            "missing_inputs": missing,
            "advice_markdown": "",
            "significant_de_genes_path": "",
            "metabolome_path": str(paths["metabolome"]),
            "guard_result": {"passed": False, "errors": ["missing required inputs"]},
            "artifacts": [],
        }

    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001 - return a structured tool error
        return {
            "status": "error",
            "error": f"Cannot create out_dir {out_path}: {exc}",
            "advice_markdown": "",
            "significant_de_genes_path": "",
            "metabolome_path": str(paths["metabolome"]),
            "guard_result": {"passed": False, "errors": ["cannot create out_dir"]},
            "artifacts": [],
        }
    run_log = out_path / "run.log"
    pipeline_result = {"attempted": False, "returncode": None, "stdout_tail": "", "stderr_tail": "", "error": ""}

    significant_de_path = _find_significant_de_genes(data_path, out_path)
    literature_evidence = _load_verified_literature_evidence(data_path, trait)
    known_dois = {entry["doi"] for entry in literature_evidence}
    if run_transcriptome:
        pipeline_result = _run_transcriptome_pipeline(data_path, out_path, run_log)
        if pipeline_result.get("returncode") != 0:
            status = "error"
        else:
            status = "completed"
        significant_de_path = _find_significant_de_genes(data_path, out_path)
    else:
        status = "completed" if significant_de_path else "error"
        if not run_log.exists():
            run_log.write_text(
                "run_transcriptome=false; existing significant_de_genes.tsv was requested.\n",
                encoding="utf-8",
            )

    if significant_de_path is None:
        advice = _build_advice_markdown(
            trait=trait,
            significant_de_path=None,
            de_support={"available": False, "supports_target_gene": False, "matches": []},
            gff_hit=_lookup_gene_in_text(paths["genome_gff"], TARGET_GENE),
            annotation_hit=_lookup_gene_in_text(paths["annotation"], TARGET_GENE),
            metabolome_summary=_inspect_metabolome(paths["metabolome"]),
            literature_evidence=literature_evidence,
        )
        guard_result = _guard_advice(advice, known_dois=known_dois)
        status = "error"
    else:
        gff_hit = _lookup_gene_in_text(paths["genome_gff"], TARGET_GENE)
        annotation_hit = _lookup_gene_in_text(paths["annotation"], TARGET_GENE)
        metabolome_summary = _inspect_metabolome(paths["metabolome"])
        de_support = _inspect_de_support(significant_de_path, TARGET_GENE)
        advice = _build_advice_markdown(
            trait=trait,
            significant_de_path=significant_de_path,
            de_support=de_support,
            gff_hit=gff_hit,
            annotation_hit=annotation_hit,
            metabolome_summary=metabolome_summary,
            literature_evidence=literature_evidence,
        )
        guard_result = _guard_advice(advice, known_dois=known_dois)

    if not guard_result.get("passed"):
        status = "failed_guard" if status == "completed" else status
    elif guard_result.get("warnings") and status == "completed":
        status = "completed_with_warnings"

    advice_path = out_path / "breeding_advice.md"
    guard_path = out_path / "guard_result.json"
    manifest_path = out_path / "run_manifest.json"
    advice_path.write_text(advice, encoding="utf-8")
    _write_json(guard_path, guard_result)

    artifacts = [
        str(path)
        for path in [significant_de_path, advice_path, guard_path, manifest_path, run_log]
        if path is not None
    ]
    manifest = {
        "tool": "smoke_flavonoid_breeding_advice",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data_dir": str(data_path),
        "trait": trait,
        "run_transcriptome": run_transcriptome,
        "pipeline_result": pipeline_result,
        "significant_de_genes_path": str(significant_de_path) if significant_de_path else "",
        "metabolome_path": str(paths["metabolome"]),
        "artifacts": artifacts,
    }
    _write_json(manifest_path, manifest)

    if significant_de_path and significant_de_path.parent != out_path:
        copied = out_path / "significant_de_genes.tsv"
        if significant_de_path.resolve() != copied.resolve():
            shutil.copy2(significant_de_path, copied)
            significant_de_path = copied
            artifacts[0] = str(copied)
            manifest["significant_de_genes_path"] = str(copied)
            manifest["artifacts"] = artifacts
            _write_json(manifest_path, manifest)

    return {
        "status": status,
        "advice_markdown": advice,
        "significant_de_genes_path": str(significant_de_path) if significant_de_path else "",
        "metabolome_path": str(paths["metabolome"]),
        "guard_result": guard_result,
        "artifacts": artifacts,
    }
