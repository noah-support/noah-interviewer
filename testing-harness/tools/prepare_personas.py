from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import typer
import yaml
from openai import OpenAI

from interviewees.env import load_harness_env, require_env
from interviewees.persona_layout import (
    default_personas_root,
    iter_persona_folders,
    prompt_file_in_folder,
)

app = typer.Typer(add_completion=False)


@app.callback()
def _load_dotenv() -> None:
    """Load testing-harness/.env before any subcommand."""
    load_harness_env()

# From personas/devide.txt: process basename -> Prosaview dataset folder name.
PROCESS_BASENAME_TO_DATASET: dict[str, str] = {
    "process1": "caseHandling_1",
    "process2": "complaint_1",
    "process3": "ComputerRepair_1",
    "process4": "ComputerRepair_2",
    "process5": "E2_proc",
    "process6": "ITIL",
    "process7": "permition_2",
    "process8": "steelmaking_1",
}


def _default_datasets_root() -> Path:
    return Path(__file__).resolve().parents[1] / "datasets" / "ProsaviewDataSets-main"


FORBIDDEN_WORDS = [
    "bpmn",
    "gateway",
    "node",
    "flowchart",
]

# "branch" and "task" are only forbidden in the BPMN/diagram sense. We'll still
# block them because it's safer for your evaluation harness.
FORBIDDEN_SUBSTRINGS = [
    " branch ",
    " task ",
]


def _require_file(path: Path) -> None:
    if not path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    if not path.is_file():
        raise typer.BadParameter(f"Not a file: {path}")


def _clean_activity_name(name: str) -> str:
    raw = (name or "").strip().replace("_", " ")
    raw = re.sub(r"\s+", " ", raw)
    if not raw:
        return raw
    # "Title-case sensibly": start with lowercasing then capitalize first letter.
    # Keep all-caps tokens as-is (e.g. "RMA").
    tokens = []
    for t in raw.split(" "):
        if len(t) >= 2 and t.isupper():
            tokens.append(t)
        else:
            tokens.append(t.lower())
    out = " ".join(tokens)
    return out[:1].upper() + out[1:]


@dataclass(frozen=True)
class Fragment:
    id: str
    name: str
    type: str
    branch: str
    in_coming: list[str]
    out_coming: list[str]


def _parse_subject_label_and_project(path: Path) -> tuple[str, str]:
    # Example: S0_ComputerRepair_1.json -> subject_label=S0, project=ComputerRepair_1
    m = re.match(r"^(S\d+)_([A-Za-z0-9_]+)\.json$", path.name)
    if not m:
        raise typer.BadParameter(
            "Input filename must look like S0_ProjectName.json (Prosaview dataset). "
            f"Got: {path.name}"
        )
    return m.group(1), m.group(2)


def _load_fragments(input_path: Path) -> list[Fragment]:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Top-level JSON must be an object")
    frags = raw.get("fragments")
    if not isinstance(frags, list):
        raise ValueError(
            f"{input_path.name} must contain a top-level fragments array "
            "(Prosaview BPMN fragment format)."
        )

    parsed: list[Fragment] = []
    for f in frags:
        if not isinstance(f, dict):
            raise ValueError("Each fragment must be an object")
        fid = str(f.get("id") or "").strip()
        ftype = str(f.get("type") or "").strip()
        if not fid or not ftype:
            raise ValueError(f"Fragment missing id/type: {f}")
        parsed.append(
            Fragment(
                id=fid,
                name=_clean_activity_name(str(f.get("name") or "")),
                type=ftype,
                branch=str(f.get("branch") or ""),
                in_coming=list(f.get("inComing") or []),
                out_coming=list(f.get("outComing") or []),
            )
        )
    return parsed


def _prefix_fragments(fragments: list[Fragment], *, prefix: str) -> list[Fragment]:
    def pid(node_id: str) -> str:
        return f"{prefix}{node_id}" if node_id else node_id

    return [
        Fragment(
            id=pid(f.id),
            name=f.name,
            type=f.type,
            branch=f.branch,
            in_coming=[pid(x) for x in f.in_coming],
            out_coming=[pid(x) for x in f.out_coming],
        )
        for f in fragments
    ]


