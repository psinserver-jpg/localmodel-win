"""The workflow engine.

THINK -> REVIEW UNDERSTANDING -> (CLARIFY) -> PLAN <-> REVIEW PLAN
      -> IMPLEMENT (step by step) -> [CHECKS + REVIEW -> FIX]* -> DELIVER

Why this works without fine-tuning:
- The orchestrator, not the model, enforces the phases. A small model only has to do
  one narrow job per call, with a fixed output format.
- A TASK ANCHOR (verbatim request + acceptance criteria) is injected into every call,
  so the model cannot drift away from what the user asked.
- Each call gets only the context it needs, trimmed to the model's real window.
- Real tools (parsers, compilers, link checkers, your test command) verify the output.
  The model cannot "PASS" its own work while a check fails.
- Cut-off answers are continued automatically; placeholders are detected and rejected.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import ui
from .checks import Finding, format_findings, has_errors, run_checks
from .client import ChatClient, ChatResult, strip_reasoning
from .config import Config
from .parse import (
    Step,
    failed_criteria,
    get_section,
    is_none,
    list_items,
    parse_file_blocks,
    parse_issues,
    parse_steps,
    parse_verdict,
    plan_files,
)
from .prompts import Slot, Templates, files_block, fit_files, render
from .skills import Skill, load_skills, select_references, select_skills
from .textutil import estimate_tokens, language_rule, tail_tokens
from .workspace import Workspace

STAGES = ["analyze", "review_analysis", "plan", "implement", "review", "final", "done"]

AskFn = Callable[[str], str]


class Pipeline:
    def __init__(
        self,
        cfg: Config,
        workspace_dir: Path,
        request: str = "",
        run_id: Optional[str] = None,
        client: Optional[ChatClient] = None,
        ask: Optional[AskFn] = None,
        approve: Optional[Callable[[list], list]] = None,
        session_context: str = "",
    ):
        self.cfg = cfg
        self.quiet = False  # chat shell: no per-phase details, only the result
        self.client = client or ChatClient(cfg)
        self.templates = Templates(cfg.resolved_prompts_dir())
        self.all_skills = load_skills(cfg.resolved_skills_dir())
        self.ask = ask
        self.approve = approve  # callback(blocks) -> blocks the user accepted

        root = workspace_dir.resolve()
        lmw_dir = root / ".lmw" / "runs"
        if run_id:
            self.run_dir = lmw_dir / run_id
            state_file = self.run_dir / "state.json"
            if not state_file.is_file():
                raise FileNotFoundError("No saved run at %s" % self.run_dir)
            self.state = json.loads(state_file.read_text(encoding="utf-8"))
        else:
            if not request.strip():
                raise ValueError("empty request")
            run_id = time.strftime("%Y%m%d-%H%M%S")
            self.run_dir = lmw_dir / run_id
            n = 1
            while self.run_dir.exists():
                n += 1
                self.run_dir = lmw_dir / ("%s-%d" % (run_id, n))
            self.run_dir.mkdir(parents=True)
            self.state = {
                "run_id": self.run_dir.name,
                "request": request.strip(),
                "stage": "analyze",
                "clarifications": "",
                "analysis_draft": "",
                "analysis": "",
                "criteria": [],
                "plan": "",
                "plan_round": 0,
                "steps": [],
                "step_index": 0,
                "review_round": 0,
                "last_review": "",
                "last_passed": False,
                "history": [],
                "pending_problems": [],
                "touched": [],
                "status": "running",
                "calls": 0,
                "session_context": session_context,
                "created": [],
            }
        self.ws = Workspace(root, backup_dir=self.run_dir / "backup")
        self.ws.touched = list(self.state.get("touched", []))
        self.ws.created = list(self.state.get("created", []))
        self.lang_rule = language_rule(self.state["request"], getattr(cfg, "language", "auto"))
        self.skills = self._pick_skills(self.state["request"])

    # =============================================================== helpers
    @property
    def request(self) -> str:
        return self.state["request"]

    def save(self) -> None:
        self.state["touched"] = self.ws.touched
        self.state["created"] = self.ws.created
        (self.run_dir / "state.json").write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _pick_skills(self, text: str) -> List[Skill]:
        return select_skills(self.all_skills, text, self.cfg.skills, self.cfg.exclude_skills)

    def _skills_text(self, extra_text: str = "", with_refs: bool = False) -> str:
        parts = []
        for s in self.skills:
            if s.always:
                continue  # the phase prompts already implement the core workflow
            parts.append("## Skill: %s\n%s" % (s.name, s.body))
        if with_refs:
            for s, r in select_references(self.skills, self.request + "\n" + extra_text):
                parts.append("## Reference (%s): %s\n%s" % (s.name, r.name, r.body))
        if not parts:
            return ""
        return "# EXPERT GUIDANCE (follow these rules)\n\n" + "\n\n".join(parts)

    def _checklists_text(self) -> str:
        parts = [s.checklist for s in self.skills if s.checklist]
        if not parts:
            return ""
        return "# REVIEW CHECKLISTS\n\n" + "\n\n".join(parts)

    def anchor(self) -> str:
        crit = self.state.get("criteria") or []
        goal = get_section(self.state.get("analysis", ""), "goal")
        cons = get_section(self.state.get("analysis", ""), "constraints")
        lines = [
            "## TASK ANCHOR (source of truth — re-read before every decision)",
            "Original request (verbatim):",
            "<<<",
            self.request,
            ">>>",
        ]
        if self.state.get("clarifications"):
            lines += ["User clarifications:", self.state["clarifications"]]
        if goal:
            lines += ["Goal: " + goal.strip()]
        if crit:
            lines += ["Acceptance criteria (ALL must pass):"] + ["%d. %s" % (i, c) for i, c in enumerate(crit, 1)]
        if cons and not is_none(cons):
            lines += ["Constraints:", cons.strip()]
        return "\n".join(lines)

    def _log(self, stage: str, prompt: str, answer: str) -> None:
        self.state["calls"] = self.state.get("calls", 0) + 1
        name = "%02d-%s.md" % (self.state["calls"], stage)
        (self.run_dir / name).write_text(
            "# PROMPT\n\n%s\n\n# RESPONSE\n\n%s\n" % (prompt, answer), encoding="utf-8"
        )

    def _system(self) -> str:
        return render(self.templates.get("system"), {"language_rule": Slot(self.lang_rule)}, 10**6)

    def call(self, stage: str, prompt: str, temperature: Optional[float] = None, expect_files: bool = False) -> str:
        """One model call with automatic continuation when the answer is cut off."""
        system = self._system()
        base = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        used = estimate_tokens(system) + estimate_tokens(prompt)
        if used > self.cfg.context_tokens - self.cfg.max_output_tokens:
            self._warn("prompt (~%d tokens) is close to the context limit (%d)" % (used, self.cfg.context_tokens))
        text = ""
        for attempt in range(self.cfg.max_continuations + 1):
            messages = base
            if attempt:
                tail = tail_tokens(text, 2500)
                messages = base + [
                    {"role": "assistant", "content": tail},
                    {"role": "user", "content": self.templates.get("continue")},
                ]
            progress = ui.Progress(self.cfg.verbose, show_status=not self.quiet)
            res: ChatResult = self.client.chat(messages, temperature=temperature, on_token=progress)
            progress.done()
            text = _merge_continuation(text, strip_reasoning(res.text))
            unclosed = expect_files and parse_file_blocks(text).truncated
            if not res.truncated and (not unclosed or attempt >= 1):
                break
            if attempt < self.cfg.max_continuations:
                self._info("answer was cut off — asking the model to continue (%d)" % (attempt + 1))
        self._log(stage, prompt, text)
        self.save()
        return text

    def _apply(self, blocks):
        if self.approve and blocks:
            accepted = self.approve(blocks)
            rejected = [b.path for b in blocks if b not in accepted]
            changed, problems = self.ws.apply_blocks(accepted)
            problems += ["The user REJECTED the change to %s. Do not change it the same way again." % r for r in rejected]
            return changed, problems
        return self.ws.apply_blocks(blocks)

    def _files_for_review(self) -> List[str]:
        files = list(self.ws.touched)
        for f in plan_files(self.state.get("plan", "")):
            if f not in files and self.ws.read(f) is not None:
                files.append(f)
        return files

    def _files_slot(self, files: List[str], share: float, focus: Optional[List[str]] = None) -> str:
        budget = int(self.cfg.input_budget() * share)
        contents = self.ws.contents_block(files)
        return files_block(fit_files(contents, budget, focus))

    # ================================================================ stages
    def run(self) -> Dict:
        stage_fns = {
            "analyze": self.stage_analyze,
            "review_analysis": self.stage_review_analysis,
            "plan": self.stage_plan,
            "implement": self.stage_implement,
            "review": self.stage_review,
            "final": self.stage_final,
        }
        self._info("run: %s   workspace: %s" % (self.state["run_id"], self.ws.root))
        self._info("model: %s (%s)   context: %d tokens" % (self.cfg.model, self.cfg.provider, self.cfg.context_tokens))
        self._info("skills: " + ", ".join(s.name for s in self.skills))
        while self.state["stage"] != "done":
            stage_fns[self.state["stage"]]()
            self.save()
        return self.state

    def _info(self, msg: str) -> None:
        if not self.quiet:
            ui.info(msg)

    def _brief(self, head: str, items=(), limit: int = 6) -> None:
        """Chat-shell view of what the workflow is doing: a short line plus a few items."""
        if not self.quiet:
            return
        print("  ⎿  " + head)
        items = [str(x).replace("\n", " ").strip() for x in items if str(x).strip()]
        for x in items[:limit]:
            print(ui.dim("     · " + (x[:120] + ("…" if len(x) > 120 else ""))))
        if len(items) > limit:
            print(ui.dim("     … 외 %d개" % (len(items) - limit)))

    def _warn(self, msg: str) -> None:
        if not self.quiet:
            ui.warn(msg)

    def _goto(self, stage: str) -> None:
        self.state["stage"] = stage
        self.save()

    # --- 1. THINK ----------------------------------------------------------
    def stage_analyze(self) -> None:
        ui.banner("1/8 THINK — analysing the request")
        budget = self.cfg.input_budget()
        prompt = render(self.templates.get("analyze"), {
            "request": Slot(self.request, 100, 10**6),
            "clarifications": Slot(self._clarifications_block(), 95, 10**6),
            "workspace": Slot(self.ws.tree(), 60, 200),
            "skills": Slot(self._skills_text(), 40),
        }, budget)
        self.state["analysis_draft"] = self.call("analyze", prompt)
        self._goto("review_analysis")

    def _clarifications_block(self) -> str:
        parts = []
        if self.state.get("session_context"):
            parts.append("## Earlier in this session (already done; those files exist in the workspace)\n"
                         + self.state["session_context"])
        if self.state.get("clarifications"):
            parts.append("## User clarifications\n" + self.state["clarifications"])
        return "\n\n".join(parts)

    # --- 2. REVIEW UNDERSTANDING ---------------------------------------------
    def stage_review_analysis(self) -> None:
        ui.banner("2/8 REVIEW — checking the understanding")
        prompt = render(self.templates.get("review_analysis"), {
            "request": Slot(self.request, 100, 10**6),
            "clarifications": Slot(self._clarifications_block(), 95, 10**6),
            "analysis": Slot(self.state["analysis_draft"], 90, 1500),
            "skills": Slot(self._skills_text(), 40),
        }, self.cfg.input_budget())
        out = self.call("review_analysis", prompt)
        if not get_section(out, "acceptance criteria"):
            self._warn("review did not return a full analysis; keeping the draft")
            out = self.state["analysis_draft"] + "\n\n" + out
        self.state["analysis"] = out
        crit = list_items(get_section(out, "acceptance criteria"))
        if not crit:
            crit = list_items(get_section(out, "requirements"))
        if not crit:
            crit = ["The original request is fully and correctly implemented."]
        self.state["criteria"] = crit[:15]
        for i, c in enumerate(self.state["criteria"], 1):
            self._info("%d. %s" % (i, c[:110]))
        self._brief("완료 기준 %d개를 정했습니다" % len(self.state["criteria"]), self.state["criteria"])

        questions = [q for q in list_items(get_section(out, "questions")) if not is_none(q)]
        if questions and not self.state.get("clarifications") and self.cfg.interactive and self.ask:
            answers = []
            ui.banner("QUESTIONS — the model needs a decision from you (Enter = let it decide)")
            for q in questions[:5]:
                a = self.ask(q).strip()
                answers.append("- Q: %s\n  A: %s" % (q, a or "(no preference — use the most reasonable choice)"))
            self.state["clarifications"] = "\n".join(answers)
            self.save()
            self._goto("review_analysis")  # refine the analysis with the answers
            return
        self.skills = self._pick_skills(self.request + "\n" + out)
        self._goto("plan")

    # --- 3/4. PLAN + REVIEW PLAN ----------------------------------------------
    def stage_plan(self) -> None:
        feedback = ""
        while True:
            self.state["plan_round"] += 1
            r = self.state["plan_round"]
            ui.banner("3/8 PLAN — round %d" % r)
            prompt = render(self.templates.get("plan"), {
                "anchor": Slot(self.anchor(), 100, 10**6),
                "analysis": Slot(self.state["analysis"], 70, 800),
                "workspace": Slot(self.ws.tree(), 60, 200),
                "skills": Slot(self._skills_text(), 40),
                "feedback": Slot(feedback, 95, 1500),
            }, self.cfg.input_budget())
            plan = self.call("plan", prompt)
            self.state["plan"] = plan

            ui.banner("4/8 REVIEW PLAN — round %d" % r)
            prompt = render(self.templates.get("review_plan"), {
                "anchor": Slot(self.anchor(), 100, 10**6),
                "plan": Slot(plan, 90, 2000),
                "skills": Slot(self._skills_text(), 40),
            }, self.cfg.input_budget())
            review = self.call("review_plan", prompt, temperature=self.cfg.review_temperature)
            verdict = parse_verdict(review)
            issues = [i for i in parse_issues(review) if i.severity in ("critical", "major")]
            missing = [l for l in list_items(get_section(review, "coverage")) if "missing" in l.lower()]
            if verdict == "PASS" and not issues and not missing:
                from .events import emit
                emit("notice", level="info", text="계획 승인")
                break
            if r >= self.cfg.plan_rounds:
                self._warn("plan still has open issues after %d rounds; continuing with the latest plan" % r)
                if issues or missing:
                    self.state["plan"] += "\n\n## Reviewer notes to respect during implementation\n" + "\n".join(
                        "- " + str(i) for i in issues) + "\n" + "\n".join("- " + m for m in missing)
                break
            self._warn("plan rejected (%d issues) — revising" % (len(issues) + len(missing)))
            self._brief("계획 검토: 보완할 점 %d개 — 계획을 고칩니다" % (len(issues) + len(missing)),
                        [str(i) for i in issues] + list(missing), 4)
            feedback = (
                "## Your previous plan was REJECTED by the reviewer. Write a corrected, complete plan.\n"
                "### Reviewer findings\n%s\n### Previous plan\n%s" % (
                    get_section(review, "issues") + "\n" + "\n".join(missing), plan)
            )
        steps = parse_steps(self.state["plan"])
        if not steps:
            steps = [Step(1, "Implement the whole plan", plan_files(self.state["plan"]),
                          "Implement every file in the plan completely.")]
        self.state["steps"] = [asdict(s) for s in steps]
        self.state["step_index"] = 0
        self.skills = self._pick_skills(self.request + "\n" + self.state["analysis"] + "\n" + self.state["plan"])
        self._info("%d implementation steps" % len(steps))
        self._brief("계획: 구현 %d단계" % len(steps),
                    ["%s%s" % (st.title, ("  (%s)" % ", ".join(st.files[:4])) if st.files else "") for st in steps], 10)
        self._goto("implement")

    # --- 5. IMPLEMENT ------------------------------------------------------
    def stage_implement(self) -> None:
        steps = [Step(**s) for s in self.state["steps"]]
        while self.state["step_index"] < len(steps):
            i = self.state["step_index"]
            step = steps[i]
            ui.banner("5/8 IMPLEMENT — step %d/%d: %s" % (i + 1, len(steps), step.title[:50]))
            known = list(dict.fromkeys(self.ws.touched + [f for f in step.files if self.ws.read(f) is not None]))
            prompt = render(self.templates.get("implement"), {
                "anchor": Slot(self.anchor(), 100, 10**6),
                "plan": Slot(self.state["plan"], 70, 600),
                "step": Slot(step.text, 98, 10**6),
                "step_number": Slot(str(i + 1), 100, 10**6),
                "step_total": Slot(str(len(steps)), 100, 10**6),
                "files": Slot(self._files_slot(known, 0.45, step.files), 80, 300),
                "skills": Slot(self._skills_text(step.text, with_refs=True), 40),
                "file_format": Slot(self.templates.get("_file_format"), 99, 10**6),
            }, self.cfg.input_budget())
            out = self.call("implement", prompt, expect_files=True)
            parsed = parse_file_blocks(out)
            if not parsed.blocks:
                self._warn("no file blocks in the answer — retrying once with a format reminder")
                out = self.call("implement", prompt + "\n\nIMPORTANT: your previous answer contained no "
                                "=== FILE: path === blocks. Output the files now in exactly that format.",
                                expect_files=True)
                parsed = parse_file_blocks(out)
            changed, problems = self._apply(parsed.blocks)
            for c in changed:
                _file_event("Write", c)
            for p in problems:
                ui.warn(p)
            self.state["pending_problems"] += problems
            self.state["step_index"] = i + 1
            self.save()
        self._goto("review")

    # --- 6/7. REVIEW <-> FIX ---------------------------------------------------
    def stage_review(self) -> None:
        while True:
            self.state["review_round"] += 1
            r = self.state["review_round"]
            files = self._files_for_review()
            ui.banner("6/8 REVIEW — round %d (checks + reviewer)" % r)
            findings = run_checks(self.ws, files, self.cfg.checks, self.cfg.check_timeout)
            findings += [Finding("error", "", p) for p in self.state.get("pending_problems", [])]
            self.state["pending_problems"] = []
            if not files:
                findings.append(Finding("error", "", "No files were produced. Implement the deliverables as FILE blocks."))
            n_err = sum(1 for f in findings if f.level == "error")
            (self._warn if n_err else self._info)("automated checks: %d errors, %d warnings" % (
                n_err, sum(1 for f in findings if f.level == "warning")))
            self._brief("자동 검사 (파일 %d개): 오류 %d · 경고 %d" % (
                len(files), n_err, sum(1 for f in findings if f.level == "warning")),
                [str(f) for f in findings if f.level == "error"], 4)
            checks_text = format_findings(findings)

            strict = r >= 2
            prompt = render(self.templates.get("review"), {
                "anchor": Slot(self.anchor(), 100, 10**6),
                "round": Slot(str(r), 100, 10**6),
                "plan": Slot(get_section(self.state["plan"], "approach") or self.state["plan"], 50, 200),
                "checks": Slot(checks_text, 95, 600),
                "files": Slot(self._files_slot(files, 0.55), 80, 500),
                "checklists": Slot(self._checklists_text(), 45),
                "review_mode": Slot(self.templates.get("review_strict") if strict else "", 90),
            }, self.cfg.input_budget())
            review = self.call("review", prompt, temperature=self.cfg.review_temperature)
            self.state["last_review"] = review

            verdict = parse_verdict(review) or "FAIL"
            issues = parse_issues(review)
            blocking = [i for i in issues if i.severity in ("critical", "major")]
            fails = failed_criteria(review)
            passed = verdict == "PASS" and not blocking and not fails and not has_errors(findings)
            self.state["last_passed"] = passed
            self.state["history"].append({
                "round": r, "verdict": verdict, "passed": passed,
                "issues": [str(i) for i in issues], "check_errors": n_err,
            })
            self.save()
            for i in issues[:12]:
                self._info(str(i)[:140])
            if issues:
                self._brief("검토에서 찾은 문제 %d개" % len(issues), [str(i) for i in issues], 5)
            from .events import emit
            if passed:
                emit("notice", level="info", text="검토 %d차: 통과" % r)
            else:
                emit("notice", level="warn", text="검토 %d차: 수정 필요 — 중요 문제 %d개, 미충족 기준 %d개, 자동검사 오류 %d개"
                     % (r, len(blocking), len(fails), n_err))

            if passed and r >= self.cfg.min_review_rounds:
                break
            if r >= self.cfg.max_review_rounds:
                if not passed:
                    self._warn("stopping after %d review rounds with open issues" % r)
                break
            to_fix = [str(i) for i in issues] + ["[major] criterion not met: " + f for f in fails]
            to_fix += [str(f) for f in findings if f.level in ("error", "warning")]
            if not to_fix and not passed:
                to_fix = ["[major] The reviewer rejected the result:\n" + (get_section(review, "criteria") or review[-2000:])]
            if not to_fix:
                self._info("no issues found — running an independent second-opinion review")
                continue
            self._fix(r, to_fix, checks_text, files)
        self._goto("final")

    def _fix(self, r: int, to_fix: List[str], checks_text: str, files: List[str]) -> None:
        ui.banner("7/8 FIX — round %d (%d issues)" % (r, len(to_fix)))
        before = self.ws.snapshot_hash(files)
        stuck = ""
        prev = self.state["history"][-2]["issues"] if len(self.state["history"]) >= 2 else []
        repeated = [i for i in to_fix if _norm(i) in {_norm(p) for p in prev}]
        if repeated:
            stuck = ("## WARNING: these issues were reported in the previous round too and are STILL NOT FIXED.\n"
                     "Your previous approach did not work. Use a different, simpler approach:\n"
                     + "\n".join("- " + i for i in repeated))
        if self.state.get("stuck_hash") == before:
            stuck += "\n## WARNING: your previous fix did not change any file. You MUST output corrected FILE blocks."
        prompt = render(self.templates.get("fix"), {
            "anchor": Slot(self.anchor(), 100, 10**6),
            "round": Slot(str(r), 100, 10**6),
            "issues": Slot("\n".join("- " + i for i in to_fix), 97, 1500),
            "checks": Slot(checks_text, 60, 300),
            "stuck_note": Slot(stuck, 96, 10**6),
            "files": Slot(self._files_slot(files, 0.5, _files_in_issues(to_fix, files)), 80, 500),
            "skills": Slot(self._skills_text("\n".join(to_fix), with_refs=False), 35),
            "file_format": Slot(self.templates.get("_file_format"), 99, 10**6),
        }, self.cfg.input_budget())
        out = self.call("fix", prompt, expect_files=True)
        parsed = parse_file_blocks(out)
        changed, problems = self._apply(parsed.blocks)
        for c in changed:
            _file_event("Edit", c)
        for p in problems:
            ui.warn(p)
        if not parsed.blocks:
            problems.append("The previous FIX answer contained no FILE/EDIT blocks, so nothing was changed.")
        self.state["pending_problems"] += problems
        after = self.ws.snapshot_hash(files)
        self.state["stuck_hash"] = after if after == before else ""
        self.save()

    # --- 8. DELIVER --------------------------------------------------------
    def stage_final(self) -> None:
        ui.banner("8/8 DELIVER — final report")
        files = self._files_for_review()
        findings = run_checks(self.ws, files, self.cfg.checks, self.cfg.check_timeout)
        status_line = "PASSED" if self.state.get("last_passed") and not has_errors(findings) else \
            "NOT FULLY PASSED — report open issues honestly"
        prompt = render(self.templates.get("final"), {
            "anchor": Slot(self.anchor(), 100, 10**6),
            "review": Slot("Overall status: %s\n\n%s" % (status_line, self.state.get("last_review", "")), 90, 800),
            "checks": Slot(format_findings(findings), 85, 300),
            "file_tree": Slot("\n".join("- " + f for f in files) or "(none)", 95, 10**6),
        }, self.cfg.input_budget())
        from .textutil import looks_like, preferred_language
        lang = preferred_language(self.state["request"], getattr(self.cfg, "language", "auto"))
        report = self.call("final", prompt + "\n\nWrite the whole report in %s (code and file names stay as they are)." % lang)
        if len(report) > 60 and not looks_like(report, lang):  # the model slipped into English: translate it
            report = self.call("translate", "Translate this report to %s. Keep code blocks, commands, file names, "
                               "identifiers and URLs exactly as they are; keep the markdown structure. "
                               "Output only the translation.\n\n%s" % (lang, report)) or report
        (self.run_dir / "REPORT.md").write_text(report, encoding="utf-8")
        self.state["status"] = "done" if "PASSED" == status_line else "incomplete"
        if self.quiet:
            from .events import emit
            emit("assistant", text=report)
        else:
            print()
            print(report)
            print()
        self._info("report: %s" % (self.run_dir / "REPORT.md"))
        self._info("logs of every phase: %s" % self.run_dir)
        if not self.quiet:
            ui.status("  📊 ")
        if self.ws.backup_dir and self.ws.backup_dir.exists():
            self._info("originals of overwritten files: %s" % self.ws.backup_dir)
        self._goto("done")


# ------------------------------------------------------------------- helpers

def _file_event(label: str, path: str) -> None:
    """Deep mode writes files directly; report them as structured tool events (shown on the web)."""
    from .events import emit
    tid = "f%d_%s" % (int(time.time() * 1000), path)
    emit("tool", id=tid, name="write_file" if label == "Write" else "edit_file", title="%s(%s)" % (label, path),
         input={"path": path})
    emit("tool_result", id=tid, ok=True, summary="저장됨")


def _merge_continuation(prev: str, new: str) -> str:
    """Join a continuation, removing a repeated overlap at the seam."""
    if not prev:
        return new
    if not new:
        return prev
    max_k = min(len(prev), len(new), 600)
    for k in range(max_k, 19, -1):
        if prev.endswith(new[:k]):
            return prev + new[k:]
    # The model sometimes restarts the last line; drop a duplicated partial line.
    last_nl = prev.rfind("\n")
    partial = prev[last_nl + 1:]
    if partial and new.startswith(partial) and len(partial) >= 8:
        return prev[: last_nl + 1] + new
    return prev + new


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()[:120]


def _files_in_issues(issues: List[str], files: List[str]) -> List[str]:
    joined = "\n".join(issues)
    return [f for f in files if f in joined or Path(f).name in joined]


def read_request(text: Optional[str], file: Optional[str]) -> str:
    if file:
        return Path(file).read_text(encoding="utf-8")
    if text:
        return text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""
