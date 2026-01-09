"""
DEX 차익거래 대시보드 (Streamlit)
실시간으로 차익거래 기회를 모니터링하고 이메일 알림 전송
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from dex_arbitrage_detector import DexArbitrageDetector, EmailNotifier, ArbitrageOpportunity
from typing import List

# 페이지 설정
st.set_page_config(
    page_title="DEX 차익거래 감지기",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 추가
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .opportunity-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """세션 상태 초기화"""
    if 'opportunities_history' not in st.session_state:
        st.session_state.opportunities_history = []
    if 'last_scan_time' not in st.session_state:
        st.session_state.last_scan_time = None
    if 'total_opportunities_found' not in st.session_state:
        st.session_state.total_opportunities_found = 0
    if 'email_sent_count' not in st.session_state:
        st.session_state.email_sent_count = 0


def display_opportunity_cards(opportunities: List[ArbitrageOpportunity]):
    """차익거래 기회 카드 표시"""
    if not opportunities:
        st.info("🔍 현재 차익거래 기회가 발견되지 않았습니다.")
        return

    for i, opp in enumerate(opportunities):
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

            with col1:
                st.markdown(f"### {opp.token_pair}")
                st.caption(f"🕐 {opp.timestamp.strftime('%H:%M:%S')}")

            with col2:
                st.markdown("**매수**")
                st.markdown(f"🏪 {opp.buy_exchange.upper()}")
                st.markdown(f"💵 ${opp.buy_price:.4f}")

            with col3:
                st.markdown("**매도**")
                st.markdown(f"🏪 {opp.sell_exchange.upper()}")
                st.markdown(f"💵 ${opp.sell_price:.4f}")

            with col4:
                st.metric(
                    "수익률",
                    f"{opp.profit_percentage:.2f}%",
                    delta=f"${opp.profit_per_unit:.4f}"
                )

            st.divider()


def create_profit_chart(opportunities: List[ArbitrageOpportunity]):
    """수익률 차트 생성"""
    if not opportunities:
        return None

    df = pd.DataFrame([
        {
            'token_pair': opp.token_pair,
            'profit_percentage': opp.profit_percentage,
            'buy_exchange': opp.buy_exchange,
            'sell_exchange': opp.sell_exchange
        }
        for opp in opportunities
    ])

    fig = px.bar(
        df,
        x='token_pair',
        y='profit_percentage',
        title='토큰별 차익거래 수익률',
        labels={'token_pair': '토큰 쌍', 'profit_percentage': '수익률 (%)'},
        color='profit_percentage',
        color_continuous_scale='Viridis',
        hover_data=['buy_exchange', 'sell_exchange']
    )

    fig.update_layout(
        height=400,
        showlegend=False
    )

    return fig


def create_history_chart(history: List[ArbitrageOpportunity]):
    """시간별 기회 발견 히스토리 차트"""
    if not history:
        return None

    df = pd.DataFrame([
        {
            'timestamp': opp.timestamp,
            'token_pair': opp.token_pair,
            'profit_percentage': opp.profit_percentage
        }
        for opp in history
    ])

    fig = px.scatter(
        df,
        x='timestamp',
        y='profit_percentage',
        color='token_pair',
        title='시간별 차익거래 기회',
        labels={'timestamp': '시간', 'profit_percentage': '수익률 (%)'},
        hover_data=['token_pair']
    )

    fig.update_layout(height=400)

    return fig


def main():
    """메인 대시보드"""
    initialize_session_state()

    # 헤더
    st.markdown('<h1 class="main-header">💰 DEX 차익거래 감지기</h1>', unsafe_allow_html=True)

    # 사이드바 설정
    st.sidebar.header("⚙️ 설정")

    # 최소 수익률 설정
    min_profit = st.sidebar.slider(
        "최소 수익률 (%)",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1
    )

    # 스캔 간격 설정
    scan_interval = st.sidebar.slider(
        "스캔 간격 (초)",
        min_value=10,
        max_value=300,
        value=60,
        step=10
    )

    # 모니터링할 토큰 설정
    st.sidebar.subheader("📊 모니터링 토큰")
    default_tokens = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
    token_input = st.sidebar.text_area(
        "토큰 쌍 (줄바꿈으로 구분)",
        value='\n'.join(default_tokens),
        height=150
    )
    token_pairs = [t.strip() for t in token_input.split('\n') if t.strip()]

    # 이메일 알림 설정
    st.sidebar.subheader("📧 이메일 알림")
    email_enabled = st.sidebar.checkbox("이메일 알림 활성화")

    email_config = None
    if email_enabled:
        with st.sidebar.expander("이메일 설정", expanded=True):
            smtp_server = st.text_input("SMTP 서버", value="smtp.gmail.com")
            smtp_port = st.number_input("SMTP 포트", value=587)
            sender_email = st.text_input("발신 이메일")
            sender_password = st.text_input("발신 비밀번호", type="password")
            recipient_email = st.text_input("수신 이메일")

            if all([smtp_server, sender_email, sender_password, recipient_email]):
                email_config = {
                    'smtp_server': smtp_server,
                    'smtp_port': smtp_port,
                    'sender_email': sender_email,
                    'sender_password': sender_password,
                    'recipient_email': recipient_email
                }

    # 메인 영역
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("모니터링 토큰", len(token_pairs))

    with col2:
        st.metric("총 발견 기회", st.session_state.total_opportunities_found)

    with col3:
        st.metric("이메일 전송", st.session_state.email_sent_count)

    with col4:
        if st.session_state.last_scan_time:
            time_ago = (datetime.now() - st.session_state.last_scan_time).seconds
            st.metric("마지막 스캔", f"{time_ago}초 전")
        else:
            st.metric("마지막 스캔", "없음")

    # 스캔 버튼
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        scan_button = st.button("🔍 지금 스캔", type="primary", use_container_width=True)

    with col_btn2:
        auto_scan = st.checkbox("자동 스캔 활성화")

    # 스캔 실행
    if scan_button or auto_scan:
        with st.spinner('차익거래 기회를 스캔 중...'):
            # 감지기 초기화
            detector = DexArbitrageDetector(min_profit_percentage=min_profit)

            # 기회 찾기
            opportunities = detector.find_arbitrage_opportunities(token_pairs)

            # 세션 상태 업데이트
            st.session_state.last_scan_time = datetime.now()

            if opportunities:
                st.session_state.total_opportunities_found += len(opportunities)
                st.session_state.opportunities_history.extend(opportunities)

                # 최근 100개만 유지
                if len(st.session_state.opportunities_history) > 100:
                    st.session_state.opportunities_history = st.session_state.opportunities_history[-100:]

                st.success(f"✅ {len(opportunities)}개의 차익거래 기회 발견!")

                # 이메일 알림
                if email_enabled and email_config:
                    try:
                        notifier = EmailNotifier(**email_config)
                        notifier.send_alert(opportunities)
                        st.session_state.email_sent_count += 1
                        st.info("📧 이메일 알림이 전송되었습니다.")
                    except Exception as e:
                        st.error(f"❌ 이메일 전송 실패: {e}")
            else:
                st.info("현재 차익거래 기회가 없습니다.")

            # 결과 표시
            st.subheader("🎯 현재 차익거래 기회")
            display_opportunity_cards(opportunities)

            # 차트 표시
            if opportunities:
                st.subheader("📊 수익률 분석")
                profit_chart = create_profit_chart(opportunities)
                if profit_chart:
                    st.plotly_chart(profit_chart, use_container_width=True)

    # 히스토리 차트
    if st.session_state.opportunities_history:
        st.subheader("📈 기회 발견 히스토리")
        history_chart = create_history_chart(st.session_state.opportunities_history)
        if history_chart:
            st.plotly_chart(history_chart, use_container_width=True)

        # 히스토리 테이블
        with st.expander("📋 전체 히스토리 보기"):
            history_df = pd.DataFrame([
                {
                    '시간': opp.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    '토큰': opp.token_pair,
                    '매수처': opp.buy_exchange,
                    '매도처': opp.sell_exchange,
                    '수익률': f"{opp.profit_percentage:.2f}%",
                }
                for opp in reversed(st.session_state.opportunities_history)
            ])
            st.dataframe(history_df, use_container_width=True)

    # 자동 스캔
    if auto_scan:
        time.sleep(scan_interval)
        st.rerun()

    # 정보 섹션
    with st.expander("ℹ️ 사용 방법"):
        st.markdown("""
        ### DEX 차익거래 감지기 사용법

        1. **설정 조정**: 사이드바에서 최소 수익률과 스캔 간격을 조정합니다.
        2. **토큰 선택**: 모니터링할 토큰 쌍을 입력합니다.
        3. **이메일 설정**: 알림을 받고 싶다면 이메일 설정을 완료합니다.
        4. **스캔 시작**: "지금 스캔" 버튼을 클릭하거나 자동 스캔을 활성화합니다.

        ⚠️ **주의사항**:
        - 실제 거래 전 반드시 가격을 재확인하세요.
        - 거래소 간 송금 수수료와 시간을 고려하세요.
        - 네트워크 지연으로 인해 기회가 사라질 수 있습니다.
        - 이 도구는 정보 제공 목적이며, 투자 조언이 아닙니다.
        """)


if __name__ == "__main__":
    main()
