"""Main orchestration for the trading workflow."""

from collections import Counter
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import os

from src.core.trade_proposal import TradeProposal, TradeProposalStatus
from src.core.execution_record import ExecutionRecord
from src.data_module import DataModule, PolygonFallbackDataProvider
from src.signal_engine import SignalEngine
from src.scoring_engine import ScoringEngine
from src.risk_management import RiskManager, RiskConfig
from src.execution_module import ExecutionModule
from src.logging_module import LoggingModule
from src.notification_module.notification_engine import NotificationModule
from src.position_monitor.position_store import PositionStore
from src.position_monitor.position_monitor import PositionMonitor


# CONFIGURATION


def build_alpaca_broker():
    """
    Create an AlpacaBroker from environment variables.
    Returns None if credentials are not configured.
    """
    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")
    if not api_key or not api_secret:
        return None
    try:
        from src.broker.alpaca_broker import AlpacaBroker
        return AlpacaBroker(api_key=api_key, api_secret=api_secret)
    except Exception as exc:
        logging.getLogger("orchestrator").warning(f"Could not create AlpacaBroker: {exc}")
        return None


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    account_size: float = 300.0
    risk_per_trade_pct: float = 1.0
    max_concurrent_positions: int = 3
    data_period: str = "1y"
    scan_interval_seconds: int = 3600  # 1 hour


