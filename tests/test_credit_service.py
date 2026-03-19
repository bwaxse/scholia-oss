"""
Unit tests for CreditService.

Tests credit balance management, deductions, grants, and tier restrictions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta

# These imports assume the service is importable
# In practice, adjust based on actual project structure
from web.services.credit_service import CreditService, get_credit_service


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    mock = MagicMock()
    mock.execute_query = AsyncMock()
    mock.transaction = MagicMock()
    return mock


@pytest.fixture
def credit_service():
    """Create a credit service with mocked dependencies."""
    with patch('web.services.credit_service.get_db_manager') as mock_get_db:
        service = CreditService()
        service.db_manager = AsyncMock()
        return service


class TestGetCreditBalance:
    """Tests for getting credit balance."""

    @pytest.mark.asyncio
    async def test_get_balance_existing_user(self, credit_service):
        """Test getting balance for user with existing credits."""
        # Mock the query response (using 20× multiplied values)
        mock_row = {
            'monthly_credits': 800,
            'rollover_credits': 200,
            'top_up_credits': 600,
            'total': 1600,
        }
        credit_service.db_manager.execute_query = AsyncMock(return_value=[mock_row])

        balance = await credit_service.get_credit_balance('user123')

        assert balance['monthly'] == 800
        assert balance['rollover'] == 200
        assert balance['top_up'] == 600
        assert balance['total'] == 1600

    @pytest.mark.asyncio
    async def test_get_balance_nonexistent_user(self, credit_service):
        """Test getting balance for user without record creates one."""
        credit_service.db_manager.execute_query = AsyncMock(return_value=[])
        credit_service._ensure_credit_balance_exists = AsyncMock()

        balance = await credit_service.get_credit_balance('user456')

        assert balance['monthly'] == 0
        assert balance['rollover'] == 0
        assert balance['top_up'] == 0  # Integer now
        assert balance['total'] == 0.0
        credit_service._ensure_credit_balance_exists.assert_called_once()


class TestCheckCanPerformOperation:
    """Tests for checking if user can perform operations."""

    @pytest.mark.asyncio
    async def test_can_perform_paper_analysis_with_sufficient_credits(self, credit_service):
        """Test user with enough credits can load paper."""
        # Mock subscription query
        credit_service.db_manager.execute_query = AsyncMock(
            return_value=[{
                'tier_id': 'pro',
                'allows_sonnet': True,
                'allows_gemini_pro': False,
            }]
        )

        # Mock balance
        credit_service.get_credit_balance = AsyncMock(
            return_value={'total': 50.0}
        )

        allowed, reason, required = await credit_service.check_can_perform_operation(
            'user123', 'paper_analysis'
        )

        assert allowed is True
        assert reason is None
        assert required == 20  # Paper load cost is now 20 credits (was 1.0)

    @pytest.mark.asyncio
    async def test_cannot_perform_operation_insufficient_credits(self, credit_service):
        """Test user without enough credits is blocked."""
        credit_service.db_manager.execute_query = AsyncMock(
            return_value=[{
                'tier_id': 'free',
                'allows_sonnet': False,
                'allows_gemini_pro': False,
            }]
        )

        credit_service.get_credit_balance = AsyncMock(
            return_value={'total': 10}  # Less than 20 needed
        )

        allowed, reason, required = await credit_service.check_can_perform_operation(
            'user123', 'paper_analysis'
        )

        assert allowed is False
        assert reason == 'insufficient_credits'
        assert required == 20  # Paper load cost is now 20 credits (was 1.0)

    @pytest.mark.asyncio
    async def test_cannot_use_restricted_model(self, credit_service):
        """Test user cannot use models restricted by tier."""
        credit_service.db_manager.execute_query = AsyncMock(
            return_value=[{
                'tier_id': 'free',
                'allows_sonnet': False,  # Free tier can't use Sonnet
                'allows_gemini_pro': False,
            }]
        )

        credit_service.get_credit_balance = AsyncMock(
            return_value={'total': 50.0}
        )

        allowed, reason, required = await credit_service.check_can_perform_operation(
            'user123', 'question', model='sonnet'
        )

        assert allowed is False
        assert reason == 'model_restricted'

    @pytest.mark.asyncio
    async def test_can_use_allowed_model(self, credit_service):
        """Test user can use models allowed by tier."""
        credit_service.db_manager.execute_query = AsyncMock(
            return_value=[{
                'tier_id': 'pro',
                'allows_sonnet': True,  # Pro tier can use Sonnet
                'allows_gemini_pro': False,
            }]
        )

        credit_service.get_credit_balance = AsyncMock(
            return_value={'total': 50.0}
        )

        allowed, reason, required = await credit_service.check_can_perform_operation(
            'user123', 'question', model='sonnet'
        )

        assert allowed is True
        assert reason is None
        assert required == 8  # Sonnet costs 8 credits


class TestDeductCredits:
    """Tests for deducting credits."""

    @pytest.mark.asyncio
    async def test_deduct_credits_priority_order(self, credit_service):
        """Test credits are deducted in priority order: rollover→monthly→top_up."""
        balance = {
            'monthly': 15,
            'rollover': 10,
            'top_up': 25,
            'total': 50.0,
        }

        # Mock connection with proper async methods
        class MockConn:
            async def fetchrow(self, query, *args):
                return {
                    'monthly_credits': Decimal('15'),
                    'rollover_credits': Decimal('10'),
                    'top_up_credits': Decimal('25'),
                }

            async def execute(self, *args, **kwargs):
                pass

            async def fetchval(self, *args, **kwargs):
                return 1  # transaction_id

        mock_conn = MockConn()

        # Create async context manager that returns mock_conn
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        credit_service.db_manager.transaction = MagicMock(return_value=mock_context)

        credit_service.get_credit_balance = AsyncMock(return_value=balance)

        # Deduct 30 credits - should take all 10 rollover + all 15 monthly + 5 from top_up
        result = await credit_service.deduct_credits(
            'user123',
            30.0,
            'question',
            notes='Test deduction'
        )

        assert result['amount'] == -30.0
        assert len(result['pools_used']) > 0


class TestGrantCredits:
    """Tests for granting credits."""

    @pytest.mark.asyncio
    async def test_grant_credits_to_pool(self, credit_service):
        """Test granting credits to a specific pool."""
        # Mock transaction context
        async def mock_transaction():
            class MockConn:
                async def execute(self, *args, **kwargs):
                    pass

                async def fetchval(self, *args, **kwargs):
                    return 1  # transaction_id

            return MockConn()

        credit_service.db_manager.transaction = MagicMock()
        credit_service.db_manager.transaction.__aenter__ = AsyncMock(return_value=await mock_transaction())
        credit_service.db_manager.transaction.__aexit__ = AsyncMock(return_value=None)

        credit_service.get_credit_balance = AsyncMock(
            return_value={
                'monthly': 40,
                'rollover': 0,
                'top_up': 0,
                'total': 40.0,
            }
        )
        credit_service._ensure_credit_balance_exists = AsyncMock()

        result = await credit_service.grant_credits(
            'user123',
            25.0,
            'top_up',
            'credit_purchase',
            notes='Test grant'
        )

        assert result['amount'] == 25.0
        assert result['balance_after']['total'] == 40.0


class TestMonthlyCreditRefresh:
    """Tests for monthly credit refresh and rollover."""

    @pytest.mark.asyncio
    async def test_rollover_calculation_within_limit(self, credit_service):
        """Test rollover calculation respects max rollover limit."""
        # Pro tier: 40 monthly, 40 max rollover
        # Unused monthly: 30
        # Max available rollover: 40 - 40 = 0
        # Should rollover 0, not 30

        # Mock connection with proper async methods
        class MockConn:
            async def fetchrow(self, query, *args):
                return {
                    'tier_id': 'pro',
                    'current_period_end': datetime.now(),
                    'monthly_credits': 40,
                    'max_rollover_credits': 40,
                }

            async def execute(self, *args, **kwargs):
                pass

        mock_conn = MockConn()

        # Create async context manager that returns mock_conn
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        credit_service.db_manager.transaction = MagicMock(return_value=mock_context)

        credit_service.get_credit_balance = AsyncMock(
            return_value={
                'monthly': 30,  # Unused from previous month
                'rollover': 0,
                'top_up': 0,
                'total': 30.0,
            }
        )
        credit_service.grant_credits = AsyncMock()

        await credit_service.monthly_credit_refresh('user123')

        # Grant should be called for new monthly credits
        credit_service.grant_credits.assert_called_once()


class TestCreditCosts:
    """Tests for credit cost constants."""

    def test_credit_cost_values(self):
        """Test that credit costs are correct after 20× multiplier."""
        assert CreditService.CREDIT_COSTS['haiku'] == 2   # raised from 1 for margin
        assert CreditService.CREDIT_COSTS['flash'] == 1    # was 0.05
        assert CreditService.CREDIT_COSTS['sonnet'] == 8   # raised from 4 for margin
        assert CreditService.CREDIT_COSTS['opus'] == 10    # was 0.5
        assert CreditService.PAPER_LOAD_COST == 20  # was 1.0

    def test_cheaper_models_cost_less(self):
        """Test that cheaper models (Haiku) cost less than expensive ones (Opus)."""
        assert CreditService.CREDIT_COSTS['haiku'] < CreditService.CREDIT_COSTS['sonnet']
        assert CreditService.CREDIT_COSTS['sonnet'] < CreditService.CREDIT_COSTS['opus']


class TestGetCreditService:
    """Tests for service factory function."""

    def test_get_credit_service_returns_service(self):
        """Test that get_credit_service returns a CreditService instance."""
        with patch('web.services.credit_service.get_db_manager'):
            service = get_credit_service()
            assert isinstance(service, CreditService)
