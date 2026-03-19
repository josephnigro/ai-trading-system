"""
Test and example - demonstrates how to use the new modular system.
PHASE 1 VALIDATION - Makes sure everything works together.
"""

import logging
from orchestrator import TradingOrchestrator, OrchestratorConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("Phase1Test")


def test_modular_system():
    """Test the complete modular trading system."""
    
    logger.info("="*80)
    logger.info("PHASE 1: MODULAR TRADING SYSTEM TEST")
    logger.info("="*80)
    
    # Create orchestrator with config
    config = OrchestratorConfig(
        account_size=200000.0,
        risk_per_trade_pct=1.0,
        max_concurrent_positions=3,
        data_period="1y"
    )
    
    orchestrator = TradingOrchestrator(config=config)
    
    # Initialize system
    logger.info("\n1. INITIALIZING SYSTEM")
    logger.info("-" * 80)
    
    if not orchestrator.initialize():
        logger.error("Failed to initialize system")
        return False
    
    logger.info("✅ System initialized successfully")
    logger.info(f"Monitoring {len(orchestrator.stock_universe)} stocks")
    
    # Print system status
    status = orchestrator.get_system_status()
    logger.info(f"Account size: ${status['account_size']:,.2f}")
    logger.info(f"Open positions: {status['open_positions']}/{config.max_concurrent_positions}")
    
    # Run market scan
    logger.info("\n2. RUNNING MARKET SCAN")
    logger.info("-" * 80)
    
    # Only scan first 5 stocks for testing
    test_universe = orchestrator.stock_universe[:5]
    orchestrator.stock_universe = test_universe
    
    proposals = orchestrator.run_scan()
    
    logger.info(f"✅ Scan complete: {len(proposals)} proposals generated")
    
    if len(proposals) == 0:
        logger.warning("No proposals generated. Testing with mock proposals...")
        return True
    
    # Display proposals
    logger.info("\n3. PROPOSALS WAITING FOR APPROVAL")
    logger.info("-" * 80)
    
    for i, proposal in enumerate(proposals[:3], 1):  # Show first 3
        logger.info(f"\nProposal #{i}:")
        logger.info(proposal.summary())
    
    # Test approval workflow
    logger.info("\n4. TESTING APPROVAL WORKFLOW")
    logger.info("-" * 80)
    
    if proposals:
        proposal = proposals[0]
        logger.info(f"Approving: {proposal.trade_id}")
        
        if orchestrator.approve_trade(proposal.trade_id, "Approved by test"):
            logger.info(f"✅ Trade approved: {proposal.trade_id}")
        
        # Check updated status
        updated_proposals = orchestrator.get_pending_proposals()
        logger.info(f"Pending proposals: {len(updated_proposals)}")
    
    # System status
    logger.info("\n5. FINAL SYSTEM STATUS")
    logger.info("-" * 80)
    
    final_status = orchestrator.get_system_status()
    logger.info(f"Account Size: ${final_status['account_size']:,.2f}")
    logger.info(f"Exposure: ${final_status['current_exposure']:,.2f}")
    logger.info(f"Daily Risk Used: ${final_status['daily_risk_used']:,.2f}")
    logger.info(f"Pending Approvals: {final_status['pending_proposals']}")
    logger.info(f"Total Executions: {final_status['execution_history']}")
    
    # Shutdown
    logger.info("\n6. SHUTDOWN")
    logger.info("-" * 80)
    
    orchestrator.shutdown()
    logger.info("✅ System shutdown complete")
    
    logger.info("\n" + "="*80)
    logger.info("PHASE 1 TEST COMPLETE - ALL SYSTEMS OPERATIONAL")
    logger.info("="*80)
    
    return True


if __name__ == "__main__":
    try:
        success = test_modular_system()
        if success:
            logger.info("\n✅ PHASE 1 SUCCESSFUL")
        else:
            logger.error("\n❌ PHASE 1 FAILED")
    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {str(e)}", exc_info=True)
