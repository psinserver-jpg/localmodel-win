## How to output files (machine-parsed — follow exactly)

For every new file, or any file shorter than about 300 lines, output the COMPLETE file:

=== FILE: relative/path/to/file.ext ===
<entire file content, from the first line to the last line>
=== END FILE ===

For a LARGE existing file where only a small part changes, you may output exact edits instead:

=== EDIT: relative/path/to/file.ext ===
<<<<<<< SEARCH
<lines copied EXACTLY from the current file>
=======
<replacement lines>
>>>>>>> REPLACE
=== END EDIT ===

Rules:
- Paths are relative to the project root, use forward slashes, no leading "/" and no "..".
- Do NOT wrap file content in ``` code fences inside a FILE block.
- Never write placeholders such as "...", "// rest of code", "TODO", "same as before", or lorem ipsum.
- A FILE block replaces the whole file, so it must contain everything, including unchanged parts.
- SEARCH text must match the current file exactly (copy it, do not retype from memory).
