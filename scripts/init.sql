CREATE SCHEMA IF NOT EXISTS trading;

-- =====================================================
-- TRADING SCHEMA TABLES
-- =====================================================

-- Signals
CREATE TABLE IF NOT EXISTS trading.signals
(
    strategy_id  TEXT        NOT NULL,
    indicator_id TEXT        NOT NULL,
    type         TEXT        NOT NULL,
    value        TEXT        NOT NULL,
    direction    TEXT        NOT NULL,
    regime       INTEGER     NOT NULL,
    market       TEXT        NOT NULL,
    timeframe    TEXT        NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL,
    metadata     JSONB       NOT NULL DEFAULT '{}',
    CONSTRAINT signals_pk PRIMARY KEY (strategy_id, indicator_id, type)
);

COMMENT ON TABLE trading.signals IS '전략 및 지표에 의해 생성된 트레이딩 신호';
COMMENT ON COLUMN trading.signals.strategy_id IS '신호를 생성한 전략의 식별자';
COMMENT ON COLUMN trading.signals.indicator_id IS '신호를 생성한 지표의 식별자';
COMMENT ON COLUMN trading.signals.type IS '신호 종류 (CROSS_OVER, THRESHOLD_CROSS, LEVEL_BREAK)';
COMMENT ON COLUMN trading.signals.value IS '신호의 구체적인 값 (GOLDEN_CROSS, DEAD_CROSS 등)';
COMMENT ON COLUMN trading.signals.direction IS '포지션 방향 (LONG, SHORT, CLOSE, HOLD)';
COMMENT ON COLUMN trading.signals.regime IS '신호 생성 시점의 시장 국면 (MarketRegime 정수값)';
COMMENT ON COLUMN trading.signals.market IS '대상 마켓 코드 (예: KRW-BTC)';
COMMENT ON COLUMN trading.signals.timeframe IS '신호가 생성된 타임프레임 (예: 1m, 5m, 1h)';
COMMENT ON COLUMN trading.signals.timestamp IS '신호 생성 시각';
COMMENT ON COLUMN trading.signals.metadata IS '추가적인 분석 데이터 또는 파라미터 정보';

-- Orders
CREATE TABLE IF NOT EXISTS trading.orders
(
    uuid             UUID        PRIMARY KEY,
    side             TEXT        NOT NULL,
    ord_type         TEXT        NOT NULL,
    price            NUMERIC,
    state            TEXT        NOT NULL,
    market           TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL,
    volume           NUMERIC,
    remaining_volume NUMERIC     NOT NULL,
    executed_volume  NUMERIC     NOT NULL,
    trades_count     INTEGER     NOT NULL,
    reserved_fee     NUMERIC     NOT NULL,
    remaining_fee    NUMERIC     NOT NULL,
    paid_fee         NUMERIC     NOT NULL,
    locked           NUMERIC     NOT NULL,
    identifier       TEXT,
    time_in_force    TEXT,
    smp_type         TEXT,
    prevented_volume NUMERIC,
    prevented_locked NUMERIC
);

COMMENT ON TABLE trading.orders IS '업비트 주문 내역';
COMMENT ON COLUMN trading.orders.uuid IS '주문의 고유 식별자';
COMMENT ON COLUMN trading.orders.side IS '주문 종류 (bid: 매수, ask: 매도)';
COMMENT ON COLUMN trading.orders.ord_type IS '주문 유형 (limit, price, market, best)';
COMMENT ON COLUMN trading.orders.price IS '주문 단가 또는 총액';
COMMENT ON COLUMN trading.orders.state IS '주문 상태 (wait, watch, done, cancel)';
COMMENT ON COLUMN trading.orders.market IS '마켓 ID (예: KRW-BTC)';
COMMENT ON COLUMN trading.orders.created_at IS '주문 생성 시각';
COMMENT ON COLUMN trading.orders.volume IS '주문 요청 수량';
COMMENT ON COLUMN trading.orders.remaining_volume IS '체결 후 남은 주문 수량';
COMMENT ON COLUMN trading.orders.executed_volume IS '체결된 수량';
COMMENT ON COLUMN trading.orders.trades_count IS '해당 주문에 대한 체결 건수';
COMMENT ON COLUMN trading.orders.reserved_fee IS '수수료로 예약된 비용';
COMMENT ON COLUMN trading.orders.remaining_fee IS '남은 수수료';
COMMENT ON COLUMN trading.orders.paid_fee IS '사용된 수수료';
COMMENT ON COLUMN trading.orders.locked IS '거래에 사용 중인 잠금 자산';
COMMENT ON COLUMN trading.orders.identifier IS '클라이언트 지정 주문 식별자';
COMMENT ON COLUMN trading.orders.time_in_force IS '주문 체결 옵션 (ioc, fok, post_only)';
COMMENT ON COLUMN trading.orders.smp_type IS '자전거래 방지 모드 (cancel_maker, cancel_taker, reduce)';
COMMENT ON COLUMN trading.orders.prevented_volume IS '자전거래 방지로 취소된 수량';
COMMENT ON COLUMN trading.orders.prevented_locked IS '자전거래 방지로 해제된 자산';

-- Trades
CREATE TABLE IF NOT EXISTS trading.trades
(
    trade_id    UUID        PRIMARY KEY,
    market      TEXT        NOT NULL,
    side        TEXT        NOT NULL,
    volume      NUMERIC     NOT NULL,
    price       NUMERIC     NOT NULL,
    strategy_id TEXT        NOT NULL,
    order_uuid  UUID        NOT NULL REFERENCES trading.orders (uuid),
    fee         NUMERIC     NOT NULL,
    fee_asset   TEXT        NOT NULL DEFAULT 'KRW',
    decision_id UUID,
    timestamp   TIMESTAMPTZ NOT NULL
);

COMMENT ON TABLE trading.trades IS '체결된 거래 기록';
COMMENT ON COLUMN trading.trades.trade_id IS '체결의 고유 식별자';
COMMENT ON COLUMN trading.trades.market IS '마켓 코드 (예: KRW-BTC)';
COMMENT ON COLUMN trading.trades.side IS '매수/매도 구분 (bid: 매수, ask: 매도)';
COMMENT ON COLUMN trading.trades.volume IS '체결 수량';
COMMENT ON COLUMN trading.trades.price IS '체결 단가';
COMMENT ON COLUMN trading.trades.strategy_id IS '이 체결을 발생시킨 전략의 식별자';
COMMENT ON COLUMN trading.trades.order_uuid IS '연관된 업비트 주문 UUID';
COMMENT ON COLUMN trading.trades.fee IS '체결 수수료';
COMMENT ON COLUMN trading.trades.fee_asset IS '수수료 자산 종류 (기본값: KRW)';
COMMENT ON COLUMN trading.trades.decision_id IS '이 체결을 발생시킨 Decision의 식별자';
COMMENT ON COLUMN trading.trades.timestamp IS '체결 시각';