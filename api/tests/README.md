# Running Tests

## Prerequisites

1. Docker installed and running
2. Python 3.11+ with dependencies installed

## Setup

### Start the test database

```bash
cd /Users/tehmacodin/Repos/third-space
docker compose -f docker-compose.test.yml up -d
```

Verify the database is ready:

```bash
docker compose -f docker-compose.test.yml exec test-db pg_isready -U test
```

### Install dependencies

```bash
cd api
pip install -e ".[dev]"
```

Or install directly:

```bash
pip install fastapi uvicorn sqlalchemy asyncpg pytest pytest-asyncio pytest-cov httpx freezegun faker factory-boy
```

## Running Tests

### Run all tests

```bash
cd api
pytest tests/ -v
```

### Run specific test file

```bash
pytest tests/test_health.py -v
pytest tests/auth/test_register.py -v
```

### Run specific test class

```bash
pytest tests/auth/test_register.py::TestRegisterSuccess -v
```

### Run specific test

```bash
pytest tests/auth/test_register.py::TestRegisterSuccess::test_register_with_valid_data_returns_201 -v
```

### Run with coverage

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Skip slow tests

```bash
pytest tests/ -v -m "not slow"
```

## Teardown

Stop the test database:

```bash
docker compose -f docker-compose.test.yml down
```
