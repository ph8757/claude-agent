import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 환경변수 로드
load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("❌ 에러: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    exit()

client = Anthropic(api_key=api_key)

# 1. 분석 대상 반도체 3사 정의
STOCK_TARGETS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "042700": "한미반도체"
}

# -------------------------------------------------------------
# [1단계] 크롤러 및 파일 저장 기능 (Tools) 정의
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
    """네이버 금융 기업실적분석 테이블에서 주요 재무 지표(PER, PBR, 배당수익률)를 크롤링하는 함수"""
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
    print(f"⚙️ [시스템 실행] 로컬에 '{filename}' 주식 분석 보고서 물리 저장 완료!")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return json.dumps({"status": "success", "message": "파일이 올바르게 물리적 저장되었습니다."}, ensure_ascii=False)

# Anthropic Tool Spec 매핑
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
    }
]

# -------------------------------------------------------------
# [2단계] Gmail 발송 기능 구현
# -------------------------------------------------------------
def send_gmail_report(subject, body_markdown):
    """지정된 마크다운 보고서를 HTML로 감싸서 다중 수신처를 포함해 Gmail로 발송하는 함수"""
    sender_email = os.environ.get("GMAIL_USER")
    sender_password = os.environ.get("GMAIL_APP_PASSWORD")
    
    my_email = os.environ.get("GMAIL_USER")
    extra_emails = os.environ.get("ADDITIONAL_RECEIVERS")
    receiver_email = f"{my_email}, {extra_emails}" if extra_emails else my_email
    
    if not sender_email or not sender_password:
        print("⚠️ [경고] Gmail 환경변수가 세팅되지 않아 메일을 발송하지 않습니다.")
        return

    html_content = f"""
    <html>
      <body>
        <h2>📊 에이전트 반도체 3사 실시간 종합 분석 리포트</h2>
        <p>네이버 금융 실시간 데이터 수집 및 Claude 3.5 Sonnet 연동 결과입니다.</p>
        <hr/>
        <div style="font-family: 'Malgun Gothic', sans-serif; white-space: pre-wrap; background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
{body_markdown}
        </div>
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
            server.sendmail(sender_email, [email.strip() for email in receiver_email.split(',')], msg.as_string())
        print("📧 [알림] Gmail 종합 분석 보고서가 성공적으로 발송되었습니다!")
    except Exception as e:
        print(f"❌ [메일 에러] 발송 중 오류 발생: {e}")

# -------------------------------------------------------------
# [3단계] ReAct 에이전트 구동 엔진 및 다중 종목 순회
# -------------------------------------------------------------
def run_integrated_agent():
    # 사용 중인 API 기반 동적 모델 리스트 확인 및 자동 바인딩
    models_page = client.models.list(limit=5)
    selected_model = models_page.data[0].id
    
    SYSTEM_PROMPT = """
    너는 국내 주식 시장에 정통한 여의도 증권가의 수석 애널리스트야.
    제공된 네이버 금융 크롤러 도구들을 사용해 종목의 '실제 실시간 데이터'와 '밸류에이션 지표'를 기반으로 분석해야 해.

    [중요 보고 규칙]
    1. 수집한 모든 수치 데이터는 가독성이 극대화되도록 반드시 '엑셀 표(Markdown Table)' 형식으로 깔끔하게 정리해라.
    2. 데이터 분석 결과를 바탕으로 최종 투자 의견 [매수(Buy) / 보유(Hold) / 매도(Sell)] 중 하나를 강력한 근거와 함께 텍스트로 명시해라.
    3. 전문적인 수석 애널리스트 수준의 간결하고 핵심적인 한 줄 평 인사이트를 포함해라.
    """
    
    combined_reports = ""
    
    # 순차적으로 3개 반도체 종목 루프 실행
    for stock_code, stock_name in STOCK_TARGETS.items():
        print(f"\n🔄 [종목 분석 시작] {stock_name}({stock_code}) 분석 루프 기동...")
        
        user_request = f"현재 '{stock_name}(종목코드: {stock_code})' 주식의 실시간 시세와 PER, PBR 지표를 도구를 통해 크롤링해와서 정밀 분석해줘. 분석 결과를 엑셀 표 스타일로 일목요연하게 정리해 줘."
        conversation_history = [{"role": "user", "content": user_request}]
        
        max_loops = 4
        loop_count = 0
        single_report = ""
        
        while loop_count < max_loops:
            loop_count += 1
            response = client.messages.create(
                model=selected_model,
                max_tokens=2500,
                system=SYSTEM_PROMPT,
                tools=tools_spec,
                messages=conversation_history
            )
            
            conversation_history.append({"role": "assistant", "content": response.content})
            
            tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
            text_blocks = [block for block in response.content if block.type == "text"]
            
            for block in text_blocks:
                if "|" in block.text or "투자 의견" in block.text:
                    single_report = block.text
            
            if not tool_use_blocks:
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
                else:
                    result_data = json.dumps({"status": "error", "message": "unknown tool"})
                    
                print(f"👀 [크롤러 데이터 확보 ({tool_name})]: {result_data}")
                
                tool_responses.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_data
                })
            
            conversation_history.append({
                "role": "user",
                "content": tool_responses
            })
            
        # 단일 종목 결과 누적
        combined_reports += f"\n## 📈 {stock_name} ({stock_code}) 종합 분석 보고서\n"
        combined_reports += single_report if single_report else "보고서 생성 실패"
        combined_reports += "\n\n<hr style='border: 1px dashed #bbb;' />\n"

    # [4단계] 종합 결과 처리 (로컬 물리 파일 저장 및 Gmail 단 한 통으로 결합 발송)
    if combined_reports:
        print("\n📊 ==================== [종합 데이터 가공 및 전송] ====================")
        # 1. 로컬 마크다운 파일로 물리적 저장 완료
        save_analysis_report("반도체3사_종합분석보고서.md", combined_reports)
        
        # 2. 통합 리포트를 Gmail로 최종 전송
        send_gmail_report("🚀 [에이전트 리포트] 반도체 3사(삼전/하이닉스/한미) 실시간 종합 분석", combined_reports)
        print("==============================================================")

if __name__ == "__main__":
    run_integrated_agent()