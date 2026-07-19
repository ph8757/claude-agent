import os
import json
import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("❌ 에러: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    exit()

client = Anthropic(api_key=api_key)

# -------------------------------------------------------------
# [1단계] 네이버 페이 증권 크롤러 기능 (Tools) 구현
# -------------------------------------------------------------
def get_naver_market_data(stock_code: str):
    """네이버 금융에서 국내 주식의 실시간 현재가, 전일대비 등락률 등을 크롤링하는 함수"""
    print(f"⚙️ [시스템 실행] 네이버 금융에서 종목코드 '{stock_code}' 실시간 시세 크롤링 중...")
    
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        no_today = soup.find("p", {"class": "no_today"})
        if not no_today:
            return json.dumps({"error": "존재하지 않는 종목코드이거나 페이지 구조가 변경되었습니다."})
        
        current_price = no_today.find("span", {"class": "blind"}).text.replace(",", "")
        
        wrap_company = soup.find("div", {"class": "description"})
        company_name = wrap_company.find("a").text if wrap_company else "국내 주식"
        
        table_blind = soup.find("table", {"class": "no_info"})
        tds = table_blind.find_all("td")
        
        prev_close = tds[0].find("span", {"class": "blind"}).text.replace(",", "")
        open_price = tds[1].find("span", {"class": "blind"}).text.replace(",", "")
        high_price = tds[2].find("span", {"class": "blind"}).text.replace(",", "")
        low_price = tds[3].find("span", {"class": "blind"}).text.replace(",", "")
        
        diff = int(current_price) - int(prev_close)
        change_pct = (diff / int(prev_close)) * 100
        
        data = {
            "company_name": company_name,
            "stock_code": stock_code,
            "current_price": f"{int(current_price):,}원",
            "day_change_pct": f"{change_pct:+.2f}%",
            "open_price": f"{int(open_price):,}원",
            "high_price": f"{int(high_price):,}원",
            "low_price": f"{int(low_price):,}원"
        }
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_naver_financial_indicators(stock_code: str):
    """네이버 금융 기업실적분석 테이블에서 주요 재무 지표(PER, PBR, ROE)를 크롤링하는 함수"""
    print(f"⚙️ [시스템 실행] 네이버 금융에서 종목코드 '{stock_code}'의 주요 재무 지표 추출 중...")
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        aside_tab = soup.find("div", {"class": "aside_invest_info"})
        table = aside_tab.find("table", {"class": "tbl_type1_bnd"})
        
        per, pbr, baedang = "N/A", "N/A", "N/A"
        
        if table:
            th_list = table.find_all("th")
            td_list = table.find_all("td")
            
            for th, td in zip(th_list, td_list):
                title = th.text.strip()
                if "PER" in title and "배" in title:
                    per = td.find("em").text.strip() if td.find("em") else td.text.strip()
                elif "PBR" in title and "배" in title:
                    pbr = td.find("em").text.strip() if td.find("em") else td.text.strip()
                elif "배당수익률" in title:
                    baedang = td.find("em").text.strip() if td.find("em") else td.text.strip()

        financials = {
            "stock_code": stock_code,
            "PER": f"{per}배" if per != "N/A" else "N/A",
            "PBR": f"{pbr}배" if pbr != "N/A" else "N/A",
            "dividend_yield": baedang
        }
        return json.dumps(financials, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def save_analysis_report(filename: str, content: str):
    """최종 투자 전략 보고서를 마크다운 파일로 저장"""
    print(f"⚙️ [시스템 실행] 로컬에 '{filename}' 국내 주식 분석 보고서 생성 완료!")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return json.dumps({"status": "success", "message": "파일이 올바르게 물리적 저장되었습니다."} , ensure_ascii=False)

# Anthropic Tool Spec 매핑 (인자 설명을 더 직관적으로 보완)
tools_spec = [
    {
        "name": "get_naver_market_data",
        "description": "네이버 금융에서 국내 주식 종목코드(6자리 숫자)의 실시간 현재가, 등락률, 시가, 고가, 저가를 크롤링합니다.",
        "input_schema": {
            "type": "object",
            "properties": {"stock_code": {"type": "string", "description": "국내 주식 종목코드 6자리 (예: 삼성전자는 005930, SK하이닉스는 000660)"}},
            "required": ["stock_code"]
        }
    },
    {
        "name": "get_naver_financial_indicators",
        "description": "네이버 금융에서 국내 주식의 현재 기준 PER, PBR, 배당수익률 등 핵심 밸류에이션 데이터를 크롤링합니다.",
        "input_schema": {
            "type": "object",
            "properties": {"stock_code": {"type": "string", "description": "국내 주식 종목코드 6자리"}},
            "required": ["stock_code"]
        }
    },
    {
        "name": "save_analysis_report",
        "description": "생성된 주식 투자 제안 보고서 본문 전체를 로컬 마크다운 파일(.md)로 물리 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "저장할 파일명 (예: 삼성전자_분석보고서.md)"},
                "content": {"type": "string", "description": "에이전트가 작성한 리포트 마크다운 본문 내용 전체 (반드시 표와 텍스트를 포함해야 함)"}
            },
            "required": ["filename", "content"]
        }
    }
]

