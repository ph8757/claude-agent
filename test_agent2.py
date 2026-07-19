import os
from anthropic import Anthropic
from dotenv import load_dotenv

# .env 파일에 적힌 키를 파이썬으로 강제 로드
load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("❌ 에러: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
else:
    print("🟢 환경변수 로드 성공! 사용 가능한 모델 목록을 조회합니다...")
    
    client = Anthropic(api_key=api_key)
    
    try:
        models_page = client.models.list(limit=5)
        available_models = [m.id for m in models_page.data]
        
        if not available_models:
            print("❌ 사용할 수 있는 모델 목록이 비어 있습니다.")
            exit()
            
        selected_model = available_models[0]
        print(f"🎯 사용할 수 있는 모델 발견: {available_models}")
        print(f"👉 자동으로 [{selected_model}] 모델을 선택하여 에이전트를 실행합니다.\n")
        
        # 에이전트의 행동 규칙 (System Prompt)
        SYSTEM_PROMPT = """
        너는 사용자의 가상 비서이자 프로그래밍 및 데이터 분석 전문 에이전트야.
        반드시 아래의 행동 규칙을 지켜서 답해야 해:
        1. 사용자가 요청한 목표를 달성하기 위해 필요한 단계를 논리적으로 먼저 생각(Thought)한다.
        2. 답변은 명확하고 간결하게 핵심만 전달한다.
        3. 데이터나 일정을 정리할 때는 사용자가 보기 편하도록 반드시 엑셀 표(Markdown Table) 형태로 정리한다.
        """
        
        message = client.messages.create(
            model=selected_model,
            max_tokens=2000,  # 생각 블록이 포함되므로 토큰을 조금 늘려줍니다.
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user", 
                    "content": "오늘 프로젝트 관리 앱 개발 일정을 짜야 해. 요구사항 정의, UI 디자인, API 연동, 테스트까지 총 4단계야. 이쁘게 정리해줘."
                }
            ]
        )
        
        print("🤖 에이전트의 답변:")
        
        # 최신 모델의 'ThinkingBlock'과 'TextBlock'을 안전하게 순회하며 출력합니다.
        for block in message.content:
            if block.type == "text":
                print(block.text)
            elif block.type == "thinking":
                print(f"[에이전트 추론 과정]\n{block.thinking}\n")
                
        print("\n🎉 드디어 에이전트 1단계 구동에 완벽히 성공했습니다!")
        
    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다:\n{e}")