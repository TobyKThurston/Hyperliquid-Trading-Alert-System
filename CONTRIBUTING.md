# Contributing

Thanks for your interest in contributing to Hyperliquid Trading Alert System!

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Hyperliquid-Trading-Alert-System.git
   cd Hyperliquid-Trading-Alert-System
   ```
3. Create a branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
5. Start services:
   ```bash
   docker-compose up -d
   ```
6. Make your changes
7. Run tests:
   ```bash
   pytest
   ```
8. Run linting:
   ```bash
   ruff check .
   ruff format .
   ```
9. Commit your changes:
   ```bash
   git commit -m "Add feature: description"
   ```
10. Push to your fork:
    ```bash
    git push origin feature/your-feature-name
    ```
11. Open a Pull Request

## Code Style

- Follow PEP 8
- Use `ruff` for linting and formatting (configured in `pyproject.toml`)
- Maximum line length: 100 characters
- Write type hints for function parameters and return values
- Use async/await for I/O operations

## Testing

- Write tests for new features
- Aim for high test coverage
- Use `pytest` and `pytest-asyncio` for async tests
- Run tests before committing: `pytest --cov=. --cov-report=term-missing`

## Pull Request Process

1. Ensure all tests pass
2. Run `ruff check .` and `ruff format .` to ensure code style
3. Update documentation if needed
4. Update CHANGELOG.md if adding new features
5. Request review from maintainers

## Commit Messages

Use clear, descriptive commit messages:
- `Add feature: description`
- `Fix bug: description`
- `Update docs: description`
- `Refactor: description`

## Questions?

Open an issue if you have questions or need clarification!

