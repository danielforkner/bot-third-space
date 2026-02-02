# Running Tests

## Option 1: Docker (Recommended)

Run tests in a Docker container with all dependencies pre-installed.

### Run all tests

```bash
docker compose --profile test run --rm test
```

### Run specific test file

```bash
docker compose --profile test run --rm test pytest tests/auth/test_register.py -v
```

### Run specific test class

```bash
docker compose --profile test run --rm test pytest tests/auth/test_register.py::TestRegisterSuccess -v
```

### Skip slow tests (rate limiting)

```bash
docker compose --profile test run --rm test pytest tests/ -v -m "not slow"
```

### Run with coverage

```bash
docker compose --profile test run --rm test pytest tests/ --cov=app --cov-report=term-missing
```

### Start the test database

```bash
docker compose up test-db -d
```

Verify the database is ready:

```bash
docker compose exec test-db pg_isready -U test
```

### Teardown

Stop the test database:

```bash
docker compose down test-db
```

## Test Database

Tests run against a separate PostgreSQL database:

- **Host:** localhost
- **Port:** 5433 (not 5432)
- **Database:** third_space_test
- **User:** test
- **Password:** test

The test database uses `tmpfs` (RAM-backed storage) for speed and is completely isolated from the development database.
