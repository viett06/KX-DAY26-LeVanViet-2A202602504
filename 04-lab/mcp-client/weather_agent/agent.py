"""
Weather Agent - Connects to Remote MCP Server on Cloud Run
Successfully connects to custom MCP HTTP endpoints!
"""
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from dotenv import load_dotenv
import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ADK web cũng nạp .env, nhưng nạp thêm ở đây để `MCP_SERVER_URL` có hiệu lực
# kể cả khi module được import trực tiếp. Không ghi đè biến đã export trong shell.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Mặc định: server chạy local. Deploy lên Cloud Run thì đặt MCP_SERVER_URL trong .env
# (ví dụ: https://<service>.run.app/mcp). verify_setup.py đọc cùng biến này.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")
# gemini-2.5-flash không còn cho API key mới. Xem chú thích ở bước 01.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

INSTRUCTION = (
    "You are a weather assistant. Always call the MCP tools for live data; "
    "never invent temperatures or conditions. "
    "Use get_current_weather(city) for current conditions, "
    "get_forecast(city, days) for a 1–3 day forecast, "
    "and health_check() when the user asks if the weather service is up. "
    "Reply in the user's language, keep it short, and add one practical tip."
)

logger.info(f"🌐 Initializing weather agent with remote MCP server")
logger.info(f"📡 MCP Server: {MCP_SERVER_URL}")

try:
    # Create connection parameters for the remote MCP server
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,  # Increased timeout for Cloud Run cold starts
    )
    
    # Create the MCP toolset - this will connect to the remote server
    logger.info("🔌 Connecting to MCP server...")
    weather_tools = McpToolset(
        connection_params=connection_params,
    )
    logger.info("✅ MCP toolset created successfully")
    
    # Create the agent with remote MCP tools
    root_agent = Agent(
        name="weather_agent",
        model=MODEL,
        description="Weather agent backed by a remote MCP server.",
        instruction=INSTRUCTION,
        tools=[weather_tools],
    )
    logger.info("✅ Weather agent initialized with remote MCP tools:")
    logger.info("   - get_current_weather(city)")
    logger.info("   - get_forecast(city, days)")
    logger.info("   - health_check()")
    logger.info("🎉 Remote MCP connection successful!")
    
except Exception as e:
    logger.error(f"❌ Failed to connect to remote MCP server: {e}")
    logger.error(f"   Server URL: {MCP_SERVER_URL}")
    import traceback
    traceback.print_exc()
    
    # Create a fallback agent without tools
    logger.warning("⚠️  Creating fallback agent without MCP tools")
    root_agent = Agent(
        name="weather_agent",
        model=MODEL,
        description="Weather agent running without MCP tools.",
        instruction=INSTRUCTION,
    )

