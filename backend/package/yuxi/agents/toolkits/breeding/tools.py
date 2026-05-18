from __future__ import annotations

"""Breeding business tools built on top of YuXi's tool registry.

These tools are not a generic open-source bioinformatics agent. They are
project-specific business wrappers that YuXi Agent Runs can call through the
standard Tool mechanism.

In this smoke workflow, the code validates demo inputs, optionally calls the
senior-provided ``run_smoke_de_pipeline.sh`` script, reads DOI and quoted
sentences from ``verified_literature_evidence.tsv``, and assembles a guarded
breeding advice markdown.
"""

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
VERIFIED_LITERATURE_EVIDENCE_FILE = "verified_literature_evidence.tsv"

REQUIRED_FILES = {
    "genome_fa": "genome.fa",
    "genome_gff": "genome.gff",
    "annotation": "xiaomi_T2T_Annotation.smoke_genes.txt",
    "sample_map": "sampleName_clientId.txt",
    "metabolome": "metabolome_raw_3372.tsv",
    "pipeline_script": "run_smoke_de_pipeline.sh",
}

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
FLAVONOID_KEYWORDS = ("黄酮", "flavonoid", "flavone", "flavonol", "anthocyan", "isoflav")
PIPELINE_DEPENDENCIES = ("hisat2-build", "hisat2", "samtools", "featureCounts", "Rscript")

# 这些输入模型主要服务于 YuXi Tool 调用时的参数约束和扩展管理展示。
# 对老师解释时，可以把它们理解为“每个业务 Tool 对外公开的输入合同”。


class SmokeFlavonoidBreedingAdviceInput(BaseModel):
    data_dir: str = Field(default=DEFAULT_DATA_DIR, description="Smoke test data directory.")
    trait: str = Field(default="黄酮相关", description="Trait focus for the breeding advice.")
    out_dir: str = Field(default=DEFAULT_OUT_DIR, description="Directory for run outputs and artifacts.")
    run_transcriptome: bool = Field(default=True, description="Whether to run run_smoke_de_pipeline.sh.")


class BreedingReferencePrepareInput(BaseModel):
    data_dir: str = Field(default=DEFAULT_DATA_DIR, description="Breeding data directory.")
    genome_fa: str = Field(default="genome.fa", description="Reference genome FASTA path relative to data_dir.")
    genome_gff: str = Field(default="genome.gff", description="Reference genome GFF path relative to data_dir.")
    annotation_txt: str = Field(
        default="xiaomi_T2T_Annotation.smoke_genes.txt",
        description="Annotation TXT path relative to data_dir.",
    )
    out_dir: str = Field(default="/tmp/yuxi_runs/breeding_reference_prepare", description="Output directory.")


class BreedingTranscriptomeDegInput(BaseModel):
    data_dir: str = Field(default=DEFAULT_DATA_DIR, description="Breeding data directory.")
    fq_dir: str = Field(default="fq", description="FASTQ directory relative to data_dir.")
    sample_map: str = Field(default="sampleName_clientId.txt", description="Sample map path relative to data_dir.")
    genome_fa: str = Field(default="genome.fa", description="Reference genome FASTA path relative to data_dir.")
    genome_gff: str = Field(default="genome.gff", description="Reference genome GFF path relative to data_dir.")
    out_dir: str = Field(default="/tmp/yuxi_runs/breeding_transcriptome_deg", description="Output directory.")
    threads: int = Field(default=8, description="Threads for the DEG pipeline.")
    run_pipeline: bool = Field(default=True, description="Whether to execute run_smoke_de_pipeline.sh.")


class BreedingMetabolomePrepareInput(BaseModel):
    data_dir: str = Field(default=DEFAULT_DATA_DIR, description="Breeding data directory.")
    metabolome_tsv: str = Field(
        default="metabolome_raw_3372.tsv",
        description="Metabolome TSV path relative to data_dir.",
    )
    trait: str = Field(default="黄酮相关", description="Trait focus.")
    out_dir: str = Field(default="/tmp/yuxi_runs/breeding_metabolome_prepare", description="Output directory.")


class BreedingLiteratureEvidenceInput(BaseModel):
    data_dir: str = Field(default=DEFAULT_DATA_DIR, description="Breeding data directory.")
    literature_evidence: str = Field(
        default=VERIFIED_LITERATURE_EVIDENCE_FILE,
        description="Literature evidence TSV path relative to data_dir.",
    )
    trait: str = Field(default="黄酮相关", description="Trait focus.")
    gene_id: str = Field(default=TARGET_GENE, description="Candidate gene id.")
    out_dir: str = Field(default="/tmp/yuxi_runs/breeding_literature_evidence", description="Output directory.")


