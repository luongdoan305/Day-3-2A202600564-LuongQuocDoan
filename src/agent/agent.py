import ast
import inspect
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgent:
    """
    TripWise ReAct Agent — Thought → Action → Observation → Final Answer.
  """

    FINAL_ANSWER_RE = re.compile(r"Final Answer:\s*(.+)", re.IGNORECASE | re.DOTALL)
    THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\n(?:Action:|Final Answer:)|\Z)", re.IGNORECASE | re.DOTALL)
    ACTION_RE = re.compile(r"Action:\s*(\w+)\s*\((.*)\)\s*$", re.IGNORECASE | re.MULTILINE)

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 8,
        prompt_version: str = "v1",
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.prompt_version = prompt_version
        self.history: List[Dict[str, str]] = []
        self._tool_map: Dict[str, Callable] = {t["name"]: t["func"] for t in tools}

    def get_system_prompt(self) -> str:
        tool_lines = "\n".join(
            [f"- {t['name']}: {t['description']}\n  Example: {t.get('example', '')}" for t in self.tools]
        )
        base_rules = """
You are TripWise — an AI travel planning agent for Vietnam destinations.

RULES:
1. Respond in Vietnamese unless the user writes in English.
2. Use ONLY the tools listed below. Never invent tool names.
3. One Action per step. Wait for Observation before the next Action.
4. Action format (no markdown, no backticks): Action: tool_name(arg1, arg2)
   - Strings in double quotes. Numbers without quotes.
5. After gathering enough data, output exactly one line starting with: Final Answer:
6. Do NOT write "Observation:" yourself — the system injects it after each tool call.

Recommended flow:
When the user asks about hotel, accommodation, room price, hotel cost, or travel budget,
call search_hotels(city, nights). Use the number of overnight stays, not the number of travel days.
Thought → Action (get_weather) → [Observation]
Thought → Action (search_attractions) → [Observation]
Thought → Action (estimate_trip_cost) → [Observation]
Thought → Action (create_itinerary) → [Observation]
Thought → Final Answer: (full day-by-day plan with cost & weather notes)
"""
        v2_extra = """
AGENT v2 — also use when helpful:
- calculate_route_time between two places in your plan
- suggest_restaurants for food preferences
- check_budget_fit(estimated_total, budget) after estimate_trip_cost
- weather_risk_warning before scheduling outdoor activities
Always verify budget with check_budget_fit before Final Answer.
"""
        examples = """
EXAMPLE Action lines:
Action: get_weather("Đà Nẵng", "today")
Action: search_attractions("Đà Nẵng", "biển")
Action: estimate_trip_cost("Đà Nẵng", 3, 2)
Action: create_itinerary("Đà Nẵng", 3, 5000000, "biển")
"""
        prompt = f"""{base_rules}
{ v2_extra if self.prompt_version == "v2" else "" }

AVAILABLE TOOLS:
{tool_lines}

{examples}
"""
        return prompt.strip()

    def run(self, user_input: str) -> str:
        logger.log_event(
            "AGENT_START",
            {"input": user_input, "model": self.llm.model_name, "version": self.prompt_version},
        )

        transcript = f"User request: {user_input}\n"
        steps = 0
        final_answer: Optional[str] = None

        llm_delay = float(os.getenv("LLM_CALL_DELAY_SEC", "0"))

        while steps < self.max_steps:
            if llm_delay > 0 and steps > 0:
                time.sleep(llm_delay)
            result = self.llm.generate(transcript, system_prompt=self.get_system_prompt())
            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )

            content = (result.get("content") or "").strip()
            logger.log_event("AGENT_STEP", {"step": steps + 1, "raw": content[:2000]})

            final_match = self.FINAL_ANSWER_RE.search(content)
            if final_match and "Action:" not in content.split("Final Answer:")[0][-80:]:
                final_answer = final_match.group(1).strip()
                self.history.append({"role": "assistant", "content": content})
                break

            thought = self._extract_thought(content)
            action = self._extract_action(content)

            if action:
                tool_name, args = action
                observation = self._execute_tool(tool_name, args)
                logger.log_event(
                    "TOOL_CALL",
                    {"tool": tool_name, "args": args, "observation": observation[:500]},
                )
                block = (
                    f"{content}\n"
                    f"Observation: {observation}\n"
                )
                transcript += f"\n{block}"
                self.history.append({"thought": thought, "action": tool_name, "observation": observation})
            elif final_match:
                final_answer = final_match.group(1).strip()
                break
            else:
                logger.log_event("PARSE_WARNING", {"step": steps + 1, "message": "No Action or Final Answer"})
                transcript += f"\n{content}\nObservation: Hãy gọi một tool hợp lệ hoặc trả Final Answer.\n"

            steps += 1

        if not final_answer:
            final_answer = (
                "Không hoàn thành trong số bước cho phép. "
                "Vui lòng thử lại với yêu cầu rõ hơn (điểm đến, số ngày, ngân sách)."
            )

        logger.log_event("AGENT_END", {"steps": steps, "version": self.prompt_version})
        return final_answer

    def _extract_thought(self, content: str) -> str:
        m = self.THOUGHT_RE.search(content)
        return m.group(1).strip() if m else ""

    def _extract_action(self, content: str) -> Optional[Tuple[str, tuple]]:
        m = self.ACTION_RE.search(content)
        if not m:
            return None
        name, args_str = m.group(1), m.group(2).strip()
        try:
            parsed = ast.literal_eval(f"({args_str})")
            if not isinstance(parsed, tuple):
                parsed = (parsed,)
            return name, parsed
        except (SyntaxError, ValueError) as e:
            logger.log_event("PARSE_ERROR", {"tool": name, "args": args_str, "error": str(e)})
            return None

    def _execute_tool(self, tool_name: str, args: tuple) -> str:
        func = self._tool_map.get(tool_name)
        if not func:
            return f"Tool '{tool_name}' not found. Available: {', '.join(self._tool_map)}"

        try:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            if len(args) < len(params):
                kwargs = dict(zip(params, args))
                out = func(**kwargs)
            else:
                out = func(*args[: len(params)])
            return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        except Exception as e:
            logger.log_event("TOOL_ERROR", {"tool": tool_name, "error": str(e)})
            return f"Tool error: {e}. Check argument types and count."
