"""Run TripWise real API demo scenarios."""
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent.agent import ReActAgent
from src.core.factory import get_llm_provider
from src.tools.tool_specs import get_tools_v1

DEMO_QUERY = "Tôi muốn đi Đà Nẵng 3 ngày 2 đêm, kiểm tra thời tiết và tìm khách sạn giá tốt"
WEATHER_DEMO_QUERY = "I want to travel to Da Nang this weekend. Check the weather for me."


def main() -> None:
    load_dotenv()
    agent = ReActAgent(llm=get_llm_provider(), tools=get_tools_v1(), max_steps=8)
    for query in (WEATHER_DEMO_QUERY, DEMO_QUERY):
        print(f"Demo: {query}\n")
        print(agent.run(query))
        print()


if __name__ == "__main__":
    main()
