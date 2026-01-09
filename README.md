# DEX 차익거래 감지기 (DEX Arbitrage Detector)

여러 거래소(DEX/CEX)에서 동일한 토큰 쌍의 가격을 비교하여 차익거래 기회를 실시간으로 감지하는 Streamlit 대시보드입니다.

## 주요 기능

- 🔍 **실시간 모니터링**: 여러 거래소의 가격을 실시간으로 비교
- 💰 **차익거래 기회 감지**: 설정한 최소 수익률 이상의 기회를 자동 감지
- 📧 **이메일 알림**: 차익거래 기회 발견 시 자동으로 이메일 알림
- 📊 **시각화 대시보드**: Streamlit 기반의 직관적인 대시보드
- 📈 **히스토리 추적**: 발견된 기회의 시간별 추이 분석

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd streamlit
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (선택사항)

이메일 알림을 사용하려면 `.env` 파일을 생성하세요:

```bash
cp .env.example .env
```

그리고 `.env` 파일을 편집하여 이메일 설정을 입력하세요:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
```

**Gmail 사용 시 주의사항**:
- Gmail의 경우 앱 비밀번호를 생성해야 합니다
- Google 계정 > 보안 > 2단계 인증 활성화 > 앱 비밀번호 생성

## 사용 방법

### Streamlit 대시보드 실행

```bash
streamlit run dex_arbitrage_dashboard.py
```

브라우저가 자동으로 열리고 대시보드가 표시됩니다 (기본: http://localhost:8501)

### CLI 모드 실행 (테스트용)

```bash
python dex_arbitrage_detector.py
```

## 대시보드 사용법

### 1. 설정 조정
- **최소 수익률**: 감지할 최소 수익률을 설정합니다 (기본: 1.0%)
- **스캔 간격**: 자동 스캔 시 간격을 설정합니다 (기본: 60초)

### 2. 모니터링 토큰 선택
사이드바에서 모니터링할 토큰 쌍을 입력합니다:
```
BTC/USDT
ETH/USDT
BNB/USDT
SOL/USDT
XRP/USDT
```

### 3. 이메일 알림 설정
- "이메일 알림 활성화" 체크박스 선택
- SMTP 서버 정보 입력
- 발신/수신 이메일 주소 입력

### 4. 스캔 시작
- **수동 스캔**: "지금 스캔" 버튼 클릭
- **자동 스캔**: "자동 스캔 활성화" 체크박스 선택

## 지원 거래소

다음 거래소에서 가격을 가져옵니다:
- Binance
- Coinbase Pro
- Kraken
- KuCoin
- Bybit
- OKX
- Gate.io
- Huobi

## 프로젝트 구조

```
.
├── dex_arbitrage_detector.py    # 핵심 감지 로직
├── dex_arbitrage_dashboard.py   # Streamlit 대시보드
├── app.py                        # Polymarket 스캐너 (기존)
├── canary_dashboard.py           # Canary 대시보드 (기존)
├── requirements.txt              # Python 의존성
├── .env.example                  # 환경 변수 예시
└── README.md                     # 프로젝트 문서
```

## 주요 클래스

### `DexArbitrageDetector`
거래소 간 가격 차이를 감지하는 메인 클래스

**메소드**:
- `get_price(exchange_name, symbol)`: 특정 거래소의 토큰 가격 조회
- `find_arbitrage_opportunities(token_pairs)`: 차익거래 기회 감지

### `EmailNotifier`
이메일 알림을 전송하는 클래스

**메소드**:
- `send_alert(opportunities)`: 차익거래 기회를 이메일로 전송

### `ArbitrageOpportunity`
차익거래 기회를 나타내는 데이터 클래스

**속성**:
- `token_pair`: 토큰 쌍 (예: BTC/USDT)
- `buy_exchange`: 매수할 거래소
- `sell_exchange`: 매도할 거래소
- `buy_price`: 매수 가격
- `sell_price`: 매도 가격
- `profit_percentage`: 수익률 (%)
- `timestamp`: 발견 시간

## 주의사항

⚠️ **중요한 고려사항**:

1. **거래 수수료**: 각 거래소의 거래 수수료를 고려해야 합니다
2. **송금 수수료**: 거래소 간 자금 이동 시 발생하는 수수료와 시간을 고려하세요
3. **슬리피지**: 실제 체결 가격은 표시된 가격과 다를 수 있습니다
4. **네트워크 지연**: API 응답 지연으로 인해 기회가 사라질 수 있습니다
5. **유동성**: 충분한 유동성이 있는지 확인하세요
6. **규제**: 각 거래소의 이용 약관과 현지 규제를 준수하세요

**이 도구는 정보 제공 목적이며, 투자 조언이 아닙니다. 실제 거래는 본인의 책임 하에 진행하세요.**

## 기술 스택

- **Python 3.9+**
- **Streamlit**: 웹 대시보드
- **CCXT**: 암호화폐 거래소 API 통합
- **Pandas**: 데이터 처리
- **Plotly**: 인터랙티브 차트
- **Web3.py**: 블록체인 연동 (향후 확장용)

## 향후 계획

- [ ] DEX 직접 연동 (Uniswap, PancakeSwap 등)
- [ ] 실시간 WebSocket 연결
- [ ] 자동 거래 실행 기능
- [ ] 더 많은 거래소 지원
- [ ] 슬리피지 계산 개선
- [ ] 거래 수수료 자동 계산
- [ ] 텔레그램 알림 추가
- [ ] 백테스팅 기능

## 라이선스

MIT License

## 기여하기

기여는 언제나 환영합니다! Pull Request를 보내주세요.

## 문의

문제가 발생하거나 제안사항이 있으시면 Issue를 생성해주세요.