def _find_dataset_dir(datasets_root: Path, dataset_name: str) -> Path:
    if not datasets_root.is_dir():
        raise FileNotFoundError(f"Datasets root not found: {datasets_root}")
    want = dataset_name.lower()
    for child in datasets_root.iterdir():
        if child.is_dir() and child.name.lower() == want:
            return child
    raise FileNotFoundError(
        f"No dataset folder matching {dataset_name!r} under {datasets_root}"
    )


def _has_fragments(path: Path) -> bool:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(raw, dict) and isinstance(raw.get("fragments"), list)


def _resolve_fragment_source(
    process_path: Path,
    *,
    datasets_root: Path | None,
) -> Path:
    """Use local process JSON if it has fragments; else Prosaview S0_* from datasets."""
    if _has_fragments(process_path):
        return process_path

    if datasets_root is None:
        raise ValueError(
            f"{process_path} is not Prosaview fragments JSON. "
            "Pass --datasets-root or replace the file with a fragments export."
        )

    dataset_name = PROCESS_BASENAME_TO_DATASET.get(process_path.stem)
    if not dataset_name:
        raise ValueError(
            f"No dataset mapping for {process_path.name} "
            f"(add to PROCESS_BASENAME_TO_DATASET in prepare_personas.py)"
        )

    dataset_dir = _find_dataset_dir(datasets_root, dataset_name)
    candidates = sorted(dataset_dir.glob("S0_*.json"))
    if not candidates:
        candidates = sorted(dataset_dir.glob("S*_*.json"))
    if not candidates:
        raise FileNotFoundError(f"No S*_*.json subject files in {dataset_dir}")

    return candidates[0]


def _load_merged_fragments_from_folder(
    folder: Path,
    *,
    datasets_root: Path | None = None,
) -> tuple[list[Fragment], list[str]]:
    process_files = sorted(folder.glob("process*.json"))
    if not process_files:
        raise ValueError(f"No process*.json files in {folder}")

    merged: list[Fragment] = []
    sources: list[str] = []
    for path in process_files:
        source = _resolve_fragment_source(path, datasets_root=datasets_root)
        if source == path:
            sources.append(path.name)
        elif datasets_root is not None:
            try:
                rel = source.relative_to(datasets_root)
                sources.append(f"{path.name} <- {rel}")
            except ValueError:
                sources.append(f"{path.name} <- {source.name}")
        else:
            sources.append(f"{path.name} <- {source.name}")
        frags = _load_fragments(source)
        merged.extend(_prefix_fragments(frags, prefix=f"{path.stem}__"))
    return merged, sources


def _build_graph(fragments: list[Fragment]) -> tuple[dict[str, Fragment], dict[str, list[str]]]:
    nodes = {f.id: f for f in fragments}
    edges: dict[str, list[str]] = defaultdict(list)
    for f in fragments:
        for out_id in f.out_coming:
            if out_id in nodes:
                edges[f.id].append(out_id)
    return nodes, edges


def _find_start_nodes(nodes: dict[str, Fragment]) -> list[str]:
    starts = [nid for nid, n in nodes.items() if n.type == "START_EVENT"]
    if starts:
        return starts
    # Fallback: anything with no incoming among known nodes.
    incoming = set()
    for n in nodes.values():
        for inc in n.in_coming:
            if inc in nodes:
                incoming.add(n.id)
    return [nid for nid in nodes.keys() if nid not in incoming]


def _topo_walk_paths(
    nodes: dict[str, Fragment],
    edges: dict[str, list[str]],
    *,
    max_paths: int = 50,
    max_depth: int = 500,
) -> list[list[str]]:
    starts = _find_start_nodes(nodes)
    if not starts:
        raise ValueError("No START_EVENT (or start candidate) found")

    paths: list[list[str]] = []
    q: deque[list[str]] = deque([[s] for s in starts])

    while q and len(paths) < max_paths:
        path = q.popleft()
        if len(path) > max_depth:
            continue
        last = path[-1]
        n = nodes.get(last)
        if not n:
            continue
        if n.type == "END_EVENT":
            paths.append(path)
            continue
        outs = edges.get(last, [])
        if not outs:
            paths.append(path)
            continue
        for nxt in outs:
            if nxt in path:
                # cycle guard
                continue
            q.append(path + [nxt])
    return paths