class BreedingAdviceGenerateInput(BaseModel):
    data_dir: str = Field(default=DEFAULT_DATA_DIR, description="Breeding data directory.")
    trait: str = Field(default="黄酮相关", description="Trait focus.")
    reference_manifest: str = Field(default="", description="Optional reference_manifest.json path.")
    transcriptome_manifest: str = Field(default="", description="Optional transcriptome_manifest.json path.")
    metabolome_manifest: str = Field(default="", description="Optional metabolome_manifest.json path.")
    literature_manifest: str = Field(default="", description="Optional literature_manifest.json path.")
    significant_de_genes: str = Field(default="", description="Optional significant_de_genes.tsv path.")
    out_dir: str = Field(default="/tmp/yuxi_runs/breeding_advice_generate", description="Output directory.")


class BreedingValidationPlanInput(BaseModel):
    trait: str = Field(default="黄酮相关", description="Trait focus.")
    gene_id: str = Field(default=TARGET_GENE, description="Candidate gene id.")
    marker_types: str = Field(default="SNP/InDel/KASP/CAPS", description="Marker types for follow-up planning.")
    out_dir: str = Field(default="/tmp/yuxi_runs/breeding_validation_plan", description="Output directory.")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _resolve_smoke_data_dir(data_dir: Path) -> Path:
    if _required_smoke_files(data_dir)[1] == []:
        return data_dir
    if not data_dir.exists():
        return data_dir

    child_dirs = [path for path in data_dir.iterdir() if path.is_dir()]
    if len(child_dirs) != 1:
        return data_dir

    child = child_dirs[0]
    if _required_smoke_files(child)[1] == []:
        return child
    return data_dir


def _required_smoke_files(data_dir: Path) -> tuple[dict[str, Path], list[str]]:
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


def _ensure_data_dir(data_dir: str) -> tuple[Path | None, dict[str, Any] | None]:
    data_path = Path(data_dir).expanduser().resolve()
    if not data_path.exists() or not data_path.is_dir():
        return None, {
            "status": "error",
            "error": f"data_dir does not exist or is not a directory: {data_path}",
            "artifacts": [],
        }
    return _resolve_smoke_data_dir(data_path), None


