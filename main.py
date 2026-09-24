import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    client = OpenAI(
        base_url = "https://openrouter.ai/api/v1",
        api_key=api_key
    )

    response = client.chat.completions.create(
    model="openrouter/free",
    messages=[
        {
            "role": "user",
            "content": "Why is Boot.dev such a great place to learn backend development? Use one paragraph maximum.",
        }
    ],
)

    print(response.choices[0].message.content)

    if response.usage is None:
        raise RuntimeError("API 요청 실패: 토큰 사용량 정보를 불러올 수 없습니다.")

    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Response tokens: {response.usage.completion_tokens}")

    print(f"Response:\n{response.choices[0].message.content}.") 

if __name__ == "__main__":
    main()
