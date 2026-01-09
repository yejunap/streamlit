import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import json

# 페이지 설정
st.set_page_config(
    page_title="Polymarket 차익거래 모니터링",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #6366f1;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .opportunity-card {
        background: #f8fafc;
        border-left: 4px solid #10b981;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .sure-win {
        border-left-color: #10b981;
        background: #f0fdf4;
    }
    .value-bet {
        border-left-color: #f59e0b;
        background: #fffbeb;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'monitoring' not in st.session_state:
    st.session_state.monitoring = False
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# Polymarket API 함수들
@st.cache_data(ttl=30)
def fetch_markets_gamma():
    """Gamma API를 통해 마켓 데이터 가져오기"""
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            'limit': 50,
            'active': 'true',
            'closed': 'false'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Gamma API 오류: {str(e)}")
        return []

@st.cache_data(ttl=30)
def fetch_markets_clob():
    """CLOB API를 통해 마켓 데이터 가져오기 (대체 방법)"""
    try:
        url = "https://clob.polymarket.com/markets"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # 활성 마켓만 필터링
        return [m for m in data if m.get('active') and not m.get('closed')]
    except Exception as e:
        st.error(f"CLOB API 오류: {str(e)}")
        return []

def process_markets(raw_markets, api_type='gamma'):
    """마켓 데이터 처리"""
    processed = []
    
    for market in raw_markets:
        try:
            if api_type == 'gamma':
                # Gamma API 형식
                prices = market.get('outcomePrices', ['0.5', '0.5'])
                processed.append({
                    'id': market.get('id'),
                    'question': market.get('question', 'N/A'),
                    'slug': market.get('slug', ''),
                    'yes_price': float(prices[0]) if prices[0] else 0.5,
                    'no_price': float(prices[1]) if len(prices) > 1 and prices[1] else 0.5,
                    'volume': float(market.get('volume', 0)),
                    'liquidity': float(market.get('liquidity', 0)),
                    'end_date': market.get('endDate', 'N/A'),
                    'url': f"https://polymarket.com/event/{market.get('slug', '')}"
                })
            else:
                # CLOB API 형식
                tokens = market.get('tokens', [])
                yes_price = float(tokens[0].get('price', 0.5)) if tokens else 0.5
                no_price = float(tokens[1].get('price', 0.5)) if len(tokens) > 1 else 0.5
                
                processed.append({
                    'id': market.get('condition_id'),
                    'question': market.get('question', 'N/A'),
                    'slug': market.get('slug', ''),
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'volume': float(market.get('volume', 0)),
                    'liquidity': float(market.get('liquidity', 0)),
                    'end_date': market.get('end_date_iso', 'N/A'),
                    'url': f"https://polymarket.com/event/{market.get('slug', '')}"
                })
        except Exception as e:
            continue
    
    return processed

def find_arbitrage_opportunities(markets, min_profit_pct=2.0, max_investment=100):
    """차익거래 기회 찾기"""
    opportunities = []
    
    for market in markets:
        total_price = market['yes_price'] + market['no_price']
        
        # 유동성 체크
        available_liquidity = min(market['liquidity'] * 0.1, max_investment)
        if available_liquidity < 10:  # 최소 $10
            continue
        
        investment = min(max_investment, available_liquidity)
        
        # Type 1: Sure Arbitrage (Yes + No < 0.98)
        if total_price < 0.98:
            yes_shares = (investment * 0.5) / market['yes_price']
            no_shares = (investment * 0.5) / market['no_price']
            guaranteed_return = min(yes_shares, no_shares)
            profit = guaranteed_return - investment
            profit_pct = (profit / investment) * 100
            
            if profit_pct >= min_profit_pct:
                opportunities.append({
                    'type': '🟢 Sure Win',
                    'question': market['question'],
                    'strategy': 'Buy both Yes & No',
                    'yes_price': market['yes_price'],
                    'no_price': market['no_price'],
                    'total_price': total_price,
                    'investment': investment,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'risk': 'None',
                    'liquidity': market['liquidity'],
                    'url': market['url'],
                    'action': f"Buy ${investment/2:.2f} Yes @ ${market['yes_price']:.3f} + ${investment/2:.2f} No @ ${market['no_price']:.3f}"
                })
        
        # Type 2: Overpriced Market (Yes + No > 1.02)
        elif total_price > 1.02:
            profit = investment * (total_price - 1) * 0.8  # 수수료 고려
            profit_pct = (profit / investment) * 100
            
            if profit_pct >= min_profit_pct:
                opportunities.append({
                    'type': '🟡 Overpriced',
                    'question': market['question'],
                    'strategy': 'Provide liquidity or short both',
                    'yes_price': market['yes_price'],
                    'no_price': market['no_price'],
                    'total_price': total_price,
                    'investment': investment,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'risk': 'Low',
                    'liquidity': market['liquidity'],
                    'url': market['url'],
                    'action': f"Total price: ${total_price:.3f} (>{1.0:.3f})"
                })
        
        # Type 3: Extreme Value Bet
        elif (market['yes_price'] < 0.15 or market['yes_price'] > 0.85) and market['liquidity'] > 5000:
            expected_value = 0.25 if market['yes_price'] < 0.15 else 0.75
            profit = investment * abs(expected_value - market['yes_price'])
            profit_pct = (profit / investment) * 100
            
            if profit_pct >= min_profit_pct * 2:  # Higher threshold
                side = 'Yes' if market['yes_price'] < 0.15 else 'No'
                opportunities.append({
                    'type': '🟠 Value Bet',
                    'question': market['question'],
                    'strategy': f'Buy underpriced {side}',
                    'yes_price': market['yes_price'],
                    'no_price': market['no_price'],
                    'total_price': total_price,
                    'investment': investment,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'risk': 'Medium',
                    'liquidity': market['liquidity'],
                    'url': market['url'],
                    'action': f"Buy {side} @ ${market['yes_price'] if side == 'Yes' else market['no_price']:.3f}"
                })
    
    # 정렬: 무위험 먼저, 그 다음 수익률
    opportunities.sort(key=lambda x: (
        0 if x['risk'] == 'None' else 1,
        -x['profit_pct']
    ))
    
    return opportunities

# UI 시작
st.markdown('<h1 class="main-header">💰 Polymarket 차익거래 모니터링</h1>', unsafe_allow_html=True)
st.markdown("실시간으로 무위험 차익거래 기회를 찾습니다")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    min_profit = st.slider(
        "최소 수익률 (%)",
        min_value=0.5,
        max_value=10.0,
        value=2.0,
        step=0.5,
        help="이 수익률 이상의 기회만 표시"
    )
    
    max_investment = st.number_input(
        "최대 투자금 (USDC)",
        min_value=10,
        max_value=10000,
        value=100,
        step=10,
        help="한 거래당 최대 투자 금액"
    )
    
    api_source = st.selectbox(
        "API 소스",
        ["Gamma API (권장)", "CLOB API"],
        help="Gamma API가 더 안정적입니다"
    )
    
    auto_refresh = st.checkbox(
        "자동 새로고침 (30초)",
        value=False,
        help="체크하면 30초마다 자동으로 업데이트"
    )
    
    st.markdown("---")
    st.markdown("### 📊 통계")
    if st.session_state.last_update:
        st.info(f"마지막 업데이트: {st.session_state.last_update}")
    
    st.markdown("---")
    st.markdown("### ℹ️ 정보")
    st.markdown("""
    **차익거래 유형:**
    - 🟢 **Sure Win**: 무위험 보장 수익
    - 🟡 **Overpriced**: 시장 비효율성
    - 🟠 **Value Bet**: 고위험 고수익
    
    **주의사항:**
    - 가스비 고려 필요
    - 슬리피지 발생 가능
    - 유동성 제약 존재
    """)

# 메인 영역
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔍 지금 검색", use_container_width=True, type="primary"):
        with st.spinner("Polymarket에서 데이터 가져오는 중..."):
            # API 선택
            if "Gamma" in api_source:
                raw_markets = fetch_markets_gamma()
                markets = process_markets(raw_markets, 'gamma')
            else:
                raw_markets = fetch_markets_clob()
                markets = process_markets(raw_markets, 'clob')
            
            if markets:
                opportunities = find_arbitrage_opportunities(
                    markets, 
                    min_profit_pct=min_profit,
                    max_investment=max_investment
                )
                st.session_state.opportunities = opportunities
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                st.success(f"✅ {len(markets)}개 마켓 분석 완료!")
            else:
                st.error("❌ 마켓 데이터를 가져올 수 없습니다. API 연결을 확인하세요.")

with col2:
    total_opps = len(st.session_state.opportunities)
    st.metric("발견된 기회", f"{total_opps}개")

with col3:
    sure_wins = len([o for o in st.session_state.opportunities if o['risk'] == 'None'])
    st.metric("무위험 기회", f"{sure_wins}개", delta="🎯")

# 자동 새로고침
if auto_refresh:
    st.info("⏰ 30초마다 자동 업데이트 중...")
    time.sleep(30)
    st.rerun()

# 기회 표시
st.markdown("---")
st.header("🎯 발견된 차익거래 기회")

if not st.session_state.opportunities:
    st.info("👆 위의 '지금 검색' 버튼을 눌러 기회를 찾아보세요!")
else:
    for idx, opp in enumerate(st.session_state.opportunities):
        css_class = "sure-win" if opp['risk'] == 'None' else "value-bet"
        
        with st.container():
            st.markdown(f'<div class="opportunity-card {css_class}">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {opp['type']} - {opp['strategy']}")
                st.markdown(f"**{opp['question']}**")
                st.markdown(f"🎬 {opp['action']}")
                
                # 세부 정보
                detail_cols = st.columns(5)
                with detail_cols[0]:
                    st.metric("Yes 가격", f"${opp['yes_price']:.3f}")
                with detail_cols[1]:
                    st.metric("No 가격", f"${opp['no_price']:.3f}")
                with detail_cols[2]:
                    st.metric("합계", f"${opp['total_price']:.3f}")
                with detail_cols[3]:
                    st.metric("투자금", f"${opp['investment']:.0f}")
                with detail_cols[4]:
                    st.metric("유동성", f"${opp['liquidity']/1000:.0f}k")
            
            with col2:
                st.markdown(f"### +{opp['profit_pct']:.2f}%")
                st.markdown(f"**수익: ${opp['profit']:.2f}**")
                st.markdown(f"위험도: {opp['risk']}")
                st.link_button("Polymarket 이동", opp['url'], use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("")

# Export 기능
if st.session_state.opportunities:
    st.markdown("---")
    st.header("📥 데이터 내보내기")
    
    # DataFrame 생성
    df = pd.DataFrame(st.session_state.opportunities)
    df = df[['type', 'question', 'strategy', 'yes_price', 'no_price', 
             'total_price', 'investment', 'profit', 'profit_pct', 'risk', 'url']]
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📄 CSV 다운로드",
            data=csv,
            file_name=f"polymarket_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        json_data = json.dumps(st.session_state.opportunities, indent=2)
        st.download_button(
            label="📋 JSON 다운로드",
            data=json_data,
            file_name=f"polymarket_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # 테이블 표시
    with st.expander("📊 데이터 테이블 보기"):
        st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748b; padding: 2rem;'>
    <p><strong>⚠️ 면책조항</strong></p>
    <p>이 도구는 정보 제공 목적으로만 사용됩니다. 실제 거래는 본인 책임하에 진행하세요.</p>
    <p>가스비, 슬리피지, 시장 변동성을 고려해야 합니다.</p>
</div>
""", unsafe_allow_html=True)
