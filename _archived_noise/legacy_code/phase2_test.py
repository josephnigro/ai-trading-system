"""
Phase 2 validation test.
Validates digest generation and approval parsing logic without live market dependencies.
"""

from orchestrator import TradingOrchestrator
from src.core.signal import Signal, SignalType
from src.core.trade_proposal import TradeProposal, TradeProposalStatus


def make_proposal(signal_id: str, ticker: str, confidence: float) -> TradeProposal:
    signal = Signal(
        signal_id=signal_id,
        ticker=ticker,
        signal_type=SignalType.BUY,
        current_price=100.0,
        entry_price=100.0,
        profit_target=112.0,
        stop_loss=95.0,
        overall_confidence=confidence,
    )
    return TradeProposal(signal=signal, shares=10)


def main() -> int:
    orchestrator = TradingOrchestrator()

    p1 = make_proposal("sig1", "PLTR", 73.0)
    p2 = make_proposal("sig2", "GME", 81.0)
    p3 = make_proposal("sig3", "SOFI", 66.0)

    orchestrator.scoring_engine.proposals = [p1, p2, p3]

    digest = orchestrator.send_daily_proposal_digest([p1, p2, p3])
    assert "Found 3 trade setup(s) today" in digest
    assert "HOW TO APPROVE:" in digest

    selective = orchestrator.process_user_approval_response("1,SOFI")
    assert selective["approved_count"] == 2
    assert selective["rejected_count"] == 1

    statuses = {p.trade_id: p.status for p in orchestrator.scoring_engine.proposals}
    assert statuses[p1.trade_id] == TradeProposalStatus.APPROVED
    assert statuses[p2.trade_id] == TradeProposalStatus.REJECTED
    assert statuses[p3.trade_id] == TradeProposalStatus.APPROVED

    print("PHASE 2 TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
