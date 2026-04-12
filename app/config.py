from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    envvar_prefix="MEALSPLIT",
    settings_files=["settings.toml", ".secrets.toml"],
    environments=True,
    env_switcher="MEALSPLIT_ENV",
    validators=[
        Validator("DATABASE_URL", must_exist=True),
        Validator("SUPABASE_URL", must_exist=True),
    ],
)
