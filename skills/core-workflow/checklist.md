# Core Review Checklist

## Requirement coverage
- [ ] Every acceptance criterion in the TASK ANCHOR is satisfied, with concrete evidence in the files
- [ ] Every explicit word of the original request is honored (numbers, names, languages, frameworks, colors, pages)
- [ ] Nothing the user said not to do was done
- [ ] No unrequested scope that adds risk (extra frameworks, build steps, features)

## Completeness
- [ ] No placeholder text: `...`, `TODO`, `FIXME`, `rest of code`, `your code here`, lorem ipsum, "구현 필요"
- [ ] No file is truncated; every file ends cleanly (closing tags, braces, final function body)
- [ ] Every file referenced by another file exists (scripts, styles, images, imports, modules)
- [ ] Every function, class, variable, CSS class, and element id that is used is also defined

## Correctness
- [ ] Mentally running the main path with a concrete example produces the expected result
- [ ] Edge cases are handled: empty input, missing file, invalid value, network error where relevant
- [ ] No syntax errors (balanced brackets, quotes, tags; valid JSON)
- [ ] No APIs, packages, or options that do not exist

## Delivery
- [ ] Exact run/open instructions are given, including install steps and Windows commands where relevant
- [ ] Dependencies are listed (requirements.txt / package.json) or none are needed
- [ ] User-visible text is in the user's language and reads naturally
