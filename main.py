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


async def run(mcp_server: MCPServer, instructions: str):
    session = PromptSession(
        message="rule-sql-agent> "
    )

    # Get all the topics from the EMQX server
    agent = Agent(
        name="Assistant",
        instructions=instructions,
        mcp_servers=[mcp_server],
        model="gpt-4o",
    )

    agent_input = []

    while True:
        user_input = session.prompt(in_thread=True).strip()
        agent_input.append({"role": "user", "content": extend_prompt(user_input)})

        result = await Runner.run(agent, agent_input)
        print(result.final_output)
        agent_input = result.to_input_list()


async def main(instructions: str):
    async with MCPServerStdio(
        name="EMQX helper server",
        params={
            "command": "uv",
            "args": [
                "--directory",
                "/Users/av/emqx/emqx-mcp-server",
                "run",
                "emqx-mcp-server",
            ],
            "env": {
                "EMQX_API_URL": "http://localhost:18083/api/v5",
                "EMQX_API_KEY": "key",
                "EMQX_API_SECRET": "secret",
            },
        },
    ) as server:
        await run(server, instructions)


if __name__ == "__main__":
    try:
        asyncio.run(main(instructions()))
    except KeyboardInterrupt:
        print("Goodbye!")