class TradingOrchestrator:
    """
    Central hub for scan, proposal, approval, and execution workflows.
    """
    
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        broker = None,
        notification_module: Optional[NotificationModule] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            config: Configuration
            broker: Broker integration (for execution)
        """
        self.config = config or OrchestratorConfig()
        self.broker = broker
        
        # Setup logging
        self.logger = logging.getLogger("TradingOrchestrator")
        
        # Initialize modules
        self.data_module = DataModule(PolygonFallbackDataProvider())
        self.signal_engine = SignalEngine()
        self.risk_manager = RiskManager(
            RiskConfig(
                account_size=self.config.account_size,
                risk_per_trade_pct=self.config.risk_per_trade_pct,
                max_concurrent_positions=self.config.max_concurrent_positions
            )
        )
        self.scoring_engine = ScoringEngine(self.risk_manager)
        self.execution_module = ExecutionModule(broker) if broker else None
        self.logging_module = LoggingModule()
        self.notification_module = notification_module or NotificationModule()

        # Position monitoring
        self.position_store = PositionStore()
        self.position_monitor = PositionMonitor(
            broker=self.broker,
            store=self.position_store,
        )
        
        # State
        self.is_initialized = False
        self.stock_universe: List[str] = []
        self.pending_proposals: List[TradeProposal] = []
        self.execution_history: List[ExecutionRecord] = []
        self.last_scan_results: List[Dict[str, Any]] = []
    
    def initialize(self, stock_universe: Optional[List[str]] = None) -> bool:
        """
        Initialize the trading system.
        
        Args:
            stock_universe: List of tickers to monitor
        
        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing trading system...")
            
            # Initialize modules
            modules = [
                self.data_module,
                self.signal_engine,
                self.risk_manager,
                self.scoring_engine,
                self.notification_module,
                self.logging_module
            ]
            
            if self.execution_module:
                modules.append(self.execution_module)
            
            for module in modules:
                if not module.initialize():
                    self.logger.error(f"Failed to initialize {module.name}")
                    return False
            
            # Set stock universe
            self.stock_universe = stock_universe or self._get_default_universe()
            
            self.is_initialized = True
            self.logger.info(f"System initialized. Monitoring {len(self.stock_universe)} stocks.")
            return True
        
        except Exception as exc:
            self.logger.error(f"Initialization failed: {str(exc)}")
            return False

    # DATA
    def run_scan(self) -> List[TradeProposal]:
        """
        Run a complete market scan and generate proposals.
        
        Returns:
            List of trade proposals
        """
        if not self.is_initialized:
            raise RuntimeError("System not initialized")
        
        self.logger.info(f"Starting market scan of {len(self.stock_universe)} stocks...")
        
        proposals: List[TradeProposal] = []
        signals_generated = 0
        proposals_created = 0
        errors = 0
        scan_results: List[Dict[str, Any]] = []
        rejection_counts: Counter[str] = Counter()
        
        for ticker in self.stock_universe:
            ticker_result = {
                'ticker': ticker,
                'passed': False,
                'rejection_reason': '',
            }

            try:
                # Fetch data
                data = self.data_module.get_ohlcv(ticker, period=self.config.data_period)
                if data is None:
                    errors += 1
                    ticker_result['rejection_reason'] = 'no_data'
                    rejection_counts[ticker_result['rejection_reason']] += 1
                    scan_results.append(ticker_result)
                    continue
                
                # Get current price
                quote = self.data_module.get_quote(ticker)
                if quote is None:
                    errors += 1
                    ticker_result['rejection_reason'] = 'no_quote'
                    rejection_counts[ticker_result['rejection_reason']] += 1
                    scan_results.append(ticker_result)
                    continue
                
                current_price = quote.get('price', data['Close'].iloc[-1])
                
                # Generate signal
                signal = self.signal_engine.generate_signal(ticker, data, current_price)
                if signal is None:
                    reason = self.signal_engine.last_rejection_reason or 'signal_filter_failed'
                    ticker_result['rejection_reason'] = reason
                    rejection_counts[reason] += 1
                    scan_results.append(ticker_result)
                    continue
                
                signals_generated += 1
                self.logging_module.log_signal(signal.to_dict())

                # Pre-proposal quality filter
                market_cap = quote.get('market_cap', 0) or 0
                avg_volume_raw = data['Volume'].tail(50).mean() if len(data) >= 50 else data['Volume'].mean()
                if hasattr(avg_volume_raw, 'iloc'):
                    avg_volume_raw = avg_volume_raw.iloc[0]
                avg_volume = float(avg_volume_raw)

                current_volume_raw = data['Volume'].iloc[-1]
                if hasattr(current_volume_raw, 'iloc'):
                    current_volume_raw = current_volume_raw.iloc[0]
                current_volume = float(current_volume_raw)
                volume_spike = (current_volume / avg_volume) if avg_volume > 0 else 0.0

                quality_score = 0

                # Price
                if current_price > 3:
                    quality_score += 1

                # Volume
                if avg_volume > 500_000:
                    quality_score += 1

                # Market Cap
                if market_cap > 1_000_000_000:
                    quality_score += 1

                # Volume Spike
                if volume_spike > 1.0:
                    quality_score += 1

                if quality_score < 3:
                    self.logger.info(f"{ticker}: filtered out (quality_score={quality_score})")
                    if avg_volume <= 500_000:
                        reason = 'low_volume'
                    elif current_price <= 3:
                        reason = 'low_price'
                    elif market_cap <= 1_000_000_000:
                        reason = 'low_market_cap'
                    elif volume_spike <= 1.0:
                        reason = 'not_near_breakout'
                    else:
                        reason = 'quality_filter_failed'
                    ticker_result['rejection_reason'] = reason
                    rejection_counts[reason] += 1
                    scan_results.append(ticker_result)
                    continue
                
                # Create proposal
                proposal = self.scoring_engine.create_proposal(signal)
                if proposal is None:
                    reason = self.scoring_engine.last_rejection_reason or 'risk_filter_failed'
                    ticker_result['rejection_reason'] = reason
                    rejection_counts[reason] += 1
                    scan_results.append(ticker_result)
                    continue
                
                proposals_created += 1
                proposals.append(proposal)
                self.logging_module.log_proposal(proposal.to_dict())
                ticker_result['passed'] = True
                scan_results.append(ticker_result)
                
            except Exception as exc:
                self.logger.error(f"Error scanning {ticker}: {str(exc)}")
                errors += 1
                ticker_result['rejection_reason'] = 'scan_exception'
                rejection_counts[ticker_result['rejection_reason']] += 1
                scan_results.append(ticker_result)
                continue
        
        self.pending_proposals = proposals
        self.last_scan_results = scan_results

        total_tickers = len(scan_results)
        passed_tickers = sum(1 for r in scan_results if r.get('passed'))
        rejected_tickers = total_tickers - passed_tickers

        summary_lines = [
            "SCAN SUMMARY:",
            f"Total tickers: {total_tickers}",
            f"Passed: {passed_tickers}",
            f"Rejected: {rejected_tickers}",
            "Breakdown:",
        ]
        for reason, count in sorted(rejection_counts.items()):
            summary_lines.append(f"- {reason}: {count}")
        if not rejection_counts:
            summary_lines.append("- none: 0")
        self.logger.info("\n".join(summary_lines))
        
        self.logger.info(
            f"Scan complete: {signals_generated} signals, "
            f"{proposals_created} proposals, {errors} errors"
        )
        
        return proposals

    # OUTPUT
    def send_daily_proposal_digest(
        self,
        proposals: Optional[List[TradeProposal]] = None,
        send_email: bool = False,
        send_sms: bool = False,
    ) -> str:
        """
        Build and publish a daily proposal message for user review.

        Args:
            proposals: Optional proposal list. Defaults to current pending proposals.

        Returns:
            Rendered digest message.
        """
        proposal_batch = proposals if proposals is not None else self.get_pending_proposals()
        message = self.notification_module.publish_trade_digest(
            proposal_batch,
            send_email=send_email,
            send_sms=send_sms,
        )
        self.logging_module.session_log.append({
            'type': 'NOTIFICATION',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'message': message,
                'proposal_count': len(proposal_batch),
                'send_email': send_email,
                'send_sms': send_sms,
            }
        })
        return message

    def process_user_approval_response(self, response: str) -> Dict[str, Any]:
        """
        Process user response to proposal digest.

        Supports:
        - yes/no to approve or reject all
        - comma-separated selections by index, ticker, or trade_id
        """
        pending = self.get_pending_proposals()
        decision = self.notification_module.parse_user_response(response, pending)

        approved_count = 0
        rejected_count = 0

        for trade_id in decision['approved_ids']:
            if self.approve_trade(trade_id, "Approved from digest response"):
                approved_count += 1

        for trade_id in decision['rejected_ids']:
            if self.reject_trade(trade_id, "Rejected from digest response"):
                rejected_count += 1

        summary = {
            'mode': decision['mode'],
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'invalid_tokens': decision['invalid_tokens'],
            'pending_after': len(self.get_pending_proposals())
        }
        self.logger.info(f"Processed approval response: {summary}")
        return summary

    # EXECUTION
    def run_daily_phase2_cycle(
        self,
        user_response: Optional[str] = None,
        response_file: Optional[str] = None,
        response_inbox_dir: Optional[str] = None,
        send_email: bool = False,
        send_sms: bool = False,
        execute_approved: bool = False
    ) -> Dict[str, Any]:
        """
        Run full Phase 2 workflow.

        Flow:
        1. Scan market and generate proposals
        2. Send daily digest to user
        3. Apply user approval response
        4. Optionally execute approved trades if broker is configured
        """
        proposals = self.run_scan()
        digest = self.send_daily_proposal_digest(
            proposals,
            send_email=send_email,
            send_sms=send_sms,
        )

        approval_result: Dict[str, Any] = {
            'mode': 'no_response',
            'approved_count': 0,
            'rejected_count': 0,
            'invalid_tokens': [],
            'pending_after': len(self.get_pending_proposals())
        }

        resolved_response = self.notification_module.get_ingested_response(
            direct_response=user_response,
            response_file=response_file,
            response_inbox_dir=response_inbox_dir,
        )

        if resolved_response is not None and proposals:
            approval_result = self.process_user_approval_response(resolved_response)

        # Optional paper-mode automation: approve all and execute immediately.
        auto_approve_paper = os.getenv("AUTO_APPROVE_PAPER", "0").strip().lower() in {"1", "true", "yes", "y", "on"}
        broker_is_paper = bool(getattr(self.broker, "_paper", False)) if self.broker is not None else False
        if auto_approve_paper and broker_is_paper and proposals:
            auto_approved = 0
            for proposal in proposals:
                if self.approve_trade(proposal.trade_id, "AUTO_APPROVE_PAPER"):
                    auto_approved += 1
            approval_result = {
                'mode': 'auto_approve_paper',
                'approved_count': auto_approved,
                'rejected_count': 0,
                'invalid_tokens': [],
                'pending_after': len(self.get_pending_proposals())
            }
            self.logger.info(f"AUTO_APPROVE_PAPER enabled: auto-approved {auto_approved} proposal(s)")

        executions: List[ExecutionRecord] = []
        if execute_approved or (auto_approve_paper and broker_is_paper):
            executions = self.execute_approved_trades()
            if executions:
                exec_dicts = [e.to_dict() for e in executions if hasattr(e, "to_dict")]
                self.notification_module.send_execution_confirmation(
                    exec_dicts,
                    send_email=send_email,
                    send_sms=send_sms,
                )

        result = {
            'proposals_generated': len(proposals),
            'digest_preview': digest[:200],
            'approval_result': approval_result,
            'response_received': resolved_response is not None,
            'executions': len(executions),
        }
        self.logger.info(f"Phase 2 daily cycle result: {result}")
        return result
    
    # SCORING
    def get_pending_proposals(self) -> List[TradeProposal]:
        """Get all pending proposals waiting for approval."""
        return self.scoring_engine.get_pending_proposals()
    
    def approve_trade(self, trade_id: str, notes: str = "") -> bool:
        """Approve a trade proposal."""
        if not self.scoring_engine.approve_proposal(trade_id, notes):
            return False
        
        self.logging_module.log_approval(trade_id, True, notes)
        self.logger.info(f"Trade {trade_id} approved")
        return True
    
    def reject_trade(self, trade_id: str, reason: str = "") -> bool:
        """Reject a trade proposal."""
        if not self.scoring_engine.reject_proposal(trade_id, reason):
            return False
        
        self.logging_module.log_approval(trade_id, False, reason)
        self.logger.info(f"Trade {trade_id} rejected")
        return True
    
    # RISK
    def execute_approved_trades(self) -> List[ExecutionRecord]:
        """
        Execute all approved trades.
        
        Returns:
            List of execution records
        """
        if not self.execution_module:
            self.logger.warning("No broker configured, skipping execution")
            return []
        
        executions = []
        
        for proposal in self.scoring_engine.proposals:
            if proposal.status != TradeProposalStatus.APPROVED:
                continue
            if proposal.signal is None:
                self.logger.warning(f"Skipping {proposal.trade_id}: missing signal")
                continue
            
            # Execute
            execution = self.execution_module.execute_buy_order(
                trade_id=proposal.trade_id,
                ticker=proposal.signal.ticker,
                shares=proposal.shares
            )
            
            if execution:
                proposal.mark_executed(
                    order_id=execution.order_id,
                    execution_price=execution.execution_price,
                    actual_shares=execution.shares
                )

                # Persist to position store for ongoing monitoring
                if proposal.signal:
                    self.position_store.add_position(
                        ticker=proposal.signal.ticker,
                        shares=execution.shares,
                        entry_price=execution.execution_price,
                        stop_loss=proposal.signal.stop_loss,
                        profit_target=proposal.signal.profit_target,
                        trade_id=proposal.trade_id,
                        order_id=execution.order_id,
                    )

                executions.append(execution)
                self.execution_history.append(execution)
                self.logging_module.log_execution(execution.to_dict())

                self.logger.info(f"Executed {proposal.trade_id}")

        return executions

    # OUTPUT
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            'initialized': self.is_initialized,
            'timestamp': datetime.utcnow().isoformat(),
            'stock_universe_size': len(self.stock_universe),
            'pending_proposals': len(self.get_pending_proposals()),
            'open_positions': self.risk_manager.open_positions,
            'account_size': self.risk_manager.config.account_size,
            'current_exposure': self.risk_manager.current_exposure,
            'daily_risk_used': self.risk_manager.daily_risk_used,
            'execution_history': len(self.execution_history)
        }
    
    # EXECUTION
    def shutdown(self) -> None:
        """Shutdown all modules."""
        self.logger.info("Shutting down trading system...")
        
        # Save logs
        log_file = self.logging_module.save_session_log()
        self.logger.info(f"Logs saved to {log_file}")
        
        # Shutdown modules
        modules = [
            self.logging_module,
            self.notification_module,
            self.execution_module,
            self.scoring_engine,
            self.risk_manager,
            self.signal_engine,
            self.data_module
        ]
        
        for module in modules:
            if module:
                module.shutdown()
        
        self.is_initialized = False
        self.logger.info("System shutdown complete")
    
    # DATA
    def _get_default_universe(self) -> List[str]:
        """Get default list of stocks to monitor."""
        return [
            'GME', 'AMC', 'BBBY', 'SOFI', 'PLTR', 'LCID', 'NIO', 'CLOV',
            'CLNE', 'OCGN', 'SPCE', 'NVAX', 'RIOT', 'TLRY', 'SNDL', 'PROG',
            'ATER', 'GNUS', 'CIDM', 'BLNK', 'FUBO', 'PRPL', 'RIG', 'UXIN',
            'KODK', 'BNGO', 'IDEX', 'VROOM'
        ]