def _ensure_out_dir(out_dir: str) -> tuple[Path | None, str | None]:
    out_path = Path(out_dir).expanduser().resolve()
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        return None, f"Cannot create out_dir {out_path}: {exc}"
    return out_path, None


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
        return {
            "exists": False,
            "columns": [],
            "sample_rows": [],
            "row_count_sampled": 0,
            "flavonoid_related": False,
            "matched_terms": [],
        }

    matched_terms: set[str] = set()
    columns: list[str] = []
    sample_rows: list[list[str]] = []
    sampled_rows = 0
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            columns = next(reader)
        except StopIteration:
            columns = []
        header_text = "\t".join(columns).lower()
        for keyword in FLAVONOID_KEYWORDS:
            if keyword.lower() in header_text:
                matched_terms.add(keyword)
        for row in reader:
            sampled_rows += 1
            sample_rows.append(row[:8])
            row_text = "\t".join(row).lower()
            for keyword in FLAVONOID_KEYWORDS:
                if keyword.lower() in row_text:
                    matched_terms.add(keyword)
            if sampled_rows >= 20:
                break

    return {
        "exists": True,
        "columns": columns,
        "sample_rows": sample_rows,
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


def _find_significant_de_genes(data_dir: Path, out_dir: Path, preferred: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if preferred is not None:
        candidates.append(preferred)
    candidates.extend([data_dir / "significant_de_genes.tsv", out_dir / "significant_de_genes.tsv"])
    for base in (data_dir, out_dir):
        if base.exists():
            candidates.extend(sorted(base.rglob("significant_de_genes.tsv")))

    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _copy_significant_de_genes(significant_de_path: Path | None, out_path: Path) -> Path | None:
    if significant_de_path is None:
        return None
    copied = out_path / "significant_de_genes.tsv"
    if significant_de_path.resolve() == copied.resolve():
        return significant_de_path
    shutil.copy2(significant_de_path, copied)
    return copied


def _load_verified_literature_evidence(
    data_dir: Path,
    trait: str,
    *,
    literature_filename: str = VERIFIED_LITERATURE_EVIDENCE_FILE,
    gene_id: str = TARGET_GENE,
) -> tuple[list[dict[str, str]], Path]:
    # DOI 和引用原句不来自大模型生成，而是从人工整理的 TSV 中读取。
    # 这里先做最小过滤，保证后续 advice 只能引用“已落盘、可追溯”的文献字段。
    evidence_path = data_dir / literature_filename
    if not evidence_path.exists():
        return [], evidence_path

    entries: list[dict[str, str]] = []
    with evidence_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            row_gene_id = (row.get("gene_id") or "").strip()
            trait_value = (row.get("trait") or "").strip()
            doi = (row.get("doi") or "").strip()
            quoted_sentence = (row.get("quoted_sentence") or "").strip()
            if row_gene_id != gene_id:
                continue
            if "黄酮" not in trait_value and "黄酮" not in trait:
                continue
            if not DOI_PATTERN.fullmatch(doi):
                continue
            if not quoted_sentence:
                continue
            entries.append(
                {
                    "gene_id": row_gene_id,
                    "trait": trait_value,
                    "doi": doi,
                    "title": (row.get("title") or "").strip(),
                    "quoted_sentence": quoted_sentence,
                    "source": (row.get("source") or "").strip(),
                    "evidence_level": (row.get("evidence_level") or "").strip(),
                    "note": (row.get("note") or "").strip(),
                }
            )
    return entries, evidence_path


def _load_json_if_present(path_value: str) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _check_missing_pipeline_tools() -> list[str]:
    return [name for name in PIPELINE_DEPENDENCIES if shutil.which(name) is None]


def _run_transcriptome_pipeline(data_dir: Path, out_dir: Path, threads: int, run_log: Path) -> dict[str, Any]:
    # 真正的转录组执行不是 YuXi 原生能力，而是调用学长给定的固定脚本。
    # 该脚本底层依赖 hisat2、samtools、featureCounts、Rscript 等开源生信软件。
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
        str(threads),
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
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
        run_log.write_text(f"Pipeline execution failed before completion: {exc}\n", encoding="utf-8")
    return result


def _render_literature_lines(literature_evidence: list[dict[str, str]]) -> list[str]:
    lines = ["## 文献证据"]
    if not literature_evidence:
        lines.extend(["真实 DOI：待文献检索补充", "引用原文：待文献检索补充"])
        return lines

    for index, evidence in enumerate(literature_evidence, start=1):
        lines.append(f"### 证据 {index}")
        lines.append(f"真实 DOI：{evidence['doi']}")
        lines.append(f"引用原文：{evidence['quoted_sentence']}")
        if evidence.get("title"):
            lines.append(f"文献标题：{evidence['title']}")
        if evidence.get("source"):
            lines.append(f"证据来源：{evidence['source']}")
        if evidence.get("evidence_level"):
            lines.append(f"证据等级：{evidence['evidence_level']}")
        if evidence.get("note"):
            lines.append(f"备注：{evidence['note']}")
    return lines


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
    # 这里负责把“文件解析得到的证据”组织成可展示的育种建议。
    # 它生成的是建议文本，不是实验结论；所有表述都必须保留 smoke demo 边界。
    if de_support.get("supports_target_gene"):
        de_sentence = (
            f"转录组结果文件 `{significant_de_path}` 中检出 {TARGET_GENE}，"
            "可作为 smoke 范式下的候选转录组证据。"
        )
    elif de_support.get("available"):
        de_sentence = (
            f"当前 `significant_de_genes.tsv` 未检出 {TARGET_GENE}；"
            "建议仍需如实标记为待进一步验证的候选线索。"
        )
    else:
        de_sentence = "当前尚未获得 `significant_de_genes.tsv`，不能判断转录组是否支持 Si9g037800。"

    ref_sentences = []
    if gff_hit.get("found"):
        ref_sentences.append(f"`genome.gff` 中找到 {TARGET_GENE} 相关记录。")
    else:
        ref_sentences.append(f"`genome.gff` 中未找到 {TARGET_GENE}，不能编造基因位置。")
    if annotation_hit.get("found"):
        ref_sentences.append(f"`xiaomi_T2T_Annotation.smoke_genes.txt` 中找到 {TARGET_GENE} 相关注释记录。")
    else:
        ref_sentences.append(f"`xiaomi_T2T_Annotation.smoke_genes.txt` 中未找到 {TARGET_GENE}，不能编造功能注释。")

    if metabolome_summary.get("flavonoid_related"):
        metabolome_sentence = (
            "代谢组原始表中出现黄酮相关字段或名称，可作为黄酮相关背景证据，"
            "但不能证明 Si9g037800 到代谢物变化的因果关系。"
        )
    else:
        metabolome_sentence = (
            "代谢组原始表暂未在表头或前 20 行样本中识别到明确黄酮关键词；"
            "仍只能作为待解析的背景输入。"
        )

    background_only = literature_evidence and all(
        evidence.get("evidence_level") != "gene_specific" for evidence in literature_evidence
    )

    advice_lines = [
        "# 黄酮相关育种建议",
        "",
        "## 性状目标",
        f"当前性状输入为：{trait}。本轮建议围绕黄酮相关性状展开，且仅代表 smoke 测试范式下的初步建议。",
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
        *_render_literature_lines(literature_evidence),
        "",
        "## 育种建议",
        f"- 将 {TARGET_GENE} 作为黄酮相关候选基因线索之一，但根据转录组和注释证据强弱动态调整优先级。",
        "- 构建或扩大群体，系统采集基因型数据和黄酮含量表型。",
        "- 在群体中开展候选基因/候选位点与黄酮含量的关联分析。",
        "- 在获得可靠候选变异后，再开展 KASP/CAPS 或其他标记转化与验证设计。",
        "",
        "## 边界",
        "本结果来自 smoke 测试流程，不是生产级全基因组结论。",
        "当前只提出群体构建、表型测定、关联分析和标记验证计划，这些验证仍待后续执行。",
    ]
    if background_only:
        advice_lines.append("当前文献证据均为背景证据，不是 Si9g037800 直接功能验证。")
    return "\n".join(advice_lines)


def _guard_advice(advice: str, *, known_dois: set[str] | None = None) -> dict[str, Any]:
    # 这是最终输出守卫：不让 Agent 文本越过当前 demo 能力边界。
    # 重点检查目标基因、群体、黄酮、DOI 真实性，以及是否误称验证已经完成。
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


def _run_reference_prepare_impl(
    *,
    data_dir: str,
    genome_fa: str,
    genome_gff: str,
    annotation_txt: str,
    out_dir: str,
) -> dict[str, Any]:
    # 参考信息阶段只做“文件存在性 + 目标基因痕迹检查”，不做复杂生物学推断。
    data_path, error = _ensure_data_dir(data_dir)
    if error:
        return error

    out_path, out_error = _ensure_out_dir(out_dir)
    if out_error:
        return {"status": "error", "error": out_error, "artifacts": []}

    genome_fa_path = data_path / genome_fa
    genome_gff_path = data_path / genome_gff
    annotation_path = data_path / annotation_txt
    missing_inputs = [str(path) for path in (genome_fa_path, genome_gff_path, annotation_path) if not path.exists()]

    gff_hit = _lookup_gene_in_text(genome_gff_path, TARGET_GENE)
    annotation_hit = _lookup_gene_in_text(annotation_path, TARGET_GENE)
    manifest_path = out_path / "reference_manifest.json"
    manifest = {
        "tool": "breeding_reference_prepare",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if not missing_inputs else "error",
        "data_dir": str(data_path),
        "genome_fa": str(genome_fa_path),
        "genome_gff": str(genome_gff_path),
        "annotation_txt": str(annotation_path),
        "gene_id": TARGET_GENE,
        "gene_found_in_gff": gff_hit["found"],
        "gene_found_in_annotation": annotation_hit["found"],
        "missing_inputs": missing_inputs,
    }
    _write_json(manifest_path, manifest)
    return {
        "status": manifest["status"],
        "manifest": str(manifest_path),
        "gene_found_in_gff": gff_hit["found"],
        "gene_found_in_annotation": annotation_hit["found"],
        "gff_matches": gff_hit["matches"],
        "annotation_matches": annotation_hit["matches"],
        "missing_inputs": missing_inputs,
        "artifacts": [str(manifest_path)],
    }


def _run_transcriptome_deg_impl(
    *,
    data_dir: str,
    fq_dir: str,
    sample_map: str,
    genome_fa: str,
    genome_gff: str,
    out_dir: str,
    threads: int,
    run_pipeline: bool,
) -> dict[str, Any]:
    # 这一段是转录组 Tool 的核心编排：
    # 1. 检查输入文件和外部软件
    # 2. 需要时调用固定脚本
    # 3. 回收 significant_de_genes.tsv 并检查目标基因是否出现
    data_path, error = _ensure_data_dir(data_dir)
    if error:
        return error

    out_path, out_error = _ensure_out_dir(out_dir)
    if out_error:
        return {"status": "error", "error": out_error, "artifacts": []}

    fq_path = data_path / fq_dir
    sample_map_path = data_path / sample_map
    genome_fa_path = data_path / genome_fa
    genome_gff_path = data_path / genome_gff
    script_path = data_path / REQUIRED_FILES["pipeline_script"]
    missing_inputs = [str(path) for path in (sample_map_path, genome_fa_path, genome_gff_path, script_path) if not path.exists()]
    fastq_files = sorted(fq_path.glob("*.fq.gz")) if fq_path.exists() else []
    if not fastq_files:
        missing_inputs.append(str(fq_path / "*.fq.gz"))

    run_log = out_path / "run.log"
    pipeline_result = {"attempted": False, "returncode": None, "stdout_tail": "", "stderr_tail": "", "error": ""}
    missing_tools: list[str] = []

    if run_pipeline and not missing_inputs:
        missing_tools = _check_missing_pipeline_tools()
        if missing_tools:
            run_log.write_text("Missing pipeline tools: " + ", ".join(missing_tools) + "\n", encoding="utf-8")
        else:
            pipeline_result = _run_transcriptome_pipeline(data_path, out_path, threads, run_log)
    elif not run_log.exists():
        run_log.write_text("run_pipeline=false; existing significant_de_genes.tsv was requested.\n", encoding="utf-8")

    preferred = out_path / "de_pipeline_out" / "04_de" / "significant_de_genes.tsv"
    significant_de_path = _find_significant_de_genes(data_path, out_path, preferred=preferred)
    copied_de_path = _copy_significant_de_genes(significant_de_path, out_path)
    de_support = _inspect_de_support(copied_de_path or significant_de_path, TARGET_GENE)

    if missing_inputs:
        status = "error"
    elif run_pipeline and missing_tools:
        status = "error"
    elif run_pipeline and pipeline_result.get("returncode") not in {0, None}:
        status = "error"
    elif copied_de_path or significant_de_path:
        status = "completed"
    else:
        status = "error"

    manifest_path = out_path / "transcriptome_manifest.json"
    manifest = {
        "tool": "breeding_transcriptome_deg",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data_dir": str(data_path),
        "fq_dir": str(fq_path),
        "sample_map": str(sample_map_path),
        "genome_fa": str(genome_fa_path),
        "genome_gff": str(genome_gff_path),
        "run_pipeline": run_pipeline,
        "threads": threads,
        "missing_inputs": missing_inputs,
        "missing_tools": missing_tools,
        "pipeline_result": pipeline_result,
        "significant_de_genes_path": str(copied_de_path or significant_de_path or ""),
        "target_gene_found": de_support["supports_target_gene"],
        "target_gene_matches": de_support["matches"],
    }
    _write_json(manifest_path, manifest)

    artifacts = [str(manifest_path), str(run_log)]
    if copied_de_path or significant_de_path:
        artifacts.insert(0, str(copied_de_path or significant_de_path))

    return {
        "status": status,
        "manifest": str(manifest_path),
        "significant_de_genes_path": str(copied_de_path or significant_de_path or ""),
        "target_gene_found": de_support["supports_target_gene"],
        "matches": de_support["matches"],
        "missing_inputs": missing_inputs,
        "missing_tools": missing_tools,
        "pipeline_result": pipeline_result,
        "artifacts": artifacts,
    }


def _run_metabolome_prepare_impl(*, data_dir: str, metabolome_tsv: str, trait: str, out_dir: str) -> dict[str, Any]:
    # 代谢组阶段当前只做轻量读取，定位黄酮相关字段或名称，作为背景证据。
    # 它不产生因果证明，也不直接证明 Si9g037800 的功能。
    data_path, error = _ensure_data_dir(data_dir)
    if error:
        return error

    out_path, out_error = _ensure_out_dir(out_dir)
    if out_error:
        return {"status": "error", "error": out_error, "artifacts": []}

    metabolome_path = data_path / metabolome_tsv
    summary = _inspect_metabolome(metabolome_path)
    status = "completed" if summary["exists"] else "error"

    manifest_path = out_path / "metabolome_manifest.json"
    manifest = {
        "tool": "breeding_metabolome_prepare",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data_dir": str(data_path),
        "trait": trait,
        "metabolome_tsv": str(metabolome_path),
        "flavonoid_related": summary["flavonoid_related"],
        "matched_terms": summary["matched_terms"],
        "columns": summary["columns"],
        "sample_rows": summary["sample_rows"],
        "note": "代谢组信号只能作为黄酮相关背景证据，不能证明 Si9g037800 的因果关系。",
    }
    _write_json(manifest_path, manifest)
    return {
        "status": status,
        "manifest": str(manifest_path),
        "metabolome_tsv": str(metabolome_path),
        "flavonoid_related": summary["flavonoid_related"],
        "matched_terms": summary["matched_terms"],
        "columns": summary["columns"],
        "sample_rows": summary["sample_rows"],
        "artifacts": [str(manifest_path)],
    }


def _run_literature_evidence_impl(
    *,
    data_dir: str,
    literature_evidence: str,
    trait: str,
    gene_id: str,
    out_dir: str,
) -> dict[str, Any]:
    # 文献阶段的价值在于给前端和最终回答提供“可追溯 DOI + 原句”。
    # 当前 smoke 数据里的证据是背景证据，不应被解释成 Si9g037800 已直接功能验证。
    data_path, error = _ensure_data_dir(data_dir)
    if error:
        return error

    out_path, out_error = _ensure_out_dir(out_dir)
    if out_error:
        return {"status": "error", "error": out_error, "artifacts": []}

    evidence_entries, evidence_path = _load_verified_literature_evidence(
        data_path,
        trait,
        literature_filename=literature_evidence,
        gene_id=gene_id,
    )
    evidence_level_counts: dict[str, int] = {}
    for entry in evidence_entries:
        level = entry.get("evidence_level") or "unknown"
        evidence_level_counts[level] = evidence_level_counts.get(level, 0) + 1

    background_only = evidence_entries and all(
        entry.get("evidence_level") != "gene_specific" for entry in evidence_entries
    )
    status = "completed" if evidence_entries else "pending_literature"
    manifest_path = out_path / "literature_manifest.json"
    manifest = {
        "tool": "breeding_literature_evidence",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data_dir": str(data_path),
        "literature_evidence_path": str(evidence_path),
        "gene_id": gene_id,
        "trait": trait,
        "evidence_count": len(evidence_entries),
        "evidence_level_counts": evidence_level_counts,
        "background_only": background_only,
        "note": (
            "当前文献证据均为背景证据，不是 Si9g037800 直接功能验证。"
            if background_only
            else "若后续补入 gene_specific 文献，再更新 direct evidence 判断。"
        ),
        "entries": evidence_entries,
    }
    _write_json(manifest_path, manifest)
    return {
        "status": status,
        "manifest": str(manifest_path),
        "literature_evidence_path": str(evidence_path),
        "entries": evidence_entries,
        "evidence_level_counts": evidence_level_counts,
        "background_only": background_only,
        "artifacts": [str(manifest_path)],
    }


def _run_breeding_advice_generate_impl(
    *,
    data_dir: str,
    trait: str,
    reference_manifest: str,
    transcriptome_manifest: str,
    metabolome_manifest: str,
    literature_manifest: str,
    significant_de_genes: str,
    out_dir: str,
) -> dict[str, Any]:
    # 建议生成阶段是总装配：
    # - 读取前面各步骤的 manifest 或直接回退执行轻量检查
    # - 汇总文件证据
    # - 生成建议 markdown
    # - 再经过 guard，防止输出越界
    data_path, error = _ensure_data_dir(data_dir)
    if error:
        return {
            **error,
            "advice_markdown": "",
            "guard_result": {"passed": False, "errors": ["missing data_dir"]},
        }

    out_path, out_error = _ensure_out_dir(out_dir)
    if out_error:
        return {
            "status": "error",
            "error": out_error,
            "advice_markdown": "",
            "guard_result": {"passed": False, "errors": ["cannot create out_dir"]},
            "artifacts": [],
        }

    reference_payload = _load_json_if_present(reference_manifest) or _run_reference_prepare_impl(
        data_dir=str(data_path),
        genome_fa=REQUIRED_FILES["genome_fa"],
        genome_gff=REQUIRED_FILES["genome_gff"],
        annotation_txt=REQUIRED_FILES["annotation"],
        out_dir=str(out_path / "reference_prepare"),
    )
    transcriptome_payload = _load_json_if_present(transcriptome_manifest) or _run_transcriptome_deg_impl(
        data_dir=str(data_path),
        fq_dir="fq",
        sample_map=REQUIRED_FILES["sample_map"],
        genome_fa=REQUIRED_FILES["genome_fa"],
        genome_gff=REQUIRED_FILES["genome_gff"],
        out_dir=str(out_path / "transcriptome_deg"),
        threads=8,
        run_pipeline=False,
    )
    metabolome_payload = _load_json_if_present(metabolome_manifest) or _run_metabolome_prepare_impl(
        data_dir=str(data_path),
        metabolome_tsv=REQUIRED_FILES["metabolome"],
        trait=trait,
        out_dir=str(out_path / "metabolome_prepare"),
    )
    literature_payload = _load_json_if_present(literature_manifest) or _run_literature_evidence_impl(
        data_dir=str(data_path),
        literature_evidence=VERIFIED_LITERATURE_EVIDENCE_FILE,
        trait=trait,
        gene_id=TARGET_GENE,
        out_dir=str(out_path / "literature_evidence"),
    )

    genome_gff_path = Path(reference_payload.get("genome_gff", data_path / REQUIRED_FILES["genome_gff"]))
    annotation_path = Path(reference_payload.get("annotation_txt", data_path / REQUIRED_FILES["annotation"]))
    metabolome_path = Path(metabolome_payload.get("metabolome_tsv", data_path / REQUIRED_FILES["metabolome"]))
    literature_evidence_entries = literature_payload.get("entries", [])

    significant_de_path = (
        Path(significant_de_genes).expanduser().resolve()
        if significant_de_genes
        else Path(transcriptome_payload["significant_de_genes_path"]).expanduser().resolve()
        if transcriptome_payload.get("significant_de_genes_path")
        else None
    )
    de_support = _inspect_de_support(significant_de_path, TARGET_GENE)
    gff_hit = _lookup_gene_in_text(genome_gff_path, TARGET_GENE)
    annotation_hit = _lookup_gene_in_text(annotation_path, TARGET_GENE)
    metabolome_summary = _inspect_metabolome(metabolome_path)
    advice = _build_advice_markdown(
        trait=trait,
        significant_de_path=significant_de_path,
        de_support=de_support,
        gff_hit=gff_hit,
        annotation_hit=annotation_hit,
        metabolome_summary=metabolome_summary,
        literature_evidence=literature_evidence_entries,
    )
    known_dois = {entry["doi"] for entry in literature_evidence_entries}
    guard_result = _guard_advice(advice, known_dois=known_dois)

    status = "completed"
    if not (significant_de_path and significant_de_path.exists()):
        status = "error"
    if not guard_result["passed"]:
        status = "failed_guard" if status == "completed" else status
    elif guard_result.get("warnings"):
        status = "completed_with_warnings"

    advice_path = out_path / "breeding_advice.md"
    guard_path = out_path / "guard_result.json"
    manifest_path = out_path / "run_manifest.json"
    advice_path.write_text(advice, encoding="utf-8")
    _write_json(guard_path, guard_result)

    copied_de_path = _copy_significant_de_genes(significant_de_path, out_path)
    artifacts = [
        str(path)
        for path in [copied_de_path or significant_de_path, advice_path, guard_path, manifest_path]
        if path is not None
    ]
    manifest = {
        "tool": "breeding_advice_generate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data_dir": str(data_path),
        "trait": trait,
        "reference_manifest": reference_payload.get("manifest", reference_manifest),
        "transcriptome_manifest": transcriptome_payload.get("manifest", transcriptome_manifest),
        "metabolome_manifest": metabolome_payload.get("manifest", metabolome_manifest),
        "literature_manifest": literature_payload.get("manifest", literature_manifest),
        "significant_de_genes_path": str(copied_de_path or significant_de_path or ""),
        "artifacts": artifacts,
    }
    _write_json(manifest_path, manifest)

    return {
        "status": status,
        "manifest": str(manifest_path),
        "advice_markdown": advice,
        "significant_de_genes_path": str(copied_de_path or significant_de_path or ""),
        "guard_result": guard_result,
        "artifacts": artifacts,
    }


def _run_validation_plan_impl(*, trait: str, gene_id: str, marker_types: str, out_dir: str) -> dict[str, Any]:
    # 这里输出的是“下一步验证计划”，不是已完成结果。
    out_path, out_error = _ensure_out_dir(out_dir)
    if out_error:
        return {"status": "error", "error": out_error, "artifacts": []}

    plan = "\n".join([
        "# 黄酮相关验证计划",
        "",
        f"- 目标基因：{gene_id}",
        f"- 性状：{trait}",
        f"- 标记类型：{marker_types}",
        "",
        "## 计划步骤",
        "- 构建或扩大群体，覆盖目标基因位点附近的遗传变异。",
        "- 对群体开展基因型检测，优先关注 SNP/InDel/KASP/CAPS 相关候选位点。",
        "- 对群体同步开展黄酮含量表型测定。",
        "- 将基因型与黄酮表型做关联分析，评估候选位点稳定性。",
        "- 对显著候选变异开展进一步确认，决定是否进入后续转化。",
        "- 在确认候选变异后，再推进 KASP/CAPS 标记的后续转化设计。",
        "",
        "## 边界",
        "以上内容是验证计划，不是已完成的群体验证、湿实验验证或最终 KASP/CAPS 标记开发结果。",
    ])
    plan_path = out_path / "validation_plan.md"
    manifest_path = out_path / "validation_manifest.json"
    plan_path.write_text(plan, encoding="utf-8")
    _write_json(
        manifest_path,
        {
            "tool": "breeding_validation_plan",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "trait": trait,
            "gene_id": gene_id,
            "marker_types": marker_types,
            "plan_path": str(plan_path),
        },
    )
    return {
        "status": "completed",
        "manifest": str(manifest_path),
        "validation_plan": plan,
        "artifacts": [str(plan_path), str(manifest_path)],
    }


@tool(
    category="breeding",
    tags=["育种", "黄酮", "参考基因组"],
    display_name="参考基因组准备",
    args_schema=BreedingReferencePrepareInput,
)
def breeding_reference_prepare(
    data_dir: str = DEFAULT_DATA_DIR,
    genome_fa: str = "genome.fa",
    genome_gff: str = "genome.gff",
    annotation_txt: str = "xiaomi_T2T_Annotation.smoke_genes.txt",
    out_dir: str = "/tmp/yuxi_runs/breeding_reference_prepare",
) -> dict[str, Any]:
    """Validate breeding reference files and locate Si9g037800 in the reference annotations."""
    return _run_reference_prepare_impl(
        data_dir=data_dir,
        genome_fa=genome_fa,
        genome_gff=genome_gff,
        annotation_txt=annotation_txt,
        out_dir=out_dir,
    )


@tool(
    category="breeding",
    tags=["育种", "黄酮", "转录组"],
    display_name="转录组差异分析",
    args_schema=BreedingTranscriptomeDegInput,
)
def breeding_transcriptome_deg(
    data_dir: str = DEFAULT_DATA_DIR,
    fq_dir: str = "fq",
    sample_map: str = "sampleName_clientId.txt",
    genome_fa: str = "genome.fa",
    genome_gff: str = "genome.gff",
    out_dir: str = "/tmp/yuxi_runs/breeding_transcriptome_deg",
    threads: int = 8,
    run_pipeline: bool = True,
) -> dict[str, Any]:
    """Run or inspect the smoke DEG workflow and summarize whether Si9g037800 is significant."""
    return _run_transcriptome_deg_impl(
        data_dir=data_dir,
        fq_dir=fq_dir,
        sample_map=sample_map,
        genome_fa=genome_fa,
        genome_gff=genome_gff,
        out_dir=out_dir,
        threads=threads,
        run_pipeline=run_pipeline,
    )


@tool(
    category="breeding",
    tags=["育种", "黄酮", "代谢组"],
    display_name="代谢组准备",
    args_schema=BreedingMetabolomePrepareInput,
)
def breeding_metabolome_prepare(
    data_dir: str = DEFAULT_DATA_DIR,
    metabolome_tsv: str = "metabolome_raw_3372.tsv",
    trait: str = "黄酮相关",
    out_dir: str = "/tmp/yuxi_runs/breeding_metabolome_prepare",
) -> dict[str, Any]:
    """Inspect metabolome input and summarize flavonoid-related background signals."""
    return _run_metabolome_prepare_impl(
        data_dir=data_dir,
        metabolome_tsv=metabolome_tsv,
        trait=trait,
        out_dir=out_dir,
    )


@tool(
    category="breeding",
    tags=["育种", "黄酮", "文献"],
    display_name="文献证据读取",
    args_schema=BreedingLiteratureEvidenceInput,
)
def breeding_literature_evidence(
    data_dir: str = DEFAULT_DATA_DIR,
    literature_evidence: str = VERIFIED_LITERATURE_EVIDENCE_FILE,
    trait: str = "黄酮相关",
    gene_id: str = TARGET_GENE,
    out_dir: str = "/tmp/yuxi_runs/breeding_literature_evidence",
) -> dict[str, Any]:
    """Read verified literature evidence and keep background evidence separate from direct gene validation."""
    return _run_literature_evidence_impl(
        data_dir=data_dir,
        literature_evidence=literature_evidence,
        trait=trait,
        gene_id=gene_id,
        out_dir=out_dir,
    )


@tool(
    category="breeding",
    tags=["育种", "黄酮", "建议"],
    display_name="育种建议生成",
    args_schema=BreedingAdviceGenerateInput,
)
def breeding_advice_generate(
    data_dir: str = DEFAULT_DATA_DIR,
    trait: str = "黄酮相关",
    reference_manifest: str = "",
    transcriptome_manifest: str = "",
    metabolome_manifest: str = "",
    literature_manifest: str = "",
    significant_de_genes: str = "",
    out_dir: str = "/tmp/yuxi_runs/breeding_advice_generate",
) -> dict[str, Any]:
    """Aggregate reference, transcriptome, metabolome and literature results into guarded breeding advice."""
    return _run_breeding_advice_generate_impl(
        data_dir=data_dir,
        trait=trait,
        reference_manifest=reference_manifest,
        transcriptome_manifest=transcriptome_manifest,
        metabolome_manifest=metabolome_manifest,
        literature_manifest=literature_manifest,
        significant_de_genes=significant_de_genes,
        out_dir=out_dir,
    )


@tool(
    category="breeding",
    tags=["育种", "黄酮", "验证计划"],
    display_name="验证计划生成",
    args_schema=BreedingValidationPlanInput,
)
def breeding_validation_plan(
    trait: str = "黄酮相关",
    gene_id: str = TARGET_GENE,
    marker_types: str = "SNP/InDel/KASP/CAPS",
    out_dir: str = "/tmp/yuxi_runs/breeding_validation_plan",
) -> dict[str, Any]:
    """Generate a validation plan for the flavonoid breeding workflow without claiming finished experiments."""
    return _run_validation_plan_impl(
        trait=trait,
        gene_id=gene_id,
        marker_types=marker_types,
        out_dir=out_dir,
    )


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
    """Keep the one-click smoke entrypoint while reusing modular flavonoid breeding tools."""
    # 这个 Tool 是当前工作台最重要的一键入口。
    # 对老师解释时，可以把它理解为“先跑转录组/读取结果，再汇总成最终建议”的包装层。
    transcriptome_payload = _run_transcriptome_deg_impl(
        data_dir=data_dir,
        fq_dir="fq",
        sample_map=REQUIRED_FILES["sample_map"],
        genome_fa=REQUIRED_FILES["genome_fa"],
        genome_gff=REQUIRED_FILES["genome_gff"],
        out_dir=out_dir,
        threads=8,
        run_pipeline=run_transcriptome,
    )
    if transcriptome_payload.get("status") == "error" and transcriptome_payload.get("error"):
        return {
            "status": "error",
            "error": transcriptome_payload["error"],
            "advice_markdown": "",
            "significant_de_genes_path": "",
            "metabolome_path": "",
            "guard_result": {"passed": False, "errors": ["missing data_dir"]},
            "artifacts": [],
        }

    # 最终 advice 仍然依赖后续 guard；即使前面文件都在，也不能绕过边界约束。
    advice_payload = _run_breeding_advice_generate_impl(
        data_dir=data_dir,
        trait=trait,
        reference_manifest="",
        transcriptome_manifest=transcriptome_payload.get("manifest", ""),
        metabolome_manifest="",
        literature_manifest="",
        significant_de_genes=transcriptome_payload.get("significant_de_genes_path", ""),
        out_dir=out_dir,
    )
    data_path, _ = _ensure_data_dir(data_dir)
    metabolome_path = data_path / REQUIRED_FILES["metabolome"] if data_path is not None else Path("")
    result = {
        "status": advice_payload["status"],
        "advice_markdown": advice_payload["advice_markdown"],
        "significant_de_genes_path": advice_payload["significant_de_genes_path"],
        "metabolome_path": str(metabolome_path),
        "guard_result": advice_payload["guard_result"],
        "artifacts": advice_payload["artifacts"],
    }
    if transcriptome_payload.get("missing_tools"):
        result["missing_tools"] = transcriptome_payload["missing_tools"]
        if result["status"] == "completed":
            result["status"] = "completed_with_warnings"
    return result