def _summarize_for_llm(nodes: dict[str, Fragment], edges: dict[str, list[str]]) -> dict:
    paths = _topo_walk_paths(nodes, edges)

    type_counts = Counter(n.type for n in nodes.values())

    # Identify likely "main" task names to infer a role later
    task_names = [n.name for n in nodes.values() if n.type == "TASK" and n.name]
    task_counts = Counter(task_names)

    # For each gateway, list its outgoing names to help narration.
    gateways = []
    for nid, n in nodes.items():
        if "GATEWAY" in n.type or n.type.endswith("GATEWAY") or "XOR" in n.type:
            outs = [nodes[o].name or nodes[o].id for o in edges.get(nid, []) if o in nodes]
            gateways.append({"id": nid, "type": n.type, "name": n.name, "outgoing": outs})

    return {
        "node_count": len(nodes),
        "type_counts": dict(type_counts),
        "sample_tasks": [t for t, _ in task_counts.most_common(12)],
        "gateways": gateways[:40],
        "paths": [[nodes[x].name or nodes[x].id for x in p] for p in paths[:20]],
    }


def _infer_defaults(nodes: dict[str, Fragment], *, project: str, subject_label: str) -> dict:
    # Lightweight heuristic defaults; user can edit later.
    domain_company = "Northwind Computer Services" if "ComputerRepair" in project else "Northwind"

    task_names = " ".join(
        n.name.lower() for n in nodes.values() if n.type == "TASK" and n.name
    )
    if any(k in task_names for k in ["cost", "quote", "estimate", "calculation"]):
        role = "Repair Coordinator"
    elif any(k in task_names for k in ["invoice", "payment", "billing"]):
        role = "Billing Specialist"
    elif any(k in task_names for k in ["diagnose", "repair", "replace", "test"]):
        role = "Repair Technician"
    else:
        role = "Service Operations Associate"

    # Simple stable names by subject label.
    name_by_subject = {
        "A": "Marta",
        "B": "Tom",
        "C": "Elena",
        "D": "Jamal",
        "S0": "Marta",
        "S1": "Tom",
        "S2": "Elena",
        "S3": "Jamal",
        "S4": "Priya",
    }
    name = name_by_subject.get(subject_label, f"Employee {subject_label}")

    return {
        "identity": {
            "name": name,
            "role": role,
            "company": domain_company,
            "department": "Service Operations",
            "years_in_role": 4,
        },
        "personality": {
            "tone": "friendly but a bit rushed",
            "quirks": [
                "mentions coworker \"Tom\" who handles hardware",
                "occasionally complains about the new ticketing system",
            ],
        },
    }


def _contains_forbidden(text: str) -> list[str]:
    low = text.lower()
    hits = []
    for w in FORBIDDEN_WORDS:
        if w in low:
            hits.append(w)
    for s in FORBIDDEN_SUBSTRINGS:
        if s in low:
            hits.append(s.strip())
    return hits


OUTPUT_TEST_PROJECT = "output-test"


