from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    envvar_prefix="CARTWISE",
    settings_files=["settings.toml", ".secrets.toml"],
    environments=True,
    env_switcher="CARTWISE_ENV",
    validators=[
        Validator("DATABASE_URL", must_exist=True),
        Validator("SUPABASE_URL", must_exist=True),
    ],
)


def get_async_database_url(*, disable_prepared_statements: bool = False) -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if disable_prepared_statements:
        sep = "&" if "?" in url else "?"
        url += f"{sep}prepared_statement_cache_size=0"
    return url
