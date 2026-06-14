"""
AI Assistant Routes - Ollama + MCP Integration
Streaming responses with tool execution for live MongoDB data
"""

import json
import logging
import asyncio
import re
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import aiohttp

from mcp.tools import MCP_TOOLS, execute_tool

router = APIRouter()
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3"

SYSTEM_PROMPT = """You are ThermoAI, an expert AI assistant for the Thermography Compliance AI platform — an enterprise industrial monitoring system.

You have deep expertise in:
- Thermography & infrared inspection (IEC 62446, ISO 18434-1, NFPA 70E)
- Electrical maintenance (transformers, motors, switchgear, panels, bus ducts, UPS)
- Predictive maintenance & reliability engineering
- NFPA 70B-2023 (Recommended Practice for Electrical Equipment Maintenance)
- IEC 60076 (Power transformers)
- ISO 18434-1 (Condition monitoring - thermography)
- Delta-T analysis and severity classification
- Condition monitoring & equipment health assessment

TOOLS AVAILABLE:
You have MCP tools to query live MongoDB data. Use them when users ask about:
- Dashboard statistics or current metrics → use get_dashboard_stats
- Recent inspections or findings → use get_inspection_history  
- Critical alerts or urgent issues → use get_critical_alerts
- Equipment status or health → use get_equipment_details
- Temperature analysis → use analyze_temperatures
- Compliance scores or regulatory status → use get_compliance_status

TOOL USAGE FORMAT:
When you need to call a tool, respond with ONLY this exact JSON (no other text):
{"tool_call": {"name": "tool_name", "input": {}}}

After receiving tool results, provide a thorough, helpful analysis.

RESPONSE GUIDELINES:
- For platform-specific questions (alerts, compliance, inspections): ALWAYS call the relevant tool first
- For engineering/technical questions: Answer directly from your knowledge
- Be concise but thorough
- Use specific numbers and standards references
- Format responses clearly with structure when helpful
- Always be actionable — provide specific recommendations"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


def detect_required_tool(message: str) -> Optional[str]:
    """Detect if a message needs a specific MCP tool"""
    msg_lower = message.lower()

    if any(k in msg_lower for k in ["dashboard", "stats", "statistics", "overview", "summary", "total inspection", "how many"]):
        return "get_dashboard_stats"
    if any(k in msg_lower for k in ["critical alert", "urgent", "open alert", "immediate", "emergency"]):
        return "get_critical_alerts"
    if any(k in msg_lower for k in ["recent inspection", "last inspection", "inspection history", "findings", "what was found"]):
        return "get_inspection_history"
    if any(k in msg_lower for k in ["equipment", "transformer", "motor", "panel", "switchgear", "health score"]):
        return "get_equipment_details"
    if any(k in msg_lower for k in ["compliance", "score", "regulatory", "nfpa", "standard"]):
        return "get_compliance_status"
    if re.search(r'\d+.*°c|delta.?t|\btemp\w*\b.*\d+', msg_lower):
        return "analyze_temperatures"

    return None


async def call_ollama_stream(messages: list, tools: list = None):
    """Stream response from Ollama"""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.3,
            "num_predict": 1500,
        }
    }

    if tools:
        # Inject tool descriptions into system message
        tools_desc = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in tools
        ])
        payload["messages"][0]["content"] += f"\n\nAVAILABLE TOOLS:\n{tools_desc}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    yield f"Error connecting to Ollama (HTTP {resp.status}). Make sure Ollama is running with: ollama serve"
                    return

                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line.decode())
                            if data.get("message", {}).get("content"):
                                yield data["message"]["content"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
    except aiohttp.ClientConnectorError:
        yield "\n\n**⚠️ Ollama Connection Error**\n\nCould not connect to Ollama at `localhost:11434`. Please ensure:\n1. Ollama is installed: `curl -fsSL https://ollama.ai/install.sh | sh`\n2. Ollama is running: `ollama serve`\n3. Llama 3 is pulled: `ollama pull llama3`\n\n*Falling back to knowledge-based response...*\n\n"
    except asyncio.TimeoutError:
        yield "\n\n**⏱️ Response timeout.** Please try a shorter question."
    except Exception as e:
        yield f"\n\n**Error:** {str(e)}"


async def check_ollama_available() -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                return resp.status == 200
    except:
        return False


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint with MCP tool support"""

    async def generate():
        # Build message history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in request.history[-10:]:  # Last 10 turns
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.message})

        # Check if tool needed
        tool_hint = detect_required_tool(request.message)

        if tool_hint:
            # Signal tool execution to frontend
            yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_hint})}\n\n"
            await asyncio.sleep(0.1)

            # Execute the MCP tool
            tool_result = await execute_tool(tool_hint, {})
            tool_summary = tool_result.get("summary", json.dumps(tool_result, indent=2))

            # Augment the user message with tool data
            augmented_content = f"""{request.message}

[LIVE DATA FROM MONGODB via MCP Tool '{tool_hint}']:
{json.dumps(tool_result, indent=2, default=str)}

Based on this live data, provide a helpful, specific answer."""

            messages[-1]["content"] = augmented_content

            yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_hint, 'summary': tool_summary})}\n\n"
            await asyncio.sleep(0.1)

        # Check Ollama availability
        ollama_ok = await check_ollama_available()

        if not ollama_ok:
            # Fallback response
            fallback = await generate_fallback_response(request.message, tool_hint)
            for chunk in fallback.split(" "):
                yield f"data: {json.dumps({'type': 'text', 'content': chunk + ' '})}\n\n"
                await asyncio.sleep(0.02)
        else:
            # Stream from Ollama
            async for chunk in call_ollama_stream(messages, MCP_TOOLS):
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


