# 핵심 요약: OpenAI API 클라이언트를 통해 LLM 추론과 도구 실행 결과를 대화 문맥(messages)에 누적하며 최대 20회 반복 내에 최종 답변을 도출하는 에이전트 피드백 루프 구현체.

import argparse
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
from prompts import system_prompt

# call_function.py 모듈에서 도구 스키마(available_functions)와 함수 디스패처(call_function)를 임포트함
from call_function import available_functions, call_function


def main():
    # dotenv.load_dotenv(): .env 파일에 정의된 환경 변수를 운영체제 프로세스 환경(os.environ)으로 로드함
    load_dotenv()
    
    # os.environ.get(): API 인증을 위한 OPENROUTER_API_KEY 환경변수 값을 조회하며 미설정 시 None을 반환함
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if api_key is None:
        # 인증 키가 누락된 경우 런타임 예외를 발생시켜 비인가 통신 시도를 방지함
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    # argparse.ArgumentParser: 명령줄(CLI) 인터페이스 인자 구문 분석기를 생성함
    parser = argparse.ArgumentParser(description="Chatbot")
    # 위치 인자(positional argument): 사용자의 질문/지시사항 문자열(user_prompt)을 필수 인자로 등록함
    parser.add_argument("user_prompt", type=str, help="User prompt")
    # 옵션 플래그(--verbose): 부가적인 상세 디버깅 정보 출력 여부를 부울(Boolean) 값으로 제어함
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # OpenAI 공식 Python SDK 규격: Base URL과 API Key를 전달하여 OpenRouter 프록시 엔드포인트에 접속하는 클라이언트를 초기화함
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # 대화 기록(Context) 초기화: 시스템 프롬프트(Role: system)와 사용자 첫 발화(Role: user)를 리스트에 순차적으로 구성함
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    # 무한 루프로 인한 끝없는 공회전과 토큰 낭비를 방지하기 위한 최대 반복 상한선 (과제 가이드라인: 20회)
    max_iterations = 20

    # Python built-in range(20): 0부터 19까지 순회하며 모델 추론과 도구 실행 결과를 반복 피드백함
    for _ in range(max_iterations):
        # client.chat.completions.create(): /chat/completions 엔드포인트로 Stateless HTTP 요청을 전송함
        # 누적된 messages 리스트 전체를 전달하여 모델이 이전 턴의 모든 발화 및 도구 실행 결과를 기억하도록 함
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=messages,
            tools=available_functions,
        )

        # ChatCompletionChoice 객체의 첫 번째 선택지에서 ChatCompletionMessage 인스턴스를 추출함
        # 모델의 발화 내용(content) 및 함수 호출 요청(tool_calls) 메타데이터가 담겨 있음
        message = response.choices[0].message

        # [과제 요구사항 2]: 모델의 어시스턴트 응답을 messages 목록에 즉시 추가(append)함
        # 이유: 모델이 직전에 자신이 내린 결정(tool_calls 포함)을 다음 루프 턴에서 반드시 인지해야 대화 문맥 정합성이 유지됨
        messages.append(message)

        # [과제 요구사항 4]: 모델이 더 이상 도구 호출(tool_calls)을 요청하지 않은 경우 (최종 응답 완성)
        if not message.tool_calls:
            # 최종 도출된 답변 문자열(content)을 콘솔에 출력함
            print(message.content)
            # 에이전트의 작업이 완료되었으므로 main() 함수를 정상 종료(루프 탈출)함
            return

        # [과제 요구사항 3]: 모델이 요청한 각 도구 호출을 순회하며 실행 및 결과 피드백을 진행함
        for tool_call in message.tool_calls:
            # call_function() 디스패처에 tool_call 인스턴스를 전달하여 파이썬 로컬 함수를 실행함
            # verbose 플래그를 넘겨 " - Calling function: ..." 출력 및 디버그 로깅을 동기화함
            result_message = call_function(tool_call, verbose=args.verbose)

            # 도구 실행 결과 검증: 함수 실행 결과(content)가 누락되거나 비어 있는지 확인하여 런타임 오작동을 차단함
            content = result_message.get("content")
            if not content:
                raise ValueError(
                    f"Function call returned empty content for tool call ID: {tool_call.id}"
                )

            # verbose 플래그 활성화 시 실행 결과 내용을 콘솔에 출력함 (CLI 과제 규격 대응)
            if args.verbose:
                print(f"-> {content}")

            # [과제 요구사항 3 - 순서 준수]: assistant 메시지가 추가된 직후, 각 tool_call에 매핑되는 도구 메시지를 messages에 추가함
            # result_message 구조: {"role": "tool", "tool_call_id": tool_call.id, "content": "..."}
            # OpenAI API 사양상 다음 어시스턴트 턴 호출 전 모든 tool_call.id에 1:1 대응하는 tool 역할 메시지가 대화 기록에 누적되어야 함
            messages.append(result_message)

    # [과제 요구사항 5]: 최대 반복 횟수(20회)에 도달할 때까지 최종 응답(return)을 내놓지 못한 경우
    # 표준 에러(stderr)에 원인 메시지를 출력하고 비정상 종료 코드 1(sys.exit(1))을 운영체제에 반환함
    sys.stderr.write(f"Error: Agent exceeded maximum iterations ({max_iterations}) without reaching a final response.\n")
    sys.exit(1)


if __name__ == "__main__":
    main()