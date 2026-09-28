from functions.get_files_info import get_files_info
from functions.get_file_content import get_file_content
from functions.run_python_file import run_python_file
from functions.write_file import write_file

schema_get_files_info = {
    # 1. 도구의 종류를 명시 (OpenAI 규격상 현재는 "function" 고정)
    "type": "function",

    "function": {
        # 2. 호출할 함수의 고유 이름
        # LLM이 이 도구를 쓰기로 결정하면 응답의 tool_call.function.name으로 이 문자열을 반환합니다.
        "name": "get_files_info",

        # 3. 함수가 하는 일 (가장 중요)
        # LLM은 사용자의 질문과 이 description을 비교해서 "지금 이 함수를 써야 하는가?"를 판단합니다.
        # "작업 디렉터리 기준 상대 경로의 파일 목록, 파일 크기, 디렉터리 여부를 반환한다"고 명시되어 있습니다.
        "description": "Lists files in a specified directory relative to the working directory, providing file size and directory status",

        # 4. 함수에 넘겨줄 인자(arguments)의 규격
        "parameters": {
            # 인자들을 담는 컨테이너 타입은 항상 "object" (파이썬의 딕셔너리/JSON 객체 형태)
            "type": "object",

            # 5. 실제로 전달받을 매개변수 목록 정의
            "properties": {
                "directory": {
                    # 인자의 타입 (문자열)
                    "type": "string",
                    # 인자의 의미와 사용법
                    # "작업 디렉터리 기준 조회할 상대 경로 (기본값은 작업 디렉터리 자체)"
                    "description": "Directory path to list files from, relative to the working directory (default is the working directory itself)",
                },
            },
        },
    },
}

# [1] get_file_content 스키마 정의
# - 특정 파일 경로(file_path)를 받아 해당 파일의 텍스트 본문을 읽어오는 도구입니다.
schema_get_file_content = {
    "type": "function",
    "function": {
        "name": "get_file_content",
        "description": "Reads and returns the full text content of a specified file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file that should be read (e.g., 'main.py').",
                },
            },
            # 파일 경로가 없으면 읽을 수 없으므로 필수 필드로 지정
            "required": ["file_path"],
        },
    },
}

# [2] run_python_file 스키마 정의
# - 실행할 파이썬 파일 경로와 선택적 CLI 인수(args)를 전달받아 실행하는 도구입니다.
schema_run_python_file = {
    "type": "function",
    "function": {
        "name": "run_python_file",
        "description": "Executes a specified Python file and returns its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the Python file to execute.",
                },
                # 여러 개의 인자를 받을 수 있도록 array 타입을 사용하며, 각 원소는 string입니다.
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional command-line arguments to pass to the Python script.",
                },
            },
            # args는 선택 사항(optional)이므로 file_path만 필수로 지정
            "required": ["file_path"],
        },
    },
}

# [3] write_file 스키마 정의
# - 파일 경로와 저장할 내용(content)을 받아 파일에 작성하거나 덮어쓰는 도구입니다.
schema_write_file = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Writes text content to a specified file. Overwrites the file if it already exists.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file that should be written or overwritten.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            # 파일 경로와 작성할 내용 둘 다 반드시 필요하므로 모두 required에 등록
            "required": ["file_path", "content"],
        },
    },
}

# ----------------------------------------------------
# 3. 사용 가능한 함수 목록 업데이트 (과제 2번)
# ----------------------------------------------------
# 4개의 스키마 객체 자체가 이미 type/function 구조를 갖추고 있으므로 그대로 리스트에 담습니다.
available_functions = [
    schema_get_files_info,
    schema_get_file_content,
    schema_run_python_file,
    schema_write_file,
]

# [핵심 요약]: LLM이 요청한 "함수 이름"과 "JSON 인자"를 받아 실제 파이썬 함수를 찾아 실행하고, 그 결과를 LLM 표준 도구 메시지(dict)로 포장하여 반환하는 실행 엔진(Dispatcher)

from collections.abc import Callable
import json

# ==============================================================================
# [준비 단계: 이름표와 실제 도구를 짝지어 두는 딕셔너리]
# ==============================================================================
# LLM은 문자열("get_file_content")만 보낼 수 있지 파이썬 함수 객체를 직접 실행할 수 없습니다.
# 따라서 "문자열 이름(Key)"을 넣으면 "실제 실행 가능한 함수 객체(Value)"가 튀어나오도록 교환소를 미리 만듭니다.
# 딕셔너리를 사용하면 if/elif 문을 수십 개 나열할 필요 없이 O(1)의 속도로 즉시 함수를 찾을 수 있습니다.
function_map: dict[str, Callable[..., str]] = {
    "get_files_info": get_files_info,  # 예: "get_files_info"가 오면 get_files_info() 함수 실행
    "get_file_content": get_file_content,  # 예: "get_file_content"가 오면 get_file_content() 함수 실행
    "run_python_file": run_python_file,  # 예: "run_python_file"이 오면 run_python_file() 함수 실행
    "write_file": write_file,  # 예: "write_file"이 오면 write_file() 함수 실행
}


