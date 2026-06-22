# WSL paste safety

Do **not** hand a heredoc (or any multi-line block) to the user as a paste-able
WSL terminal command. Clipboard CRLF line endings cause `: command not found`
and partial execution.

Instead:

1. Write the content to a file with the Write tool.
2. Have the user run the file directly (`bash script.sh`, `python3 script.py`).

This applies to any multi-line snippet you'd otherwise ask the user to paste.
