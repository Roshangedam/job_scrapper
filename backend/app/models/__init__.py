# Models package — import all models here for Alembic discovery
from app.models.engine_model import Engine, EnginePlatform, SearchPreference  # noqa
from app.models.job import Job, JobMatchReport  # noqa
from app.models.platform import Platform, PlatformConfig  # noqa
from app.models.candidate import CandidateProfile  # noqa
from app.models.scrape_run import ScrapeRun  # noqa
from app.models.settings_model import EmailConfig, AppSetting  # noqa
