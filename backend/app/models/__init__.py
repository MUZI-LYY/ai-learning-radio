"""SQLAlchemy ORM 模型集合。

导入顺序保证 Alembic autogenerate 与 `Base.metadata` 能发现所有表。
"""

from app.models.analytics_event import AnalyticsEvent
from app.models.daily_quota_usage import DailyQuotaUsage
from app.models.generation_task import GenerationTask
from app.models.knowledge_point import KnowledgePoint
from app.models.learning_source import LearningSource
from app.models.news_article import NewsArticle
from app.models.news_favorite import NewsFavorite
from app.models.news_program import NewsProgram
from app.models.news_source import NewsSource
from app.models.program import Program
from app.models.provider_usage import ProviderUsage
from app.models.recall_question import RecallQuestion
from app.models.task_step import TaskStep
from app.models.user import User

__all__ = [
    "AnalyticsEvent",
    "DailyQuotaUsage",
    "NewsArticle",
    "NewsFavorite",
    "NewsProgram",
    "NewsSource",
    "GenerationTask",
    "KnowledgePoint",
    "LearningSource",
    "Program",
    "ProviderUsage",
    "RecallQuestion",
    "TaskStep",
    "User",
]