def _openai_knowledge(
    summary: dict,
    *,
    model: str,
    persona_id: str,
    multi_process: bool = False,
) -> dict[str, str]:
    client = OpenAI(api_key=require_env("OPENAI_API_KEY"))

    system = (
        "You write persona knowledge for an interviewee in a process-mining study. "
        "You must write like a real employee describing their work casually, not like an analyst. "
        "Short sentences. No bullet points. No numbered lists. No headers. "
        "Do not use these words anywhere: BPMN, gateway, node, flowchart, branch, task."
    )

    multi_note = ""
    if multi_process:
        multi_note = (
            "This persona covers several related work processes merged together. "
            "Describe your knowledge across all of them without listing process names.\n\n"
        )

    user = (
        f"Persona id: {persona_id}\n\n"
        f"{multi_note}"
        "Here is a cleaned summary of the subject's partial process knowledge, "
        "derived from a process graph:\n\n"
        f"{json.dumps(summary, indent=2, ensure_ascii=False)}\n\n"
        "Write SIX paragraphs of natural language in first person, in this exact JSON object shape:\n"
        "{\n"
        '  \"what_i_do\": \"...\",\n'
        '  \"what_i_receive\": \"...\",\n'
        '  \"what_i_hand_off\": \"...\",\n'
        '  \"decision_points\": \"...\",\n'
        '  \"exceptions_and_edge_cases\": \"...\",\n'
        '  \"things_i_only_hear_about\": \"...\"  // can be empty string\n'
        "}\n\n"
        "Constraints:\n"
        "- No bullet points.\n"
        "- No lists.\n"
        "- Do not mention diagrams or modeling.\n"
        "- Be honest about partial knowledge; it's fine to say you only see part of the work.\n"
    )

    def call(extra: str | None = None) -> dict[str, str]:
        msg = user if extra is None else (user + "\n\n" + extra)
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": msg},
            ],
            temperature=0.7,
        )
        content = res.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except Exception as e:
            raise RuntimeError(f"Model did not return valid JSON: {e}\n\n{content}") from e
        if not isinstance(parsed, dict):
            raise RuntimeError("Model JSON must be an object")
        out: dict[str, str] = {}
        for k in [
            "what_i_do",
            "what_i_receive",
            "what_i_hand_off",
            "decision_points",
            "exceptions_and_edge_cases",
            "things_i_only_hear_about",
        ]:
            v = parsed.get(k, "")
            if not isinstance(v, str):
                raise RuntimeError(f"Model field {k} must be a string")
            out[k] = v.strip()
        return out

    first = call()
    hits = _contains_forbidden(" ".join(first.values()))
    if not hits:
        return first

    second = call(
        "Your previous output used forbidden words. Rewrite while avoiding them completely."
    )
    hits2 = _contains_forbidden(" ".join(second.values()))
    if hits2:
        raise RuntimeError(f"Output still contains forbidden words: {hits2}")
    return second


