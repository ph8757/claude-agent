import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("❌ 에러: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    exit()

client = Anthropic(api_key=api_key)

# 1. 에이전트가 필요할 때 호출할 실제 파이썬 함수를 정의합니다.
def get_current_weather(location: str):
    """지정된 지역의 실시간 날씨 데이터를 반환하는 함수 (샘플 데이터)"""
    print(f"⚙️ [시스템 실행] 파이썬이 실제로 '{location}'의 날씨 데이터를 조회 중...")
    
    # 실제 환경에서는 여기서 기상청 API 등을 호출하게 됩니다.
    weather_database = {
        "과천": {"temperature": "26°C", "condition": "맑음", "humidity": "45%"},
        "서울": {"temperature": "28°C", "condition": "비", "humidity": "80%"},
        "유후인": {"temperature": "22°C", "condition": "안개", "humidity": "60%"}
    }
    
    # 등록되지 않은 지역은 기본값 반환
    return json.dumps(weather_database.get(location, {"temperature": "24°C", "condition": "정보 없음", "humidity": "50%"},), ensure_ascii=False)

# 2. 클로드에게 "너는 이 도구를 쓸 수 있어"라고 명세를 알려줍니다. (Anthropic Tools 규격)
tools_spec = [
    {
        "name": "get_current_weather",
        "description": "지정된 대한민국 또는 일본 도시의 현재 실시간 날씨(기온, 상태, 습도)를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "날씨를 조회할 도시 이름 (예: 과천, 서울, 유후인)"
                }
            },
            "required": ["location"]
        }
    }
]

print("🟢 에이전트 2단계(도구 연동) 구동 시작...")

try:
    # 에이전트에게 외부 도구를 조회해야만 풀 수 있는 질문을 던집니다.
    user_question = "지금 과천 날씨가 어떤지 확인해서 알려주고, 내가 오늘 외출할 때 조심해야 할 점을 한 줄로 요약해줘."
    print(f"👤 사용자 질문: {user_question}\n")

    # 3. 모델 목록 조회 및 자동 선택 (아까 검증된 방식)
    models_page = client.models.list(limit=5)
    selected_model = models_page.data[0].id

    # 4. 에이전트에게 도구 명세(tools)를 함께 주입하여 호출합니다.
    response = client.messages.create(
        model=selected_model,
        max_tokens=2000,
        tools=tools_spec,  # 👈 도구 쥐여주기!
        messages=[{"role": "user", "content": user_question}]
    )

    # 5. 에이전트가 '도구를 쓰겠다'고 요청했는지 확인합니다.
    tool_use_block = None
    for block in response.content:
        if block.type == "tool_use":
            tool_use_block = block
            break
            
    if tool_use_block:
        print(f"🤖 에이전트의 판단: '이 질문을 풀려면 도구가 필요해!'")
        print(f"🎯 호출할 도구 이름: {tool_use_block.name}")
        print(f"📦 에이전트가 보낸 인자값: {tool_use_block.input}\n")
        
        # 6. 에이전트의 요청대로 실제 파이썬 함수를 실행합니다.
        tool_name = tool_use_block.name
        tool_input = tool_use_block.input
        
        if tool_name == "get_current_weather":
            # 에이전트가 추출한 '과천'이라는 텍스트를 파이썬 함수에 매개변수로 주입
            tool_result = get_current_weather(location=tool_input["location"])
            print(f"💾 파이썬 함수 결과물 추출 완료: {tool_result}\n")
            
            # 7. 실행한 결과 데이터를 다시 에이전트에게 먹여서 최종 답변을 받아냅니다.
            final_response = client.messages.create(
                model=selected_model,
                max_tokens=2000,
                tools=tools_spec,
                messages=[
                    {"role": "user", "content": user_question},     # 원래 질문
                    {"role": "assistant", "content": response.content}, # 도구를 쓰겠다고 한 에이전트의 이전 대화
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_block.id, # 어떤 도구 요청에 대한 답인지 매칭
                                "content": tool_result            # 파이썬이 뱉은 진짜 데이터
                            }
                        ]
                    }
                ]
            )
            
            print("🤖 에이전트의 최종 답변:")
            for block in final_response.content:
                if block.type == "text":
                    print(block.text)
                    
            print("\n🎉 에이전트가 도구를 직접 선택하고 결과를 받아 분석하는 2단계 테스트에 성공했습니다!")
            
    else:
        print("🤖 에이전트가 도구를 쓰지 않고 자체 지식으로 답변했습니다:")
        print(response.content[0].text)

except Exception as e:
    print(f"\n❌ 오류 발생:\n{e}")