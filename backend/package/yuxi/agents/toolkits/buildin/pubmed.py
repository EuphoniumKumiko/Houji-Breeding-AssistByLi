import time
import re
from typing import Any, Dict, List, Optional


from yuxi.agents.toolkits.registry import tool
from langchain_community.utilities import PubMedAPIWrapper
from langchain_community.tools import PubmedQueryRun

from yuxi.utils import logger


def _make_pubmed_url(pmid: Optional[str]) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""


def _safe_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _looks_like_transient_network_error(e: Exception) -> bool:
    msg = str(e).lower()
    transient_markers = [
        "ssl", "tls", "certificate", "timed out", "timeout",
        "connection reset", "connection aborted",
        "failed to establish a new connection",
        "remote end closed connection", "name or service not known",
        "temporarily unavailable",
    ]
    return any(m in msg for m in transient_markers)


def _missing_xmltodict(e: Exception) -> bool:
    # Covers: "Could not import xmltodict python package..."
    msg = str(e).lower()
    return "xmltodict" in msg and ("could not import" in msg or "install" in msg)


def clean_pubmed_title(v: Any) -> str:
    if v is None:
        return ""

    if isinstance(v, str):
        return v.strip()

    if isinstance(v, dict):
        txt = v.get("#text")
        if isinstance(txt, str) and txt.strip():
            return txt.strip()
        return " ".join(str(x).strip() for x in v.values() if str(x).strip()).strip()

    if isinstance(v, (list, tuple)):
        parts = [str(x).strip() for x in v if str(x).strip()]
        if not parts:
            return ""
        avg_len = sum(len(p) for p in parts) / len(parts)
        if avg_len < 25:
            return ""
        return " ".join(parts).strip()

    return str(v).strip()


# ---- snippet cleaning (your upgraded version) ----

_PREFIX_NUM_RE = re.compile(r"^\s*(?:[-–—]?\s*\d+[\.\)]\s*|\(\s*\d+\s*\)\s*)")

_LIST_PREFIX_RE2 = re.compile(
    r"""^\s*
        (?:[-–—]?\s*\d+\s*)?
        \[\s*
        (?:
            (?:'[^']{0,80}'|"[^"]{0,80}"|[^,\]]{1,80})\s*,\s*
        ){1,200}
        (?:'[^']{0,80}'|"[^"]{0,80}"|[^,\]]{1,80})
        \s*\]\s*
    """,
    re.VERBOSE
)

_DASH_LIST_PREFIX_RE = re.compile(
    r"""^\s*\[\s*(?:'?-{1,10}'?\s*,\s*){1,500}'?-{1,10}'?\s*\]\s*""",
    re.VERBOSE
)

_LEADING_JUNK_RE = re.compile(r"^\s*(?:[-–—]+|\*+|•+|\|+)\s*")


def clean_pubmed_snippet(text: Any) -> str:
    s = str(text or "").strip()
    if not s:
        return ""

    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _DASH_LIST_PREFIX_RE.sub("", s)
    s = _LIST_PREFIX_RE2.sub("", s)
    s = _PREFIX_NUM_RE.sub("", s)
    s = _LEADING_JUNK_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---- robust wrapper/tool init (version tolerant) ----

def _build_pubmed_wrapper(max_results: int) -> PubMedAPIWrapper:
    """
    Some langchain_community versions use different constructor args.
    Try a couple safely.
    """
    try:
        return PubMedAPIWrapper(top_k_results=max_results)
    except TypeError:
        # older/newer variants sometimes use `k` or `top_k`
        try:
            return PubMedAPIWrapper(k=max_results)  # type: ignore
        except TypeError:
            return PubMedAPIWrapper(top_k=max_results)  # type: ignore


