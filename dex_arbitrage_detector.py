"""
DEX 간 차익거래 기회 감지기
- 여러 DEX에서 동일 토큰 쌍의 가격을 비교
- 차익거래 기회 발견 시 이메일 알림
- Streamlit 대시보드로 실시간 모니터링
"""

import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import streamlit as st
import pandas as pd
import ccxt
import requests


@dataclass
class ArbitrageOpportunity:
    """차익거래 기회 데이터 클래스"""
    token_pair: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_percentage: float
    timestamp: datetime

    @property
    def profit_per_unit(self) -> float:
        return self.sell_price - self.buy_price


class DexArbitrageDetector:
    """DEX 차익거래 감지 클래스"""

    def __init__(self, min_profit_percentage: float = 1.0):
        """
        Args:
            min_profit_percentage: 최소 수익률 (%)
        """
        self.min_profit_percentage = min_profit_percentage
        self.exchanges = self._initialize_exchanges()

    def _initialize_exchanges(self) -> Dict[str, ccxt.Exchange]:
        """거래소 초기화"""
        exchanges = {}

        exchange_list = [
            'binance',
            'coinbasepro',
            'kraken',
            'kucoin',
            'bybit',
            'okx',
            'gateio',
            'huobi'
        ]

        for exchange_id in exchange_list:
            try:
                exchange_class = getattr(ccxt, exchange_id)
                exchange = exchange_class({
                    'enableRateLimit': True,
                    'timeout': 10000,
                })
                exchanges[exchange_id] = exchange
            except Exception as e:
                print(f"Failed to initialize {exchange_id}: {e}")

        return exchanges

    def get_price(self, exchange_name: str, symbol: str) -> Optional[float]:
        """특정 거래소에서 토큰 가격 가져오기"""
        try:
            if exchange_name not in self.exchanges:
                return None

            exchange = self.exchanges[exchange_name]
            ticker = exchange.fetch_ticker(symbol)

            # 평균 가격 사용 (bid + ask) / 2
            if ticker and 'bid' in ticker and 'ask' in ticker:
                if ticker['bid'] and ticker['ask']:
                    return (float(ticker['bid']) + float(ticker['ask'])) / 2

            # 평균 가격이 없으면 last 가격 사용
            if ticker and 'last' in ticker and ticker['last']:
                return float(ticker['last'])

        except Exception as e:
            print(f"Error fetching price from {exchange_name} for {symbol}: {e}")

        return None

    def find_arbitrage_opportunities(
        self,
        token_pairs: List[str]
    ) -> List[ArbitrageOpportunity]:
        """차익거래 기회 찾기"""
        opportunities = []

        for symbol in token_pairs:
            prices = {}

            # 모든 거래소에서 가격 가져오기
            for exchange_name in self.exchanges.keys():
                price = self.get_price(exchange_name, symbol)
                if price:
                    prices[exchange_name] = price

            # 최소 2개 이상의 거래소에서 가격을 가져온 경우
            if len(prices) >= 2:
                # 최저가와 최고가 찾기
                min_exchange = min(prices, key=prices.get)
                max_exchange = max(prices, key=prices.get)

                min_price = prices[min_exchange]
                max_price = prices[max_exchange]

                # 수익률 계산
                profit_percentage = ((max_price - min_price) / min_price) * 100

                # 최소 수익률 이상인 경우 기회로 기록
                if profit_percentage >= self.min_profit_percentage:
                    opportunity = ArbitrageOpportunity(
                        token_pair=symbol,
                        buy_exchange=min_exchange,
                        sell_exchange=max_exchange,
                        buy_price=min_price,
                        sell_price=max_price,
                        profit_percentage=profit_percentage,
                        timestamp=datetime.now()
                    )
                    opportunities.append(opportunity)

        # 수익률 높은 순으로 정렬
        opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
        return opportunities


