"""Command line interface: `python -m lmw <command>` (or lmw.bat / ./lmw)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__, ui
from .checks import format_findings, has_errors, run_checks
from .client import ChatClient, ModelError
from .config import Config, load_config
from .exporter import build_prompt
from .pipeline import Pipeline, read_request
from .skills import load_skills, select_skills
from .workspace import Workspace


def _add_model_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("model server")
    g.add_argument("--config", help="path to lmw.config.json")
    g.add_argument("--provider", choices=["openai", "ollama"], help="openai = any OpenAI-compatible server; ollama = native Ollama API (sets num_ctx)")
    g.add_argument("--base-url", dest="base_url", help="e.g. http://localhost:11434/v1 (Ollama), http://localhost:1234/v1 (LM Studio), http://localhost:8080/v1 (llama.cpp)")
    g.add_argument("-m", "--model", help="model name, e.g. qwen2.5-coder:14b")
    g.add_argument("--api-key", dest="api_key")
    g.add_argument("--ctx", dest="context_tokens", type=int, help="model context window in tokens (default 16384)")
    g.add_argument("--max-tokens", dest="max_output_tokens", type=int, help="max tokens per answer (default 4096)")
    g.add_argument("--temperature", type=float)


def _add_workflow_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("workflow")
    g.add_argument("-w", "--workspace", default=".", help="project folder to create/modify (default: current folder)")
    g.add_argument("--check", dest="checks", action="append", help="command that must succeed, e.g. \"pytest -q\" (repeatable)")
    g.add_argument("--skill", dest="skills", action="append", help="force-include a skill (repeatable)")
    g.add_argument("--no-skill", dest="exclude_skills", action="append", help="exclude a skill (repeatable)")
    g.add_argument("--min-rounds", dest="min_review_rounds", type=int, help="minimum review rounds (default 2)")
    g.add_argument("--max-rounds", dest="max_review_rounds", type=int, help="maximum review/fix rounds (default 5)")
    g.add_argument("--plan-rounds", dest="plan_rounds", type=int, help="maximum plan/review rounds (default 2)")
    g.add_argument("--no-interactive", dest="interactive", action="store_false", default=None, help="never ask questions; assume")
    g.add_argument("-v", "--verbose", action="store_true", default=None, help="stream model output to the console")


OVERRIDE_KEYS = ["provider", "base_url", "model", "api_key", "context_tokens", "max_output_tokens",
                 "temperature", "checks", "skills", "exclude_skills", "min_review_rounds",
                 "max_review_rounds", "plan_rounds", "interactive", "verbose"]


def _cfg(args: argparse.Namespace) -> Config:
    overrides: Dict = {k: getattr(args, k, None) for k in OVERRIDE_KEYS}
    return load_config(getattr(args, "config", None), overrides)


def _ask(question: str) -> str:
    try:
        return input("  ? %s\n    > " % question)
    except EOFError:
        return ""


def cmd_run(args) -> int:
    cfg = _cfg(args)
    request = read_request(" ".join(args.request) if args.request else None, args.file)
    if not request.strip():
        ui.err('no request given. Example: lmw run "Make a landing page for a cafe" -w ./cafe')
        return 2
    ask = _ask if cfg.interactive and sys.stdin.isatty() else None
    pipe = Pipeline(cfg, Path(args.workspace), request=request, ask=ask)
    state = pipe.run()
    return 0 if state.get("status") == "done" else 1


def cmd_resume(args) -> int:
    cfg = _cfg(args)
    runs = Path(args.workspace).resolve() / ".lmw" / "runs"
    run_id = args.run_id
    if not run_id:
        candidates = sorted(p.name for p in runs.glob("*") if (p / "state.json").is_file()) if runs.is_dir() else []
        if not candidates:
            ui.err("no saved runs in %s" % runs)
            return 2
        run_id = candidates[-1]
    ask = _ask if cfg.interactive and sys.stdin.isatty() else None
    pipe = Pipeline(cfg, Path(args.workspace), run_id=run_id, ask=ask)
    if pipe.state["stage"] == "done":
        ui.info("run %s is already finished (status: %s)" % (run_id, pipe.state.get("status")))
        return 0
    ui.info("resuming %s at stage '%s'" % (run_id, pipe.state["stage"]))
    state = pipe.run()
    return 0 if state.get("status") == "done" else 1


def cmd_skills(args) -> int:
    cfg = _cfg(args)
    skills = load_skills(cfg.resolved_skills_dir())
    picked = {s.name for s in select_skills(skills, args.text)} if args.text else set()
    for s in skills:
        mark = "*" if s.name in picked else " "
        print("%s %-16s p=%-3d %s" % (mark, s.name, s.priority, s.description))
        if s.references:
            print("    references: " + ", ".join(r.name for r in s.references))
    if args.text:
        print("\n* = selected for: %r" % args.text)
    return 0


def cmd_export(args) -> int:
    cfg = _cfg(args)
    text = build_prompt(cfg, args.skills or [], compact=args.compact, references=args.references,
                        for_text=args.for_text or "", budget=args.budget)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        from .textutil import estimate_tokens
        ui.ok("wrote %s (~%d tokens)" % (args.output, estimate_tokens(text)))
    else:
        print(text)
    return 0


def cmd_check(args) -> int:
    cfg = _cfg(args)
    ws = Workspace(Path(args.workspace))
    files = args.files or ws.list_files()
    findings = run_checks(ws, files, cfg.checks, cfg.check_timeout)
    print(format_findings(findings))
    return 1 if has_errors(findings) else 0


def cmd_doctor(args) -> int:
    cfg = _cfg(args)
    ui.banner("LMW doctor")
    ui.info("provider: %s   base_url: %s   model: %s" % (cfg.provider, cfg.base_url, cfg.model))
    ui.info("context: %d tokens, answer budget: %d, prompt budget: %d" % (
        cfg.context_tokens, cfg.max_output_tokens, cfg.input_budget()))
    try:
        ui.ok("skills dir: %s (%d skills)" % (cfg.resolved_skills_dir(), len(load_skills(cfg.resolved_skills_dir()))))
        ui.ok("prompts dir: %s" % cfg.resolved_prompts_dir())
    except FileNotFoundError as e:
        ui.err(str(e))
        return 1
    client = ChatClient(cfg)
    try:
        models = client.list_models()
        ui.ok("server reachable, %d models available" % len(models))
        for m in models[:30]:
            print("     - " + m)
        if models and cfg.model not in models and not any(m.startswith(cfg.model) for m in models):
            ui.warn("model '%s' not found on the server — set --model" % cfg.model)
    except ModelError as e:
        ui.err(str(e))
        return 1
    try:
        res = client.chat([{"role": "user", "content": "Reply with exactly: OK"}], max_tokens=16)
        ui.ok("test completion: %r (finish: %s)" % (res.text.strip()[:40], res.finish_reason))
    except ModelError as e:
        ui.err(str(e))
        return 1
    if cfg.provider == "openai" and ":11434" in cfg.base_url:
        ui.warn("You are using Ollama through /v1. Ollama may silently cut prompts to its default context. "
                "Use --provider ollama (sets num_ctx) or set OLLAMA_CONTEXT_LENGTH on the Ollama server.")
    return 0


def cmd_init(args) -> int:
    target = Path(args.output or "lmw.config.json")
    if target.exists() and not args.force:
        ui.err("%s already exists (use --force to overwrite)" % target)
        return 1
    cfg = Config()
    data = {k: v for k, v in cfg.to_dict().items() if k not in ("skills_dir", "prompts_dir")}
    data["provider"] = "ollama"
    data["base_url"] = "http://localhost:11434"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ui.ok("wrote %s — edit model/base_url to match your server" % target)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lmw", description="LMW — keep local models on task: think, plan, build, review, fix, deliver.")
    p.add_argument("--version", action="version", version="lmw " + __version__)
    sub = p.add_subparsers(dest="command")

    r = sub.add_parser("run", help="run the full workflow for a request")
    r.add_argument("request", nargs="*", help="what you want built (or use -f / stdin)")
    r.add_argument("-f", "--file", help="read the request from a text/markdown file")
    _add_model_args(r)
    _add_workflow_args(r)
    r.set_defaults(func=cmd_run)

    rs = sub.add_parser("resume", help="continue an interrupted run")
    rs.add_argument("run_id", nargs="?", help="run id (default: latest)")
    _add_model_args(rs)
    _add_workflow_args(rs)
    rs.set_defaults(func=cmd_resume)

    s = sub.add_parser("skills", help="list skills (optionally show which a text would select)")
    s.add_argument("text", nargs="?", help="sample request to test skill routing")
    s.add_argument("--config")
    s.set_defaults(func=cmd_skills)

    e = sub.add_parser("export", help="build one system prompt for chat apps (Open WebUI, LM Studio, ...)")
    e.add_argument("--skill", dest="skills", action="append", help="skill to include (repeatable; default: all)")
    e.add_argument("--for", dest="for_text", help="select skills automatically for this sample request")
    e.add_argument("--compact", action="store_true", help="short version for small context windows")
    e.add_argument("--references", action="store_true", help="also include reference files (long)")
    e.add_argument("--budget", type=int, help="max tokens for the exported prompt")
    e.add_argument("-o", "--output", help="output file (default: print)")
    e.add_argument("--config")
    e.set_defaults(func=cmd_export)

    c = sub.add_parser("check", help="run the automated checks on a folder")
    c.add_argument("files", nargs="*", help="files to check (default: all)")
    c.add_argument("-w", "--workspace", default=".")
    c.add_argument("--check", dest="checks", action="append")
    c.add_argument("--config")
    c.set_defaults(func=cmd_check)

    d = sub.add_parser("doctor", help="test the connection to your model server")
    _add_model_args(d)
    d.set_defaults(func=cmd_doctor)

    i = sub.add_parser("init", help="write an lmw.config.json template")
    i.add_argument("-o", "--output")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    ui.setup_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except KeyboardInterrupt:
        ui.err("interrupted — continue later with: lmw resume")
        return 130
    except ModelError as e:
        ui.err(str(e))
        ui.info("progress is saved; continue with: lmw resume")
        return 1
    except (FileNotFoundError, ValueError) as e:
        ui.err(str(e))
        return 2
