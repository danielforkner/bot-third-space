"""Bootstrap a local .env file with secure defaults."""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path


def _generate_secret(bytes_len: int = 32) -> str:
    return secrets.token_urlsafe(bytes_len)


def _generate_password(bytes_len: int = 24) -> str:
    return secrets.token_urlsafe(bytes_len)


def _is_placeholder(value: str) -> bool:
    return "CHANGE_ME" in value or value.strip() == ""


def _parse_kv_line(line: str) -> tuple[str, str] | None:
    if "=" not in line or line.lstrip().startswith("#"):
        return None
    key, _, value = line.partition("=")
    return key.strip(), value.strip()


def build_values(
    template_lines: list[str],
    *,
    db_host: str,
    db_port: str,
    force_rotate: bool,
    dev_cors: bool,
) -> dict[str, str]:
    existing: dict[str, str] = {}
    for line in template_lines:
        parsed = _parse_kv_line(line)
        if parsed:
            key, value = parsed
            existing[key] = value

    postgres_user = existing.get("POSTGRES_USER", "postgres")
    postgres_db = existing.get("POSTGRES_DB", "third_space")
    postgres_password = existing.get("POSTGRES_PASSWORD", "")

    if force_rotate or _is_placeholder(postgres_password):
        postgres_password = _generate_password()

    secrets_values = {
        "SECRET_KEY": _generate_secret(),
        "API_KEY_SECRET": _generate_secret(),
        "JWT_SECRET": _generate_secret(),
    }

    values = {
        "POSTGRES_USER": postgres_user,
        "POSTGRES_PASSWORD": postgres_password,
        "POSTGRES_DB": postgres_db,
    }

    database_url = (
        f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{db_host}:{db_port}/{postgres_db}"
    )
    if "DATABASE_URL" in existing:
        values["DATABASE_URL"] = database_url

    for key, value in secrets_values.items():
        if key not in existing:
            continue
        current = existing.get(key, "")
        if force_rotate or _is_placeholder(current):
            values[key] = value
        else:
            values[key] = current

    if dev_cors and "CORS_ORIGINS" in existing:
        values["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"

    return values


def write_env(template_lines: list[str], values: dict[str, str]) -> str:
    rendered: list[str] = []
    for line in template_lines:
        parsed = _parse_kv_line(line)
        if not parsed:
            rendered.append(line)
            continue
        key, _value = parsed
        if key in values:
            rendered.append(f"{key}={values[key]}\n")
        else:
            rendered.append(line)
    return "".join(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a .env file from .env.example")
    parser.add_argument(
        "--path",
        default=None,
        help="Output path for .env (default: repo root/.env)",
    )
    parser.add_argument(
        "--db-host",
        default="db",
        help="Database host for DATABASE_URL (default: db)",
    )
    parser.add_argument(
        "--db-port",
        default="5432",
        help="Database port for DATABASE_URL (default: 5432)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use localhost for DATABASE_URL host",
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Regenerate secrets even if placeholders are already replaced",
    )
    parser.add_argument(
        "--dev-cors",
        action="store_true",
        help="Set CORS_ORIGINS to local dev defaults",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .env if present",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / ".env.example"
    if not template_path.exists():
        print(f"Template not found: {template_path}", file=sys.stderr)
        return 1

    env_path = Path(args.path) if args.path else repo_root / ".env"
    if env_path.exists() and not args.force:
        print(
            f"{env_path} already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    db_host = "localhost" if args.local else args.db_host
    template_lines = template_path.read_text(encoding="utf-8").splitlines(keepends=True)
    values = build_values(
        template_lines,
        db_host=db_host,
        db_port=args.db_port,
        force_rotate=args.rotate,
        dev_cors=args.dev_cors,
    )
    env_path.write_text(write_env(template_lines, values), encoding="utf-8")

    if os.name != "nt":
        try:
            env_path.chmod(0o600)
        except OSError:
            pass

    print(f"Wrote {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
