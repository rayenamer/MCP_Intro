import asyncio
import sys
import os
from dotenv import load_dotenv
from contextlib import AsyncExitStack

from mcp_client import MCPClient
from core.claude import Claude
from core.cli_chat import CliChat
from core.cli import CliApp

load_dotenv()

# Anthropic Config
claude_model = os.getenv("CLAUDE_MODEL", "")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

assert claude_model, "Error: CLAUDE_MODEL cannot be empty. Update .env"
assert anthropic_api_key, (
    "Error: ANTHROPIC_API_KEY cannot be empty. Update .env"
)

async def main():
    claude_service = Claude(model=claude_model)
    server_scripts = sys.argv[1:]
    clients = {}

    use_uv = os.getenv("USE_UV", "0") == "1"
    server_script = os.path.abspath("mcp_server.py")

    if use_uv:
        command, args = "uv", ["run", server_script]
    else:
        command, args = sys.executable, [server_script]

    async with AsyncExitStack() as stack:
        doc_client = await stack.enter_async_context(
            MCPClient(command=command, args=args)
        )
        clients["doc_client"] = doc_client

        for i, script in enumerate(server_scripts):
            client_id = f"client_{i}_{script}"
            abs_script = os.path.abspath(script)
            client_command = "uv" if use_uv else sys.executable
            client_args = ["run", abs_script] if use_uv else [abs_script]

            client = await stack.enter_async_context(
                MCPClient(command=client_command, args=client_args)
            )
            clients[client_id] = client

        chat = CliChat(doc_client=doc_client, clients=clients, claude_service=claude_service)
        cli = CliApp(chat)
        await cli.initialize()
        await cli.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
