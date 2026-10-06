# PHASE 6 — REVIEW RESULT (round {{round}})

{{anchor}}

## Plan summary
{{plan}}

## Automated check results (from real tools — trust these)
{{checks}}

## Current project files
{{files}}

{{checklists}}

{{review_mode}}

## Your job
Review the result as a strict, skeptical senior reviewer who did NOT write it.
1. Re-read the TASK ANCHOR. For EACH acceptance criterion decide PASS or FAIL and cite evidence (file and what you see).
2. Mentally run it with a concrete example: open the page / call the function / run the script. Trace what happens. Look for crashes, broken references, missing files, wrong output, broken layout.
3. Go through the checklists item by item. Only report items that actually fail.
4. Every automated check ERROR is a real issue that must be fixed.
5. Report concrete issues with concrete fixes. Do not report style preferences as major.

## Output format (use exactly these headings)
## Criteria
1. PASS|FAIL — <evidence>
## Issues
- [critical|major|minor] <file>: <problem> → <fix>
(write "- none" if there are no issues)
## VERDICT: PASS
(or)
## VERDICT: FAIL

Use PASS only if every criterion is PASS and there are no critical or major issues.
