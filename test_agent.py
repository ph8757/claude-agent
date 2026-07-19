import os
from anthropic import Anthropic
from dotenv import load_dotenv

# .env 파일에 적힌 키를 파이썬으로 강제 로드
load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("❌ 에러: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
else:
    print("🟢 환경변수 로드 성공! 클로드에게 메시지를 보냅니다...")
    
    # 공식 베이스 URL을 명시적으로 선언하여 주소가 꼬이는 것을 방지합니다.
    client = Anthropic(
        api_key=api_key,
        base_url="https://api.anthropic.com"
    )
    
    try:
        # Anthropic의 가장 표준적인 Claude 3.5 Sonnet 기본 모델 코드로 요청합니다.
        message = client.messages.create(
             model="claude-sonnet-5",
            max_tokens=500,
            
            messages=[
                {"role": "user", "content": "연결 테스트입니다. 확인되었다면 '성공'이라고 대답해주세요."}
            ]
        )
        print("\n🤖 클로드의 응답:")
        print(message.content[0].text)
        print("\n🎉 연결에 최종 성공했습니다!")
        
    except Exception as e:
        print(f"\n❌ API 호출 중 에러가 발생했습니다:\n{e}")
        print("\n💡 [팁] 만약 똑같이 404 에러가 난다면, 현재 발급받으신 API 키가 'sk-ant-'로 시작하는 Anthropic 공식 홈페이지(console.anthropic.com)의 키가 맞는지 다시 한번 확인해 주세요!")