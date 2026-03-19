# Testing Context

> See also: [Root CLAUDE.md](../CLAUDE.md) for overall architecture

## Test Framework

- **Framework**: pytest
- **Async Support**: pytest-asyncio
- **Mocking**: unittest.mock (AsyncMock, MagicMock)

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_credit_service.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=web --cov-report=html
```

## Test Organization

```
tests/
├── test_credit_service.py      # Unit tests for credit management
├── test_webhooks_integration.py # Integration tests for Stripe webhooks
├── test_subscription_service.py # Unit tests for subscriptions (TODO)
└── ... (add more as needed)
```

## Testing Patterns

### Async Tests

Use `@pytest.mark.asyncio` decorator:

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_operation():
    service = MyService()
    result = await service.async_method()
    assert result == expected
```

### Mocking Database

Mock the database manager:

```python
@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    mock = MagicMock()
    mock.execute_query = AsyncMock()
    mock.transaction = MagicMock()
    return mock
```

**Mock query results:**
```python
# Return rows
mock_db_manager.execute_query = AsyncMock(
    return_value=[
        {'id': '123', 'name': 'Test'},
        {'id': '456', 'name': 'Test 2'}
    ]
)

# Return empty
mock_db_manager.execute_query = AsyncMock(return_value=[])
```

**Mock transactions:**
```python
async def mock_transaction():
    class MockConn:
        async def execute(self, query, *args):
            pass

        async def fetchrow(self, query, *args):
            return {'id': '123', 'value': 42}

        async def fetchval(self, query, *args):
            return 1

    return MockConn()

mock_db_manager.transaction = MagicMock()
mock_db_manager.transaction.__aenter__ = AsyncMock(
    return_value=await mock_transaction()
)
mock_db_manager.transaction.__aexit__ = AsyncMock(return_value=None)
```

### Mocking Services

Create fixtures for services with mocked dependencies:

```python
@pytest.fixture
def credit_service():
    """Create credit service with mocked dependencies."""
    with patch('web.services.credit_service.get_db_manager') as mock_get_db:
        service = CreditService()
        service.db_manager = AsyncMock()
        return service
```

### Testing Credit Service

**Test balance retrieval:**
```python
@pytest.mark.asyncio
async def test_get_balance_existing_user(credit_service):
    # Mock database response
    mock_row = {
        'monthly_credits': 40,
        'rollover_credits': 10,
        'top_up_credits': Decimal('25.50'),
        'bonus_credits': 5,
        'total': Decimal('80.50'),
    }
    credit_service.db_manager.execute_query = AsyncMock(
        return_value=[mock_row]
    )

    balance = await credit_service.get_credit_balance('user123')

    assert balance['monthly'] == 40
    assert balance['total'] == 80.50
```

**Test credit checks:**
```python
@pytest.mark.asyncio
async def test_insufficient_credits(credit_service):
    # Mock subscription (free tier)
    credit_service.db_manager.execute_query = AsyncMock(
        return_value=[{
            'tier_id': 'free',
            'allows_sonnet': False,
        }]
    )

    # Mock balance (0 credits)
    credit_service.get_credit_balance = AsyncMock(
        return_value={'total': 0}
    )

    allowed, reason, required = await credit_service.check_can_perform_operation(
        'user123', 'paper_analysis'
    )

    assert allowed is False
    assert reason == 'insufficient_credits'
```

### Testing Webhooks

**Test signature verification:**
```python
def create_webhook_signature(payload: str, secret: str) -> str:
    """Create valid Stripe webhook signature."""
    timestamp = str(int(datetime.now().timestamp()))
    signed_content = f'{timestamp}.{payload}'
    signature = hmac.new(
        secret.encode(),
        signed_content.encode(),
        hashlib.sha256
    ).hexdigest()
    return f't={timestamp},v1={signature}'

@pytest.mark.asyncio
async def test_valid_signature_accepted():
    payload = json.dumps({'id': 'evt_123', 'type': 'checkout.session.completed'})
    signature = create_webhook_signature(payload, 'whsec_test_secret')

    assert signature.startswith('t=')
    assert 'v1=' in signature
```

**Test idempotency:**
```python
@pytest.mark.asyncio
async def test_duplicate_webhook_rejected(subscription_service):
    stripe_event_id = 'evt_duplicate_123'

    # Mock: webhook already processed
    subscription_service.db_manager.execute_query = AsyncMock(
        return_value=[{'stripe_event_id': stripe_event_id, 'status': 'processed'}]
    )

    result = await subscription_service.db_manager.execute_query(
        'SELECT * FROM stripe_webhook_events WHERE stripe_event_id = $1',
        (stripe_event_id,)
    )

    assert len(result) > 0
    assert result[0]['stripe_event_id'] == stripe_event_id
```

## Test Coverage Goals

### Critical Paths (Must Test)
- ✅ Credit balance calculations
- ✅ Credit deduction logic (priority order)
- ✅ Permission checks (tier restrictions)
- ✅ Webhook idempotency
- ✅ Webhook event routing

### Important (Should Test)
- Subscription creation/cancellation
- Monthly credit refresh with rollover
- Admin exemptions from credit checks
- API error responses (402, 403)

### Nice to Have
- End-to-end API tests
- Integration tests with real database
- Load testing for webhook processing

## Mocking Best Practices

1. **Use AsyncMock for async methods:**
   ```python
   service.async_method = AsyncMock(return_value=result)
   ```

2. **Use MagicMock for sync methods:**
   ```python
   service.sync_method = MagicMock(return_value=result)
   ```

3. **Mock at the boundary:**
   - Mock database, not business logic
   - Mock external APIs (Stripe, Anthropic)
   - Don't mock the code you're testing

4. **Use fixtures for reusable mocks:**
   ```python
   @pytest.fixture
   def mock_stripe_client():
       with patch('web.core.stripe_client.stripe') as mock:
           yield mock
   ```

## Common Patterns

### Testing Error Conditions

```python
@pytest.mark.asyncio
async def test_handles_database_error(service):
    service.db_manager.execute_query = AsyncMock(
        side_effect=Exception("Database connection failed")
    )

    with pytest.raises(Exception) as exc_info:
        await service.operation()

    assert "Database connection failed" in str(exc_info.value)
```

### Testing with Decimal Values

```python
from decimal import Decimal

# Always use Decimal for credit amounts
credit_service.db_manager.execute_query = AsyncMock(
    return_value=[{
        'top_up_credits': Decimal('25.50'),  # Not float!
    }]
)
```

### Verifying Method Calls

```python
@pytest.mark.asyncio
async def test_calls_deduct_credits(credit_service):
    credit_service.deduct_credits = AsyncMock()

    await perform_operation(credit_service)

    credit_service.deduct_credits.assert_called_once_with(
        user_id='user123',
        amount=1.0,
        operation_type='paper_analysis'
    )
```

## CI/CD Integration

Tests run automatically on:
- Pull request creation
- Push to main branch
- Manual trigger

Configure in `.github/workflows/test.yml` (TODO):
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest tests/ -v
```

## TODO: Test Coverage Expansion

- [ ] Test subscription service methods
- [ ] Test Stripe webhook handlers end-to-end
- [ ] Test credit top-up purchases
- [ ] Test monthly credit refresh
- [ ] Integration tests with test database
- [ ] API endpoint tests (FastAPI TestClient)
