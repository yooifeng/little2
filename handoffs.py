from agents import Agent, Runner
import asyncio

english_agent = Agent(
    name="English agent",
    instructions="You only speak English. When asked about your name, respond with 'My name is Assistant'.",
)

chinese_agent = Agent(
    name="Chinese agent",
    instructions="You only speak Chinese. When asked about your name, respond with '我的名字是助手'.",
)

triage_agent = Agent(
    name="Triage agent",
    instructions="Handoff to the appropriate agent based on the language of the request. If the input is in Chinese, use the Chinese agent. Otherwise, use the English agent.",
    handoffs=[english_agent, chinese_agent],
)

async def main():
    result = await Runner.run(triage_agent, input="你叫什么名字")
    print(result.final_output)
    # Expected output: 我的名字是助手

if __name__ == "__main__":
    asyncio.run(main())
