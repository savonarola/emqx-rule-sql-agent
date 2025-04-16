import argparse
import asyncio
import glob
import logging
from pathlib import Path

import agents
from agents import Agent, Runner
from agents.mcp import MCPServer, MCPServerStdio
from prompt_toolkit import PromptSession

logging.basicConfig(level=logging.WARNING)
logging.getLogger("openai.agents").setLevel(logging.WARNING)
agents.run.RunConfig.tracing_disabled = True


def instructions():
    doc_file_pattern = Path(__file__).parent.joinpath("rule-sql-context").joinpath("*.md")
    print(doc_file_pattern)
    rule_sql_doc_files = glob.glob(str(doc_file_pattern))
    rule_sql_docs = [open(f).read() for f in rule_sql_doc_files]
    syntax = "\n".join(rule_sql_docs)

    return f"""
    You help to compose an SQL statement for the EMQX Rule Engine.

    The following are the documents for the SQL statements:
    {syntax}
    """


def extend_prompt(user_input: str):
    return f"""
    Please help to compose an SQL statement for the EMQX Rule Engine:
    {user_input}

    Use the validate_sql tool to validate the SQL statement before providing the final answer.
    Use the 

    For validation with validate_sql tool, provide samples that are expected to match
    and samples that are expected to not match the SQL statement.

    In case of composing an SQL statement, provide concise answer, without any additional text.
    """


async def run(mcp_server: MCPServer, instructions: str, args: argparse.Namespace):
    session = PromptSession(
        message="rule-sql-agent> "
    )

    # Get all the topics from the EMQX server
    agent = Agent(
        name="Assistant",
        instructions=instructions,
        mcp_servers=[mcp_server],
        model=args.model,
    )

    agent_input = []

    while True:
        user_input = session.prompt(in_thread=True).strip()
        agent_input.append({"role": "user", "content": extend_prompt(user_input)})

        result = await Runner.run(agent, agent_input)
        print(result.final_output)
        agent_input = result.to_input_list()


def main():
    parser = argparse.ArgumentParser("EMQX Rule SQL Agent")
    parser.add_argument("--model", type=str, default="gpt-4o")
    parser.add_argument("--emqx-mcp-server-dir", type=dir_path, required=True)
    parser.add_argument("--emqx-api-url", type=str, default="http://localhost:18083/api/v5")
    parser.add_argument("--emqx-api-key", type=str, default="key")
    parser.add_argument("--emqx-api-secret", type=str, default="secret")

    args = parser.parse_args()
    try:
        asyncio.run(run_mcp_server(instructions(), args))
    except KeyboardInterrupt:
        print("Goodbye!")


async def run_mcp_server(instructions: str, args: argparse.Namespace):
    async with MCPServerStdio(
        name="EMQX helper server",
        params={
            "command": "uv",
            "args": [
                "--directory",
                args.emqx_mcp_server_dir,
                "run",
                "emqx-mcp-server",
            ],
            "env": {
                "EMQX_API_URL": args.emqx_api_url,
                "EMQX_API_KEY": args.emqx_api_key,
                "EMQX_API_SECRET": args.emqx_api_secret,
            },
        },
    ) as server:
        await run(server, instructions, args)

def dir_path(path_str):
    path = Path(path_str)
    if path.is_dir():
        return str(path)
    else:
        raise argparse.ArgumentTypeError(f"'{path_str}' is not a valid directory")

if __name__ == "__main__":
    main()