class EmailNotifier:
    """이메일 알림 클래스"""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_email: str
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send_alert(self, opportunities: List[ArbitrageOpportunity]):
        """차익거래 기회 이메일 알림"""
        if not opportunities:
            return

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'🚨 DEX 차익거래 기회 {len(opportunities)}건 발견!'
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email

            # 이메일 본문 생성
            html_content = self._generate_email_html(opportunities)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # SMTP 서버 연결 및 전송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            print(f"Email sent successfully to {self.recipient_email}")

        except Exception as e:
            print(f"Failed to send email: {e}")

    def _generate_email_html(self, opportunities: List[ArbitrageOpportunity]) -> str:
        """이메일 HTML 생성"""
        html = """
        <html>
        <head>
            <style>
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }
                th {
                    background-color: #4CAF50;
                    color: white;
                }
                tr:nth-child(even) {
                    background-color: #f2f2f2;
                }
                .profit {
                    color: #4CAF50;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <h2>🚨 DEX 차익거래 기회 발견!</h2>
            <p>다음 차익거래 기회가 발견되었습니다:</p>
            <table>
                <tr>
                    <th>토큰 쌍</th>
                    <th>매수 거래소</th>
                    <th>매도 거래소</th>
                    <th>매수가</th>
                    <th>매도가</th>
                    <th>수익률</th>
                </tr>
        """

        for opp in opportunities:
            html += f"""
                <tr>
                    <td>{opp.token_pair}</td>
                    <td>{opp.buy_exchange.upper()}</td>
                    <td>{opp.sell_exchange.upper()}</td>
                    <td>${opp.buy_price:.4f}</td>
                    <td>${opp.sell_price:.4f}</td>
                    <td class="profit">{opp.profit_percentage:.2f}%</td>
                </tr>
            """

        html += """
            </table>
            <p><small>이 알림은 자동으로 생성되었습니다. 실제 거래 전 반드시 가격을 재확인하세요.</small></p>
        </body>
        </html>
        """

        return html


def main():
    """메인 함수 - CLI 테스트용"""
    detector = DexArbitrageDetector(min_profit_percentage=1.0)

    # 모니터링할 토큰 쌍 (시가총액 상위 100개 기준)
    token_pairs = [
        # Top 10
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'SOL/USDT',
        'ADA/USDT', 'DOGE/USDT', 'TRX/USDT', 'AVAX/USDT', 'DOT/USDT',

        # 11-20
        'MATIC/USDT', 'LINK/USDT', 'SHIB/USDT', 'UNI/USDT', 'ATOM/USDT',
        'LTC/USDT', 'ETC/USDT', 'XLM/USDT', 'BCH/USDT', 'FIL/USDT',

        # 21-30
        'APT/USDT', 'NEAR/USDT', 'ARB/USDT', 'VET/USDT', 'OP/USDT',
        'ALGO/USDT', 'ICP/USDT', 'HBAR/USDT', 'IMX/USDT', 'INJ/USDT',

        # 31-40
        'FTM/USDT', 'AAVE/USDT', 'GRT/USDT', 'SAND/USDT', 'MANA/USDT',
        'AXS/USDT', 'THETA/USDT', 'FLOW/USDT', 'XTZ/USDT', 'EOS/USDT',

        # 41-50
        'EGLD/USDT', 'APE/USDT', 'CHZ/USDT', 'RUNE/USDT', 'FXS/USDT',
        'ZIL/USDT', 'ENJ/USDT', 'BAT/USDT', 'GALA/USDT', 'KCS/USDT',

        # 51-60
        'CRV/USDT', 'SNX/USDT', 'LDO/USDT', 'QNT/USDT', 'KLAY/USDT',
        'ONE/USDT', 'ROSE/USDT', 'BLUR/USDT', 'CELO/USDT', 'ZEC/USDT',

        # 61-70
        'DASH/USDT', 'WAVES/USDT', 'NEO/USDT', 'IOTA/USDT', 'MKR/USDT',
        'XMR/USDT', 'KSM/USDT', 'HNT/USDT', 'GMT/USDT', 'ANKR/USDT',

        # 71-80
        'COMP/USDT', '1INCH/USDT', 'SUI/USDT', 'SEI/USDT', 'WOO/USDT',
        'DYDX/USDT', 'MASK/USDT', 'STORJ/USDT', 'OCEAN/USDT', 'COTI/USDT',

        # 81-90
        'KAVA/USDT', 'ZRX/USDT', 'YFI/USDT', 'BNT/USDT', 'REN/USDT',
        'SKL/USDT', 'ONT/USDT', 'ICX/USDT', 'QTUM/USDT', 'IOTX/USDT',

        # 91-100
        'BAL/USDT', 'OMG/USDT', 'SUSHI/USDT', 'C98/USDT', 'JASMY/USDT',
        'PERP/USDT', 'LQTY/USDT', 'RAY/USDT', 'CFX/USDT', 'GLMR/USDT',
    ]

    print("DEX 차익거래 기회 스캔 중...")
    opportunities = detector.find_arbitrage_opportunities(token_pairs)

    if opportunities:
        print(f"\n{len(opportunities)}개의 기회 발견!\n")
        for opp in opportunities:
            print(f"{'='*80}")
            print(f"토큰: {opp.token_pair}")
            print(f"매수: {opp.buy_exchange} @ ${opp.buy_price:.4f}")
            print(f"매도: {opp.sell_exchange} @ ${opp.sell_price:.4f}")
            print(f"수익률: {opp.profit_percentage:.2f}%")
            print(f"시간: {opp.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("차익거래 기회를 찾지 못했습니다.")


if __name__ == "__main__":
    main()
