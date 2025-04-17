## Usage

```bash
uv venv
. .venv/bin/activate
uv pip install .
uv run main.py --docs-dir ./rule-sql-context --model gpt-4o
uv run ./main.py --emqx-mcp-server-dir path/to/emqx-mcp-server --docs-dir ./rule-sql-context --count-tokens
```

