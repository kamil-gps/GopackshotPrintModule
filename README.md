# Gopackshot Print Module

Minimal CUPS-based printing module for Brother QL-1100.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.gopackshot_print.cli --pagesize DC06 --text "HELLO"
```

Use `--pagesize 62mm` for continuous tape.