@tool(category="buildin", tags=["搜索"], display_name="PubMed 搜索")
def pubmed_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """PubMed 文献检索工具：根据关键词/作者/期刊/年份等条件查询生物医学论文，输出论文标题与摘要片段，并附 PubMed 页面链接与 PMID。适合用于循证检索、背景调研与论文线索收集。"""
    t0 = time.perf_counter()
    max_results = max(1, int(max_results))

    out: Dict[str, Any] = {"query": query, "results": [], "response_time": 0.0}

    wrapper = _build_pubmed_wrapper(max_results)
    tool = PubmedQueryRun(api_wrapper=wrapper)

    logger.info(f"[PubMed_Search] query='{query}', max_results={max_results}")

    last_err: Optional[Exception] = None

    for attempt in range(1, 4):
        try:
            docs = wrapper.load_docs(query) or []
            logger.info(f"[PubMed_Search] attempt={attempt} load_docs returned {len(docs)} docs")

            docs = docs[:max_results]
            results: List[Dict[str, Any]] = []

            for idx, d in enumerate(docs):
                md = getattr(d, "metadata", {}) or {}

                pmid = _safe_text(md.get("uid", "")).strip()
                raw_title = md.get("Title", "")  # keep your confirmed key
                title = clean_pubmed_title(raw_title) or "(No title)"
                snippet = clean_pubmed_snippet(getattr(d, "page_content", "")) or "(No content)"

                url = _make_pubmed_url(pmid) if pmid else ""
                score = 1.0 / (idx + 1)

                results.append(
                    {
                        "title": title,
                        "content": snippet,
                        "url": url,
                        "score": float(score),
                        "pmid": pmid,
                    }
                )

            out["results"] = results
            out["response_time"] = round(time.perf_counter() - t0, 4)
            if results:
                logger.info(f"[PubMed_Search] success via load_docs, results={len(results)}")
            else:
                # out["message"] = "No PubMed results."
                logger.info(f"[PubMed_Search] returned no results (0 docs)")

            return out

        except KeyError as e:
            # Robust webenv detection
            last_err = e
            logger.exception(f"[PubMed_Search] attempt={attempt} failed (KeyError): {e}")

            if e.args and e.args[0] == "webenv":
                logger.warning("[PubMed_Search] KeyError 'webenv' detected, fallback to tool.run()")
                try:
                    text = _safe_text(tool.run(query)).strip()
                except Exception as e2:
                    # tool.run may also fail; final safe fallback below
                    last_err = e2
                    logger.exception(f"[PubMed_Search] tool.run failed after webenv: {e2}")
                    text = ""

                m = re.search(r"\bPMID:\s*(\d+)\b", text)
                pmid = m.group(1) if m else ""
                out["results"] = [
                    {
                        "title": f"PubMed results for: {query}",
                        "content": text or "(No content)",
                        "url": _make_pubmed_url(pmid) if pmid else "",
                        "score": 0.0,
                        "pmid": pmid,
                    }
                ]
                out["response_time"] = round(time.perf_counter() - t0, 4)
                return out

            # non-webenv KeyError: treat as non-transient and break to final fallback
            break

        except Exception as e:
            last_err = e
            logger.exception(f"[PubMed_Search] attempt={attempt} failed: {e}")

            # If xmltodict missing, don't retry; go straight to a safe fallback response
            if _missing_xmltodict(e):
                out["results"] = [
                    {
                        "title": f"PubMed results for: {query}",
                        "content": "Missing dependency: xmltodict. Install with `pip install xmltodict`.",
                        "url": "",
                        "score": 0.0,
                        "pmid": "",
                    }
                ]
                out["response_time"] = round(time.perf_counter() - t0, 4)
                return out

            if _looks_like_transient_network_error(e) and attempt < 3:
                sleep_s = 0.5 * (2 ** (attempt - 1))
                logger.warning(f"[PubMed_Search] transient error, retry after {sleep_s}s")
                time.sleep(sleep_s)
                continue

            if attempt == 3:
                logger.warning("[PubMed_Search] final fallback to tool.run()")
                try:
                    text = _safe_text(tool.run(query)).strip()
                except Exception as e2:
                    # Absolute last resort: never raise, return a valid shaped response
                    last_err = e2
                    logger.exception(f"[PubMed_Search] tool.run final fallback also failed: {e2}")
                    text = ""

                out["results"] = [
                    {
                        "title": f"PubMed results for: {query}",
                        "content": text or f"(No content). Last error: {type(last_err).__name__}: {last_err}",
                        "url": "",
                        "score": 0.0,
                        "pmid": "",
                    }
                ]
                out["response_time"] = round(time.perf_counter() - t0, 4)
                return out

            break

    # If we broke out early, still return well-formed output
    out["results"] = [
        {
            "title": f"PubMed results for: {query}",
            "content": f"(No content). Last error: {type(last_err).__name__}: {last_err}",
            "url": "",
            "score": 0.0,
            "pmid": "",
        }
    ]
    out["response_time"] = round(time.perf_counter() - t0, 4)
    logger.error(f"[PubMed_Search] giving up. last_err={last_err}")
    return out