# ==============================================================================
# [실행 단계: call_function 동작 흐름]
# ==============================================================================
def call_function(tool_call, verbose: bool = False) -> dict:

    # --------------------------------------------------------------------------
    # 1. 메타데이터 추출 및 JSON 문자열 파싱 (데이터 변환)
    # --------------------------------------------------------------------------
    # tool_call 객체 안에서 세 가지 필수 요소를 확인합니다.
    # 1) 어떤 함수를 부를지: tool_call.function.name (문자열)
    # 2) 어떤 답변 번호표인지: tool_call.id (나중에 LLM이 자기 요청과 매칭할 때 쓰는 고유 ID)
    function_name = tool_call.function.name
    tool_call_id = tool_call.id

    # LLM이 보낸 인자(tool_call.function.arguments)는 파이썬 dict가 아닌 단순 'JSON 문자열'입니다.
    # 예: '{"file_path": "lorem.txt"}'
    # 따라서 json.loads()를 써서 파이썬 딕셔너리 형태 {'file_path': 'lorem.txt'} 로 변환해야 파이썬 함수에 넣을 수 있습니다.
    # [or "{}"를 붙인 이유]: 인자가 필요 없는 함수이거나 모델이 None 또는 빈 문자열("")을 보낼 때,
    # json.loads()가 터지는(JSONDecodeError) 현상을 막고 안전하게 빈 딕셔너리({})로 처리하기 위한 방어 코드입니다.
    function_args = json.loads(tool_call.function.arguments or "{}")

    # --------------------------------------------------------------------------
    # 2. 콘솔 로깅 (사람이 터미널에서 진행 상황 확인)
    # --------------------------------------------------------------------------
    # --verbose 옵션이 켜져 있으면 인자 목록까지 상세히 출력하고,
    # 꺼져 있으면 깔끔하게 함수 이름만 터미널에 표시하여 현재 에이전트의 행동을 모니터링합니다.
    if verbose:
        print(f" - Calling function: {function_name}({function_args})")
    else:
        print(f" - Calling function: {function_name}")

    # --------------------------------------------------------------------------
    # 3. 화이트리스트 검증 및 에러 처리 (보안 및 안전망)
    # --------------------------------------------------------------------------
    # LLM이 환각(Hallucination)을 일으켜 우리가 만든 적도 없는 이상한 함수명(예: "hack_computer")을 보낼 수 있습니다.
    # 프로그램 전체가 crash(비정상 종료)되지 않도록, 매핑 테이블에 없는 이름이면 즉시 에러 도구 메시지를 LLM에게 반환합니다.
    # 이렇게 하면 LLM이 "아, 내가 잘못된 함수를 불렀구나" 하고 스스로 인지할 수 있습니다.
    if function_name not in function_map:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": f"Error: Unknown function: {function_name}",
        }

    # --------------------------------------------------------------------------
    # 4. 보안 경로 주입 (Argument Injection - 중요!)
    # --------------------------------------------------------------------------
    # LLM에게 로컬 컴퓨터의 실제 디렉터리 경로를 알려주면 보안상 위험하고 모델이 헷갈릴 수 있습니다.
    # 따라서 LLM이 파일명만 전달하더라도, 파이썬 코드가 강제로 기준 디렉터리를 "./calculator"로 집어넣어 줍니다.
    # 결과적으로 function_args는 {'file_path': 'lorem.txt', 'working_directory': './calculator'} 가 되어
    # 함수가 안전하게 지정된 격리 폴더(샌드박스) 내부에서만 파일을 조작하도록 제한합니다.
    function_args["working_directory"] = "./calculator"

    # --------------------------------------------------------------------------
    # 5. 실제 파이썬 함수 실행 (동적 디스패치 & kwargs 언패킹)
    # --------------------------------------------------------------------------
    # 1) 이름으로 함수 객체 찾기:
    #    target_function = function_map["get_file_content"]  -> 실제 get_file_content 함수 객체를 꺼냄
    target_function = function_map[function_name]

    # 2) **function_args (키워드 언패킹)로 실행:
    #    target_function(**{'file_path': 'lorem.txt', 'working_directory': './calculator'})
    #    은 실제로 get_file_content(file_path="lorem.txt", working_directory="./calculator") 와 동일하게 실행됩니다.
    # 3) 반환된 문자열(예: 파일 내용, 테스트 결과 텍스트)을 result 변수에 저장합니다.
    result = target_function(**function_args)

    # --------------------------------------------------------------------------
    # 6. LLM 규격 도구 메시지(Tool Message) 생성 및 반환
    # --------------------------------------------------------------------------
    # 모델에 결과를 보낼 때는 OpenAI/OpenRouter 규약에 맞는 3개 키를 가진 딕셔너리로 감싸서 리턴해야 합니다.
    # - role: "tool" -> "이것은 시스템이나 유저가 아니라 도구(함수)가 일한 결과물이다"라는 것을 모델에 알림
    # - tool_call_id: 처음에 모델이 발급해 준 접수 번호표 ID -> 모델이 "내가 아까 시킨 그 작업의 결과군" 하고 인식
    # - content: 실제 함수가 작업하고 돌려준 문자열 결과 텍스트
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": result,
    }