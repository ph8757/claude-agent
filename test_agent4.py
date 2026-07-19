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

# -------------------------------------------------------------
# [도구 정의] 에이전트가 사용할 2가지 파이썬 함수
# -------------------------------------------------------------
def get_stock_price(ticker: str):
    """특정 주식의 현재가(달러)를 조회하는 함수"""
    print(f"⚙️ [시스템 실행] 파이썬이 '{ticker}' 주식 시세를 실시간 조회 중...")
    mock_prices = {"TSLA": 250.0, "NVDA": 130.0, "QQQ": 480.0}
    price = mock_prices.get(ticker.upper(), 100.0)
    return json.dumps({"ticker": ticker, "current_price": price})

def calculate_portfolio_value(ticker: str, shares: int, current_price: float):
    """현재 보유 수량과 가격을 곱해 평가 금액을 계산하는 함수"""
    print(f"⚙️ [시스템 실행] 파이썬이 계산기 가동 중: {ticker} {shares}주 × ${current_price}...")
    total_value = shares * current_price
    return json.dumps({"ticker": ticker, "total_value": total_value})

# 클로드에게 제공할 도구 명세 명시
tools_spec = [
    {
        "name": "get_stock_price",
        "description": "특정 주식 종목(Ticker)의 실시간 현재가(달러)를 조회합니다. (예: TSLA, NVDA)",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "주식 티커 기호"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "calculate_portfolio_value",
        "description": "보유 주식 수량과 현재가를 기반으로 총 평가 자산 가치를 계산합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "주식 티커"},
                "shares": {"type": "integer", "description": "보유 주식 수량"},
                "current_price": {"type": "number", "description": "현재 주가 (달러)"}
            },
            "required": ["ticker", "shares", "current_price"]
        }
    }
]

# -------------------------------------------------------------
# [핵심] ReAct 루프 실행 엔진
# -------------------------------------------------------------
print("🟢 에이전트 3단계(ReAct 루프 엔진) 가동...")

# 복합적인 연쇄 작업이 필요한 질문
user_task = "내가 현재 테슬라(TSLA) 주식을 4주 가지고 있어. 현재 시세를 조회한 뒤, 내 총 테슬라 평가 금액이 얼마인지 계산해서 엑셀 표(Markdown) 형태로 깔끔하게 요약해 줘."
print(f"👤 사용자 요청: {user_task}\n")

# 대화 기록을 누적할 리스트 (여기에 생각, 행동, 결과가 차곡차곡 쌓여 루프가 돌아갑니다)
conversation_history = [{"role": "user", "content": user_task}]

# 가용한 모델 자동 선택
models_page = client.models.list(limit=5)
selected_model = models_page.data[0].id

# 에이전트에게 생각 프로세스를 강제하는 시스템 프롬프트
SYSTEM_PROMPT = """
너는 철저하게 논리적으로 움직이는 투자 분석 에이전트야.
목표를 달성할 때까지 다음 ReAct 프로세스를 무한히 반복해야 해:
1. 사용자의 요청을 분석하고 다음 단계에 무엇을 해야 할지 '생각(Thought)'한다.
2. 조회가 필요하다면 제공된 도구를 '행동(Action)'으로 호출한다.
3. 도구 결과가 돌아오면 이를 '관찰(Observation)'하고, 목표가 달성될 때까지 다음 행동을 취한다.
4. 모든 정보가 완벽히 수집되면 최종 결과를 엑셀 표(Markdown Table) 형식으로 정돈하여 사용자에게 보고한다.
"""

MAX_LOOPS = 5  # 무한 루프 방지 안전장치
loop_count = 0

while loop_count < MAX_LOOPS:
    loop_count += 1
    print(f"🔄 [ReAct Loop #{loop_count}] 에이전트가 생각 중...")
    
    # 1. 현재까지의 대화 기록과 도구 명세를 함께 서버로 전송
    response = client.messages.create(
        model=selected_model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=tools_spec,
        messages=conversation_history
    )
    
    # 에이전트의 응답을 대화 기록에 누적 (이래야 다음 루프 때 본인이 뭘 했는지 기억함)
    conversation_history.append({"role": "assistant", "content": response.content})
    
    # 2. 에이전트가 텍스트로 생각한 내용이 있다면 출력
    tool_use_block = None
    for block in response.content:
        if block.type == "text":
            print(f"🧠 [에이전트의 생각]:\n{block.text}\n")
        elif block.type == "thinking":
            print(f"🧠 [에이전트 추론 내부 과정]:\n{block.thinking}\n")
        elif block.type == "tool_use":
            tool_use_block = block

    # 3. 만약 도구를 쓰라는 요청(Action)이 없다면 ➡️ 루프 종료 (최종 답변 도달)
    if not tool_use_block:
        print("🎯 [목표 달성] 에이전트가 최종 결론에 도달했습니다.")
        break
        
    # 4. 도구를 쓰라는 요청이 있다면 파이썬 함수 매핑 실행
    tool_name = tool_use_block.name
    tool_input = tool_use_block.input
    tool_id = tool_use_block.id
    
    print(f"🎬 [에이전트의 행동]: 도구 '{tool_name}' 호출 요청")
    print(f"📦 매개변수: {tool_input}")
    
    # 실제 파이썬 기능 분기 실행
    if tool_name == "get_stock_price":
        result_data = get_stock_price(ticker=tool_input["ticker"])
    elif tool_name == "calculate_portfolio_value":
        result_data = calculate_portfolio_value(
            ticker=tool_input["ticker"],
            shares=tool_input["shares"],
            current_price=tool_input["current_price"]
        )
    else:
        result_data = json.dumps({"error": "알 수 없는 도구"})
        
    print(f"👀 [시스템 관찰 결과]: {result_data}\n" + "-"*40)
    
    # 5. 도구 실행 결과(Observation)를 대화 기록에 추가하여 다음 루프의 인풋으로 준비
    conversation_history.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_data
            }
        ]
    })

print("\n📊 ==================== [에이전트 최종 보고서] ====================")
# 대화 기록의 맨 마지막 텍스트 블록 출력
for block in conversation_history[-1]["content"]:
    if block.type == "text":
        print(block.text)
print("==================================================================")
print("\n🎉 스스로 판단하고 체이닝하는 ReAct 루프 에이전트 구현 성공!")