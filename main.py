import asyncio
import logging

import agents
from agents import Agent, Runner
from agents.mcp import MCPServer, MCPServerStdio
from prompt_toolkit import PromptSession

logging.basicConfig(level=logging.WARNING)
logging.getLogger("openai.agents").setLevel(logging.WARNING)
agents.run.RunConfig.tracing_disabled = True


def instructions():
    syntax = open("/Users/av/emqx/emqx-docs/en_US/data-integration/rule-sql-syntax.md").read()

    return f"""
    You help to compose an SQL statement for the EMQX Rule Engine.

    The rules for the SQL statements are as follows:
    {syntax}
    """


def extend_prompt(user_input: str):
    return f"""
    Please help to compose an SQL statement for the EMQX Rule Engine.
    {user_input}

    Use the validate_sql tool to validate the SQL statement before providing the final answer.

    For validation with validate_sql tool, provide samples that are expected to match
    and samples that are expected to not match the SQL statement.

    In case of success, provide the final SQL statement only, without any additional text.
    """


async def run(mcp_server: MCPServer, instructions: str):
    session = PromptSession(message="rule-sql-agent> ")

    # Get all the topics from the EMQX server
    agent = Agent(
        name="Assistant",
        instructions=instructions,
        mcp_servers=[mcp_server],
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
