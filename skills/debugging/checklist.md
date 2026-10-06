# Debugging Review Checklist

## Diagnosis
- [ ] The answer quotes or names the exact error line (error type and message) it is fixing
- [ ] The answer identifies the file and line or function where the error originates in the user's code
- [ ] The stated root cause explains every reported symptom, not just the last error
- [ ] At least two possible causes were considered, or the single cause is directly proven by the error text or code
- [ ] Environment problems (missing package, wrong interpreter, venv not active, PATH, port in use, execution policy) are handled with commands, not code changes

## Fix
- [ ] The fix changes the code where the bad value or wrong behavior is created, not only where it crashes
- [ ] The error is not hidden by `try/except: pass`, an empty `catch {}`, a blanket `if x:` guard, or a hard-coded value
- [ ] The change is minimal and does not rename, reformat, or refactor unrelated code
- [ ] The fixed code is shown in full (whole file or whole function) with no `...` or `rest of code` placeholders
- [ ] Every name used in the fix is defined or imported, and any new dependency is listed with its install command
- [ ] Public interfaces (function signatures, routes, CLI flags, file formats) are unchanged, or every call site is updated
- [ ] Temporary debug prints and logging added during diagnosis are removed or clearly marked as optional

## Verification
- [ ] The answer gives the exact command(s) to reproduce the original problem and to confirm it is fixed
- [ ] A regression test or self-check that would have failed before the fix is included or described
- [ ] Existing tests are re-run (the command to run them is given)
- [ ] Edge cases near the bug (empty, `None`/`undefined`, zero, missing file or key) are handled by the fix
- [ ] Commands are given for Windows PowerShell, plus macOS/Linux equivalents when they differ

## Explanation
- [ ] The answer explains in plain words why the original code failed
- [ ] The answer states what was changed and why that change removes the cause
- [ ] If information was missing, the answer asks for the specific missing item (full traceback, command, versions, file)
