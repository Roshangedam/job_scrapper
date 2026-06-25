"""Base adapter interface — all platform scrapers must implement this.

To add a new platform:
1. Create a new file in adapters/ (e.g., linkedin_adapter.py)
2. Create a class that extends BaseJobAdapter
3. Implement all abstract methods
4. The adapter_registry auto-discovers it on startup — zero core code changes!
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawJobListing:
    """Raw scraped job data before AI normalization."""
    source_platform: str
    source_url: str = ""
    source_job_id: str = ""
    title: str = ""
    company_name: str = ""
    company_logo_url: str = ""
    location: str = ""
    description_raw: str = ""
    description_html: str = ""
    salary_text: str = ""
    experience_text: str = ""
    posted_date: str = ""
    date_posted_iso: str = ""
    valid_through: str = ""
    applicants_count: Optional[int] = None
    employment_type: str = ""
    skills_text: str = ""
    skills_list: list = field(default_factory=list)
    skills_preferred: list = field(default_factory=list)
    apply_url: str = ""
    hr_name: str = ""
    hr_email: str = ""
    company_rating: Optional[float] = None
    role: str = ""
    industry_type: str = ""
    department: str = ""
    role_category: str = ""
    education_ug: str = ""
    education_pg: str = ""
    extra_data: dict = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def to_raw_text(self) -> str:
        """Convert to text format for AI normalization."""
        parts = [
            f"Title: {self.title}",
            f"Company: {self.company_name}",
            f"Rating: {self.company_rating}" if self.company_rating else "",
            f"Location: {self.location}",
            f"Experience: {self.experience_text}",
            f"Salary: {self.salary_text}",
            f"Employment Type: {self.employment_type}",
            f"Role: {self.role}" if self.role else "",
            f"Industry: {self.industry_type}" if self.industry_type else "",
            f"Department: {self.department}" if self.department else "",
            f"Role Category: {self.role_category}" if self.role_category else "",
            f"Education UG: {self.education_ug}" if self.education_ug else "",
            f"Education PG: {self.education_pg}" if self.education_pg else "",
            f"Preferred Skills: {', '.join(self.skills_preferred)}" if self.skills_preferred else "",
            f"All Skills: {self.skills_text}",
            f"Posted: {self.posted_date}",
            f"Date Posted: {self.date_posted_iso}" if self.date_posted_iso else "",
            f"Valid Through: {self.valid_through}" if self.valid_through else "",
            f"Applicants: {self.applicants_count or 'N/A'}",
            f"HR: {self.hr_name} ({self.hr_email})" if self.hr_name else "",
            f"Apply URL: {self.apply_url}" if self.apply_url else "",
            f"Source URL: {self.source_url}",
            f"\nDescription:\n{self.description_raw}",
        ]
        return "\n".join(p for p in parts if p)


class BaseJobAdapter(ABC):
    """Abstract interface for platform-specific job scrapers.

    Every adapter MUST implement:
    - platform_name: unique identifier (e.g., "naukri")
    - platform_display_name: human-readable name (e.g., "Naukri.com")
    - platform_logo: path to logo file
    - initialize(): setup browser/auth
    - scrape_jobs(): perform the actual scraping
    - cleanup(): release resources
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Unique platform identifier."""
        pass

    @property
    @abstractmethod
    def platform_display_name(self) -> str:
        """Human-readable platform name."""
        pass

    @property
    @abstractmethod
    def platform_logo(self) -> str:
        """Logo filename or URL."""
        pass

    @abstractmethod
    async def initialize(self, config: dict = None) -> None:
        """Setup browser context, authentication, cookies."""
        pass

    @abstractmethod
    async def scrape_jobs(self, search_params: dict) -> List[RawJobListing]:
        """Scrape jobs based on search parameters.

        Args:
            search_params: {
                "keywords": ["python developer", "backend"],
                "companies": ["Google", "Microsoft"],
                "locations": ["Bangalore", "Pune"],
                "experience_min": 2,
                "experience_max": 5
            }

        Returns:
            List of RawJobListing objects
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup browser resources."""
        pass