# -------------------------------------------------------------
# [2단계] ReAct 에이전트 구동 엔진
# -------------------------------------------------------------
target_code = "005930" 
user_request = f"현재 종목코드 '{target_code}' 주식의 실시간 시세와 PER, PBR 지표를 네이버 금융에서 크롤링해와서 정밀 분석해줘. 의견과 데이터를 엑셀 표로 깔끔하게 정리한 뒤 '국내주식_{target_code}_분석보고서.md' 파일로 저장해줘."

conversation_history = [{"role": "user", "content": user_request}]

models_page = client.models.list(limit=5)
selected_model = models_page.data[0].id

SYSTEM_PROMPT = """
너는 국내 주식 시장에 정통한 여의도 증권가의 수석 애널리스트야.
사용자가 6자리 종목코드를 주면 반드시 네이버 금융 크롤러 도구들을 사용해 '실제 실시간 데이터'를 기반으로 분석해야 해.

[중요 보고 규칙]
1. 'get_naver_market_data'와 'get_naver_financial_indicators'로 수집한 모든 수치는 엑셀 표(Markdown Table) 형식으로 이쁘게 정돈해라.
2. 수치 분석이 끝나면 반드시 최종 추천 의견 [매수(Buy) / 보유(Hold) / 매도(Sell)] 중 하나를 근거와 함께 텍스트로 명시해라.
3. 이 모든 표와 텍스트 분석 내용을 통째로 완성한 뒤, 마지막 단계에 'save_analysis_report' 툴을 호출해라.
4. 'save_analysis_report'를 호출할 때, 'content' 매개변수에는 단순 파일명이 아니라 네가 방금 작성한 표와 리포트 내용 '전체'를 문자열로 주입해야 한다. 절대 'content' 자리에 빈 값이나 파일명만 넣지 마라.
"""

max_loops = 5
loop_count = 0