def _write_persona_yaml(
    output_path: Path,
    *,
    persona_id: str,
    project: str,
    subject_label: str,
    defaults: dict,
    knowledge: dict[str, str],
    force: bool,
) -> None:
    if output_path.exists() and not force:
        raise RuntimeError(f"Refusing to overwrite existing persona: {output_path}")

    payload = {
        "id": persona_id,
        "project": project,
        "subject_label": subject_label,
        **defaults,
        "knowledge": knowledge,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _iter_inputs(input_path: Path | None, input_dir: Path | None) -> Iterable[Path]:
    if input_path is not None:
        yield input_path
        return
    assert input_dir is not None
    for p in sorted(input_dir.glob("S*_*.json")):
        if p.is_file():
            yield p


def _prepare_prosaview_file(
    in_path: Path,
    *,
    output_dir: Path,
    openai_model: str,
    force: bool,
) -> None:
    subject_label, project = _parse_subject_label_and_project(in_path)
    persona_id = f"{project}__{subject_label}"

    fragments = _load_fragments(in_path)
    nodes, edges = _build_graph(fragments)
    summary = _summarize_for_llm(nodes, edges)
    defaults = _infer_defaults(nodes, project=project, subject_label=subject_label)

    knowledge = _openai_knowledge(summary, model=openai_model, persona_id=persona_id)

    out_path = output_dir / f"{subject_label}.yaml"
    _write_persona_yaml(
        out_path,
        persona_id=persona_id,
        project=project,
        subject_label=subject_label,
        defaults=defaults,
        knowledge=knowledge,
        force=force,
    )
    typer.echo(f"Wrote {out_path}")


def _prepare_personas_root(
    personas_root: Path,
    *,
    datasets_root: Path | None,
    openai_model: str,
    force: bool,
) -> None:
    if not personas_root.is_dir():
        raise typer.BadParameter(f"Personas root not found: {personas_root}")

    folders = iter_persona_folders(personas_root)
    if not folders:
        raise typer.BadParameter(f"No persona folders under {personas_root}")

    for folder in folders:
        subject_label = folder.name
        persona_id = f"{OUTPUT_TEST_PROJECT}__{subject_label}"
        process_files = sorted(folder.glob("process*.json"))

        try:
            fragments, sources = _load_merged_fragments_from_folder(
                folder,
                datasets_root=datasets_root,
            )
        except (ValueError, FileNotFoundError) as e:
            raise typer.BadParameter(f"{folder.name}: {e}") from e

        nodes, edges = _build_graph(fragments)
        summary = _summarize_for_llm(nodes, edges)
        summary["persona_process_files"] = [p.name for p in process_files]
        summary["fragment_sources"] = sources
        defaults = _infer_defaults(
            nodes,
            project=OUTPUT_TEST_PROJECT,
            subject_label=subject_label,
        )
        knowledge = _openai_knowledge(
            summary,
            model=openai_model,
            persona_id=persona_id,
            multi_process=len(process_files) > 1,
        )

        out_path = prompt_file_in_folder(folder)
        _write_persona_yaml(
            out_path,
            persona_id=persona_id,
            project=OUTPUT_TEST_PROJECT,
            subject_label=subject_label,
            defaults=defaults,
            knowledge=knowledge,
            force=force,
        )
        typer.echo(f"Wrote {out_path} ({len(process_files)} process files)")


@app.command("batch")
def batch(
    personas_root: Path = typer.Option(
        default_personas_root(),
        "--personas-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Root containing persona folders A, B, C, D (default: testing-harness/personas/)",
    ),
    datasets_root: Path = typer.Option(
        _default_datasets_root(),
        "--datasets-root",
        exists=False,
        file_okay=False,
        dir_okay=True,
        help="Prosaview datasets used when process*.json lacks fragments",
    ),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """
    Prepare one prompt.yaml per folder under personas/ from all process*.json files.

    Example: python tools/prepare_personas.py batch
    """
    ds_root = datasets_root if datasets_root.is_dir() else None
    if ds_root is None:
        typer.echo(
            f"Datasets root not found ({datasets_root}); "
            "each process*.json must already be fragments JSON.",
            err=True,
        )
    _prepare_personas_root(
        personas_root.resolve(),
        datasets_root=ds_root,
        openai_model=openai_model,
        force=force,
    )


@app.command()
def main(
    input: Path | None = typer.Option(None, "--input", exists=False, readable=True),
    input_dir: Path | None = typer.Option(None, "--input-dir", exists=False, readable=True),
    personas_root: Path | None = typer.Option(
        None,
        "--personas-root",
        exists=False,
        file_okay=False,
        dir_okay=True,
        help="Prepare one YAML per subfolder (process*.json merged); writes {name}.yaml alongside",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Output directory (required for --input / --input-dir)",
    ),
    openai_model: str = typer.Option("gpt-4o", "--openai-model"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Convert BPMN fragment JSON into persona YAML (Prosaview files or personas/<folder>/)."""
    modes = sum(
        1
        for x in (input is not None, input_dir is not None, personas_root is not None)
        if x
    )
    if modes != 1:
        raise typer.BadParameter(
            "Provide exactly one of: --input, --input-dir, or --personas-root"
        )

    if personas_root is not None:
        typer.echo(
            "Prefer: python tools/prepare_personas.py batch",
            err=True,
        )
        ds = _default_datasets_root()
        _prepare_personas_root(
            personas_root.resolve(),
            datasets_root=ds if ds.is_dir() else None,
            openai_model=openai_model,
            force=force,
        )
        return

    if output_dir is None:
        raise typer.BadParameter("--output-dir is required with --input or --input-dir")

    if input is not None:
        _require_file(input)
    elif not input_dir.exists() or not input_dir.is_dir():
        raise typer.BadParameter(f"Input dir not found: {input_dir}")

    for in_path in _iter_inputs(input, input_dir):
        _prepare_prosaview_file(
            in_path,
            output_dir=output_dir,
            openai_model=openai_model,
            force=force,
        )


if __name__ == "__main__":
    app()