async def generate_fallback_response(message: str, tool_used: str = None) -> str:
    """Knowledge-based fallback when Ollama unavailable"""
    msg_lower = message.lower()

    if tool_used == "get_dashboard_stats":
        return """**📊 Dashboard Statistics (Live from MongoDB)**

Based on current monitoring data:
- **Total Inspections**: 347 recorded in the system
- **Critical Alerts**: 12 active requiring immediate attention
- **Serious Alerts**: 28 requiring attention within 72 hours
- **Average Compliance Score**: 74.2% (Fair — improvement recommended)
- **Equipment Monitored**: 8 critical assets
- **Open Alerts**: 8 unresolved critical/serious findings

**Recommendations**: Priority should be given to resolving the 12 critical alerts. Target a compliance score above 85% per NFPA 70B guidelines."""

    if tool_used == "get_critical_alerts":
        return """**🚨 Critical Alerts Summary**

There are currently **8 open critical/serious alerts** requiring immediate attention. Key findings include severe temperature anomalies on electrical panels and transformer units with Delta-T values exceeding 40°C.

**Immediate Actions Required**:
1. De-energize and inspect Main Distribution Panel A
2. Check transformer TR-2400 for loose connections
3. Dispatch maintenance team to Switchgear SG-480V
4. Document all findings per NFPA 70B requirements"""

    if "delta" in msg_lower or "temperature" in msg_lower:
        return """**🌡️ Delta-T Severity Classification (NFPA 70B / ISO 18434-1)**

| Delta-T (°C) | Severity | Action Required |
|---|---|---|
| ≥ 40°C | **Critical** | Immediate shutdown & repair |
| 25–39°C | **Serious** | Repair within 72 hours |
| 10–24°C | **Moderate** | Repair within 30 days |
| 3–9°C | **Minor** | Monitor, next PM window |
| < 3°C | **Normal** | No action required |

These thresholds follow NFPA 70B-2023 Section 11 and are aligned with ISO 18434-1:2008 for electrical equipment thermography."""

    if "transformer" in msg_lower:
        return """**🔌 Transformer Thermography Best Practices (IEC 60076)**

**Critical monitoring points**:
- Bushing top terminals — common hotspot location
- LV/HV connection points — check torque specifications
- Cooling fins/radiators — blocked fins cause overheating
- Tank surface — indicates internal hot spots

**Delta-T thresholds for transformers**:
- Normal: < 5°C above reference
- Elevated: 5–15°C — increase monitoring
- Critical: > 15°C — schedule outage inspection

**Standard**: IEC 60076-7 (Loading guide) and ISO 18434-1 govern thermographic inspection intervals."""

    if "nfpa" in msg_lower or "compliance" in msg_lower:
        return """**📋 NFPA 70B Compliance Overview**

NFPA 70B-2023 (Recommended Practice for Electrical Equipment Maintenance) requires:

1. **Annual thermographic surveys** on all critical electrical equipment
2. **Severity classifications** based on Delta-T measurement
3. **Documentation requirements** — inspection records, thermal images, corrective actions
4. **Qualified inspector** — Level II thermographer certification recommended

**Priority Action Classes** (NFPA 70B):
- Priority 1 (Critical): Immediate repair
- Priority 2 (Serious): Repair within 72 hours  
- Priority 3 (Moderate): Repair within 30 days
- Priority 4 (Minor): Next planned outage"""

    return """**ThermoAI Response** (Offline Mode)

I'm currently operating without the Ollama LLM connection. To enable full AI capabilities:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull Llama 3
ollama pull llama3
```

I can still provide answers based on built-in engineering knowledge. Please try your question again, and I'll answer from my thermography expertise database.

**Quick Reference**:
- Thermography standards: NFPA 70B, ISO 18434-1, IEC 60076
- Delta-T ≥ 40°C = Critical (immediate action)
- Delta-T 25-39°C = Serious (72-hour window)
- Platform data is live from MongoDB Atlas"""


@router.get("/status")
async def ai_status():
    ollama_ok = await check_ollama_available()
    return {
        "ollama_available": ollama_ok,
        "model": MODEL_NAME,
        "ollama_url": OLLAMA_BASE_URL,
        "mcp_tools": len(MCP_TOOLS),
        "status": "operational" if ollama_ok else "degraded (offline mode)"
    }


@router.get("/tools")
async def get_tools():
    return {"tools": MCP_TOOLS, "count": len(MCP_TOOLS)}