while loop_count < max_loops:
    loop_count += 1
    print(f"\n🔄 [국장 데이터 크롤링 루프 #{loop_count}] 에이전트가 네이버 금융을 스크래핑하는 중...")
    
    response = client.messages.create(
        model=selected_model,
        max_tokens=3500,
        system=SYSTEM_PROMPT,
        tools=tools_spec,
        messages=conversation_history
    )
    
    conversation_history.append({"role": "assistant", "content": response.content})
    
    tool_use_blocks = []
    for block in response.content:
        if block.type == "text":
            print(f"🧠 [에이전트 생각]:\n{block.text}")
        elif block.type == "tool_use":
            tool_use_blocks.append(block)

    if not tool_use_blocks:
        print("\n🎯 [크롤링 및 분석 완료] 에이전트가 최종 작업을 종료했습니다.")
        break
        
    tool_responses = []
    
    for tool_use in tool_use_blocks:
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_id = tool_use.id
        
        if tool_name == "get_naver_market_data":
            result_data = get_naver_market_data(stock_code=tool_input["stock_code"])
        elif tool_name == "get_naver_financial_indicators":
            result_data = get_naver_financial_indicators(stock_code=tool_input["stock_code"])
        elif tool_name == "save_analysis_report":
            filename = tool_input.get("filename", f"국내주식_{target_code}_분석보고서.md")
            
            # 모든 종류의 인자 유실 패턴 방어 고도화
            content = tool_input.get("content") or tool_input.get("report_content") or tool_input.get("text")
            
            if not content or len(content.strip()) < 30:
                # 만약 Claude가 또 본문을 누락시켰다면, 어시스턴트 대화 히스토리에서 가장 마지막으로 뱉었던 보고서 텍스트를 강제로 추출해 바인딩합니다.
                print("⚠️ [시스템 감지] 에이전트가 툴 호출 인자에 본문을 누락하여 대화 히스토리에서 역추적을 시작합니다...")
                for history in reversed(conversation_history):
                    if history["role"] == "assistant":
                        for b in history["content"]:
                            if b.type == "text" and "|" in b.text: # 표가 포함된 텍스트 블록 서치
                                content = b.text
                                break
                
                # 역추적도 실패했을 때를 대비한 최종 백업
                if not content:
                    content = "에이전트가 보고서 본문 매핑에 실패했습니다. 이전 터미널 결과를 확인해 주세요."
            
            result_data = save_analysis_report(filename=filename, content=content)
            
        else:
            result_data = json.dumps({"status": "error", "message": "unknown tool"})
            
        print(f"👀 [크롤러 수집 데이터 ({tool_name})]: {result_data}")
        
        tool_responses.append({
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": result_data
        })
    
    conversation_history.append({
        "role": "user",
        "content": tool_responses
    })

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_gmail_report(subject, body_markdown):
    """지정된 마크다운 보고서를 HTML로 간단히 변환하여 Gmail로 발송하는 함수"""
    sender_email = os.environ.get("GMAIL_USER")
    sender_password = os.environ.get("GMAIL_APP_PASSWORD") # 구글 앱 비밀번호
    
    # 기본 내 메일에다가, 추가 수신자 비밀값이 있다면 뒤에 콤마로 붙여주는 방식
    my_email = os.environ.get("GMAIL_USER")
    extra_emails = os.environ.get("ADDITIONAL_RECEIVERS")
    
    receiver_email = f"{my_email}, {extra_emails}" if extra_emails else my_email
    
    #receiver_email = os.environ.get("GMAIL_USER") # 내 메일로 내가 받기
    
    if not sender_email or not sender_password:
        print("⚠️ [경고] Gmail 환경변수가 세팅되지 않아 메일을 발송하지 않습니다.")
        return

    # 마크다운 텍스트를 이메일에서 읽기 편하게 줄바꿈 처리
    # (더 이쁘게 보려면 간단한 HTML 변환을 거쳐도 좋습니다)
    html_content = f"""
    <html>
      <body>
        <h2>📊 에이전트 국장 정밀 분석 보고서</h2>
        <p>네이버 금융 실시간 스크래핑 결과입니다. VS Code나 마크다운 뷰어에 복사해 넣으시면 표가 활성화됩니다.</p>
        <hr/>
        <pre style="font-family: 'Malgun Gothic', sans-serif; white-space: pre-wrap; background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
{body_markdown}
        </pre>
      </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("📧 [알림] Gmail 분석 보고서가 성공적으로 발송되었습니다!")
    except Exception as e:
        print(f"❌ [메일 에러] 발송 중 오류 발생: {e}")

# ------ 기존 While 루프 끝나는 지점 아래에 배치 ------
print("\n📊 ==================== [프로세스 완료] ====================")
# content 변수에 담긴 최종 마크다운 본문을 수집하여 메일 발송 트리거
if 'content' in locals() and content:
    send_gmail_report(f"🚀 [에이전트 리포트] 삼성전자(005930) 실시간 데이터 분석", content)
    
print("==============================================================")
print("이제 VS Code에서 '국내주식_005930_분석보고서.md' 파일을 다시 클릭해 보세요!")
print("그 상태에서 Ctrl + Shift + V 를 누르시면 완성된 실시간 표가 등장합니다.")
print("==============================================================")