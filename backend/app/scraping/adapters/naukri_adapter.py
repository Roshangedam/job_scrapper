"""Naukri.com Job Scraper Adapter.

Scrapes job listings from Naukri.com using Playwright.
Handles dynamic content, pagination, and extracts structured job data.

Two-step flow:
  1. Listing page → Collect job detail URLs from rendered cards
  2. Detail pages → Navigate to each URL asynchronously, extract full data
     from JSON-LD structured data + HTML selectors
"""

import json
import logging
import asyncio
import re
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.config import settings
from app.scraping.base_adapter import BaseJobAdapter, RawJobListing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONCURRENT_DETAIL_PAGES = 5          # Max browser tabs for detail scraping
DETAIL_PAGE_TIMEOUT     = 25000      # ms – timeout per detail page navigation
LISTING_PAGE_TIMEOUT    = 30000      # ms – timeout for search results page
POLITE_DELAY_BETWEEN    = 1.5        # seconds between batches
SCROLL_PAUSE            = 1.0        # seconds between scrolls
MAX_SCROLLS             = 5          # number of times to scroll listing page


class NaukriAdapter(BaseJobAdapter):
    """Naukri.com scraper using Playwright browser automation."""

    BASE_URL = "https://www.naukri.com"

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._playwright = None

    # ------------------------------------------------------------------
    # BaseJobAdapter interface
    # ------------------------------------------------------------------
    @property
    def platform_name(self) -> str:
        return "naukri"

    @property
    def platform_display_name(self) -> str:
        return "Naukri.com"

    @property
    def platform_logo(self) -> str:
        return "/platform-logos/naukri.svg"

    async def initialize(self, config: dict = None) -> None:
        """Launch a Chromium browser with stealth anti-detection settings."""
        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            channel="chrome",  # Crucial for bypassing Naukri bot detection
            headless=settings.PLAYWRIGHT_HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
            ],
        )

        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )

        # Inject cookies if provided (e.g. for authenticated sessions)
        if config and config.get("cookies"):
            await self._context.add_cookies(config["cookies"])

        logger.info("🌐 Naukri browser context initialized")

    async def scrape_jobs(self, search_params: dict) -> List[RawJobListing]:
        """Entry point — build search combos, scrape listings, scrape details."""
        all_jobs: List[RawJobListing] = []

        keywords      = search_params.get("keywords", [])
        locations     = search_params.get("locations", [])
        companies     = search_params.get("companies", [])
        experience_min = search_params.get("experience_min")
        experience_max = search_params.get("experience_max")
        max_jobs       = search_params.get("max_jobs", settings.MAX_JOBS_PER_SCRAPE)

        # Build every keyword × location combination
        search_queries: List[dict] = []

        if keywords:
            for kw in keywords:
                if locations:
                    for loc in locations:
                        search_queries.append({"keyword": kw, "location": loc})
                else:
                    search_queries.append({"keyword": kw, "location": ""})

        if companies:
            for company in companies:
                for kw in (keywords or [""]):
                    search_queries.append(
                        {"keyword": f"{kw} {company}".strip(), "location": ""}
                    )

        if not search_queries:
            logger.warning("No search queries — provide keywords, locations, or companies")
            return []

        for query in search_queries:
            if len(all_jobs) >= max_jobs:
                break

            try:
                jobs = await self._scrape_search_page(
                    keyword=query["keyword"],
                    location=query["location"],
                    experience_min=experience_min,
                    experience_max=experience_max,
                    max_results=max_jobs - len(all_jobs),
                )
                all_jobs.extend(jobs)
                logger.info(
                    f"📋 Got {len(jobs)} fully-scraped jobs for "
                    f"'{query['keyword']}' in '{query['location']}'"
                )
                # Be polite between search queries
                await asyncio.sleep(POLITE_DELAY_BETWEEN)

            except Exception as e:
                logger.error(f"❌ Error scraping '{query['keyword']}': {e}")
                continue

        logger.info(f"✅ Total jobs scraped from Naukri: {len(all_jobs)}")
        return all_jobs

    async def cleanup(self) -> None:
        """Release browser resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("🧹 Naukri browser cleaned up")

    # ======================================================================
    # STEP 1 — Listing / Search-Results Page
    # ======================================================================
    async def _scrape_search_page(
        self,
        keyword: str,
        location: str = "",
        experience_min: Optional[float] = None,
        experience_max: Optional[float] = None,
        max_results: int = 50,
    ) -> List[RawJobListing]:
        """Navigate to search results, collect job URLs, scrape each detail page."""
        page = await self._context.new_page()
        try:
            url = self._build_search_url(keyword, location, experience_min, experience_max)
            logger.info(f"🔍 Navigating to listing page: {url}")

            await page.goto(url, wait_until="networkidle", timeout=LISTING_PAGE_TIMEOUT)
            await asyncio.sleep(5)  # Let Next.js hydrate & render cards

            # Dismiss cookie / login popups
            await self._close_popups(page)

            # Scroll to trigger lazy-loaded cards
            await self._scroll_page(page, scrolls=MAX_SCROLLS)

            # Collect job detail URLs from the rendered cards
            job_urls = await self._extract_job_urls_from_page(page, max_results)
            logger.info(f"🔗 Collected {len(job_urls)} job detail URLs from listing page")

            if not job_urls:
                logger.warning("⚠️  No job URLs found — page may not have rendered")
                return []

            # STEP 2 — scrape each detail page concurrently
            jobs = await self._scrape_details_concurrently(job_urls)
            return jobs

        except Exception as e:
            logger.error(f"Error on listing page: {e}")
            return []
        finally:
            await page.close()

    def _build_search_url(
        self,
        keyword: str,
        location: str = "",
        experience_min: Optional[float] = None,
        experience_max: Optional[float] = None,
    ) -> str:
        """Build Naukri search URL.  e.g. /java-developer-jobs-in-pune?experience=1"""
        slug = keyword.lower().replace(" ", "-")
        url = f"{self.BASE_URL}/{slug}-jobs"

        if location:
            url += f"-in-{location.lower().replace(' ', '-')}"

        params = []
        if experience_min is not None:
            params.append(f"experience={int(experience_min)}")
        if experience_max is not None:
            params.append(f"experienceTo={int(experience_max)}")

        if params:
            url += "?" + "&".join(params)

        return url

    # ------------------------------------------------------------------
    # Listing-page helpers
    # ------------------------------------------------------------------
    async def _extract_job_urls_from_page(
        self, page: Page, max_results: int
    ) -> List[str]:
        """Pull unique job detail URLs from the rendered listing page.

        We try multiple strategies because Naukri's DOM changes across
        versions (legacy vs Next.js SSR).
        """
        urls: List[str] = []
        seen: set = set()

        # Strategy 1 — <a> tags whose href matches /job-listings-*
        links = await page.evaluate("""
            () => {
                const anchors = document.querySelectorAll('a[href*="job-listings"]');
                return Array.from(anchors).map(a => a.href);
            }
        """)
        for href in (links or []):
            if href and href not in seen:
                seen.add(href)
                urls.append(href)

        logger.info(f"  Strategy 1 (a[href*=job-listings]): {len(urls)} URLs")

        # Strategy 2 — elements with data-job-id → build URL from title link
        if not urls:
            links2 = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll('[data-job-id]');
                    const result = [];
                    cards.forEach(c => {
                        const a = c.querySelector('a[href]');
                        if (a && a.href) result.push(a.href);
                    });
                    return result;
                }
            """)
            for href in (links2 or []):
                if href and href not in seen:
                    seen.add(href)
                    urls.append(href)
            logger.info(f"  Strategy 2 (data-job-id): {len(urls)} URLs")

        # Strategy 3 — any <a> with href containing /job-listings-
        if not urls:
            links3 = await page.evaluate("""
                () => {
                    const all = document.querySelectorAll('a');
                    const result = [];
                    all.forEach(a => {
                        if (a.href && a.href.includes('/job-listings-')) {
                            result.push(a.href);
                        }
                    });
                    return result;
                }
            """)
            for href in (links3 or []):
                if href and href not in seen:
                    seen.add(href)
                    urls.append(href)
            logger.info(f"  Strategy 3 (broad /job-listings-): {len(urls)} URLs")

        # Strategy 4 — Modern Naukri: look for job card wrappers and extract
        # any link that points to a Naukri job page (various URL patterns)
        if not urls:
            links4 = await page.evaluate("""
                () => {
                    const result = [];
                    // Try all links on page matching Naukri job detail patterns
                    const allAnchors = document.querySelectorAll('a');
                    allAnchors.forEach(a => {
                        const h = a.href || '';
                        if (
                            h.includes('naukri.com/job/') ||
                            h.includes('naukri.com/job-listings') ||
                            h.match(/naukri\\.com\\/[\\w-]+-jobs-/) ||
                            h.match(/naukri\\.com\\/[\\w-]+-\\d{6,}/)
                        ) {
                            result.push(h);
                        }
                    });
                    return result;
                }
            """)
            for href in (links4 or []):
                if href and href not in seen:
                    seen.add(href)
                    urls.append(href)
            logger.info(f"  Strategy 4 (broad job URL patterns): {len(urls)} URLs")

        # Strategy 5 — Dump debug info if still nothing found
        if not urls:
            debug = await page.evaluate("""
                () => {
                    const body = document.body;
                    const allLinks = document.querySelectorAll('a[href]');
                    const sampleLinks = Array.from(allLinks).slice(0, 20).map(a => a.href);
                    const title = document.title;
                    const bodyLength = (body && body.innerText) ? body.innerText.length : 0;
                    return {
                        title: title,
                        bodyTextLength: bodyLength,
                        totalLinks: allLinks.length,
                        sampleLinks: sampleLinks
                    };
                }
            """)
            logger.warning(
                f"⚠️  0 job URLs found. Debug dump:\n"
                f"  Page title: {debug.get('title','?')}\n"
                f"  Body text length: {debug.get('bodyTextLength',0)}\n"
                f"  Total links on page: {debug.get('totalLinks',0)}\n"
                f"  Sample links: {debug.get('sampleLinks',[])[:]}"
            )

        # De-duplicate fully-qualified URLs
        unique: List[str] = []
        final_seen: set = set()
        for u in urls:
            canonical = u.split("?")[0]       # drop query params for dedup
            if canonical not in final_seen:
                final_seen.add(canonical)
                unique.append(u)

        return unique[:max_results]

    async def _close_popups(self, page: Page):
        """Try to dismiss overlay modals / popups."""
        selectors = [
            "button.styles_closeIcon__3UUxk",
            "[class*='close']",
            "button[aria-label='Close']",
            ".crossIcon",
        ]
        for sel in selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.4)
            except Exception:
                pass

    async def _scroll_page(self, page: Page, scrolls: int = 3):
        """Scroll down to trigger lazy-loaded job cards."""
        for _ in range(scrolls):
            await page.evaluate("window.scrollBy(0, 1200)")
            await asyncio.sleep(SCROLL_PAUSE)

    # ======================================================================
    # STEP 2 — Detail Pages (async / concurrent)
    # ======================================================================
    async def _scrape_details_concurrently(
        self, urls: List[str]
    ) -> List[RawJobListing]:
        """Scrape multiple detail pages in parallel (bounded by semaphore)."""
        logger.info(f"⏳ Starting concurrent scraping for {len(urls)} job details. (Semaphore=1)")
        semaphore = asyncio.Semaphore(1)  # Temporary reduction to avoid rate limiting

        async def _bounded(url: str) -> Optional[RawJobListing]:
            async with semaphore:
                return await self._scrape_job_detail(url)

        tasks = [_bounded(u) for u in urls]
        # Adding a total timeout to gather in case one hangs forever
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=300.0)
            logger.info("✅ Gather completed for job details.")
        except asyncio.TimeoutError:
            logger.error("🛑 Timeout during concurrent detail scraping!")
            results = []

        jobs: List[RawJobListing] = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Detail scrape failed for {urls[i]}: {res}")
            elif res and getattr(res, 'title', None):
                jobs.append(res)

        return jobs

    async def _scrape_job_detail(self, url: str) -> Optional[RawJobListing]:
        """Open a new tab, navigate to *url*, extract everything, close tab."""
        page = None
        try:
            logger.info(f"📄 Scraping detail [START]: {url}")
            page = await self._context.new_page()
            
            # Using networkidle as it was previously proven to bypass empty titles
            await page.goto(url, wait_until="networkidle", timeout=DETAIL_PAGE_TIMEOUT)
            await asyncio.sleep(2)  # Let dynamic widgets render

            job = RawJobListing(source_platform="naukri", source_url=url)

            # --- Primary source: JSON-LD structured data ---
            logger.info(f"📄 Scraping detail [JSON-LD] {url}")
            jsonld = await self._extract_jsonld(page)
            if jsonld:
                self._populate_from_jsonld(job, jsonld)

            # --- Secondary: HTML selectors (fill gaps / override) ---
            logger.info(f"📄 Scraping detail [HTML] {url}")
            await self._extract_html_details(page, job)
            
            # --- Job ID from URL ---
            if not job.source_job_id:
                match = re.search(r'-(\d{10,})(?:\?|$)', url)
                if match:
                    job.source_job_id = match.group(1)

            # --- Apply URL is the job page itself ---
            if not job.apply_url:
                job.apply_url = url

            # Polite delay per page
            await asyncio.sleep(0.5)
            
            logger.info(f"✅ Scraping detail [DONE]: {url}")
            return job

        except Exception as e:
            logger.error(f"❌ Error scraping detail page {url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    # ------------------------------------------------------------------
    # JSON-LD extraction
    # ------------------------------------------------------------------
    async def _extract_jsonld(self, page: Page) -> Optional[Dict[str, Any]]:
        """Parse the first JobPosting JSON-LD block on the page."""
        try:
            scripts = await page.evaluate("""
                () => {
                    const tags = document.querySelectorAll('script[type="application/ld+json"]');
                    return Array.from(tags).map(s => s.textContent);
                }
            """)
            for raw in (scripts or []):
                try:
                    data = json.loads(raw)
                    if data.get("@type") == "JobPosting":
                        return data
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.debug(f"JSON-LD extraction error: {e}")
        return None

    def _populate_from_jsonld(self, job: RawJobListing, ld: Dict[str, Any]):
        """Map JSON-LD JobPosting schema → RawJobListing fields."""
        job.title            = ld.get("title", job.title)
        job.date_posted_iso  = ld.get("datePosted", "")
        job.valid_through    = ld.get("validThrough", "")
        job.employment_type  = ld.get("employmentType", "")

        # Description (HTML string)
        desc = ld.get("description", "")
        if desc:
            job.description_html = desc
            # Strip HTML tags for plain text version
            job.description_raw = re.sub(r"<[^>]+>", " ", desc)
            job.description_raw = re.sub(r"\s+", " ", job.description_raw).strip()

        # Company
        org = ld.get("hiringOrganization") or {}
        job.company_name     = org.get("name", job.company_name)
        job.company_logo_url = org.get("logo", job.company_logo_url)

        # Location
        loc = ld.get("jobLocation") or {}
        address = loc.get("address") or {}
        localities = address.get("addressLocality") or []
        if isinstance(localities, list) and localities:
            job.location = ", ".join(str(l) for l in localities if l and str(l) != "-")
        elif isinstance(localities, str):
            job.location = localities

        # Salary
        salary = ld.get("baseSalary") or {}
        val = salary.get("value") or {}
        salary_amt = val.get("value", "")
        salary_unit = val.get("unitText", "")
        currency = salary.get("currency", "")
        if salary_amt:
            job.salary_text = f"{currency} {salary_amt} {salary_unit}".strip()

        # Experience
        exp = ld.get("experienceRequirements") or {}
        months = exp.get("monthsOfExperience")
        if months:
            try:
                years = int(months) // 12
                job.experience_text = job.experience_text or f"{years}+ years"
            except (ValueError, TypeError):
                pass

        # Skills
        skills = ld.get("skills") or []
        if isinstance(skills, list):
            job.skills_list = [s.strip() for s in skills if s]
            job.skills_text = ", ".join(job.skills_list)

        # Education
        qual = ld.get("qualifications") or {}
        edu_level = qual.get("educationalLevel", "")
        if edu_level:
            job.education_ug = edu_level

        # Role category / industry
        job.role            = ld.get("responsibilities", "")
        job.industry_type   = ld.get("industry", "")
        occ = ld.get("occupationalCategory", "")
        if occ:
            job.department = occ

        # ID
        identifier = ld.get("identifier") or {}
        val_id = identifier.get("value", "")
        if val_id:
            job.source_job_id = str(val_id)

    # ------------------------------------------------------------------
    # HTML selector extraction (fills gaps not in JSON-LD)
    # ------------------------------------------------------------------
    async def _extract_html_details(self, page: Page, job: RawJobListing):
        """Extract data from visible HTML elements to complement JSON-LD."""

        # Title fallback
        if not job.title:
            job.title = await self._text(page, "h1.styles_jd-header-title__rZwM1")

        # Company fallback
        if not job.company_name:
            job.company_name = await self._text(
                page, ".styles_jd-header-comp-name__MvqAI a"
            )

        # Experience from header (more readable than JSON-LD months)
        exp_text = await self._text(page, ".styles_jhc__exp__k_giM span")
        if exp_text:
            job.experience_text = exp_text

        # Salary from header
        sal_text = await self._text(page, ".styles_jhc__salary__jdfEC span")
        if sal_text and sal_text != "Not Disclosed":
            job.salary_text = sal_text
        elif sal_text:
            job.salary_text = sal_text

        # Location from header
        loc_text = await self._text(page, ".styles_jhc__location__W_pVs a")
        if loc_text:
            job.location = loc_text

        # Posted date & applicants from stat spans
        stats = await page.query_selector_all(".styles_jhc__stat__PgY67")
        for stat in (stats or []):
            try:
                label_el = await stat.query_selector("label")
                value_el = await stat.query_selector("span")
                if label_el and value_el:
                    label = (await label_el.inner_text()).strip().lower()
                    value = (await value_el.inner_text()).strip()
                    if "posted" in label:
                        job.posted_date = value
                    elif "applicant" in label:
                        try:
                            job.applicants_count = int(
                                value.replace("+", "").replace(",", "").strip()
                            )
                        except ValueError:
                            job.extra_data["applicants_text"] = value
            except Exception:
                continue

        # Full description HTML (backup if JSON-LD was missing)
        if not job.description_raw:
            desc_text = await self._text(page, ".styles_JDC__dang-inner-html__h0K4t")
            if desc_text:
                job.description_raw = desc_text

        # ---- Key Skills (preferred vs other) ----
        preferred_skills: List[str] = []
        other_skills: List[str] = []

        skill_chips = await page.query_selector_all(".styles_chip__7YCfG")
        for chip in (skill_chips or []):
            try:
                text_el = await chip.query_selector("span")
                if not text_el:
                    continue
                skill_text = (await text_el.inner_text()).strip()
                if not skill_text:
                    continue

                # Check if this chip has the preferred star icon
                star = await chip.query_selector("i.ni-icon-jd-save")
                if star:
                    preferred_skills.append(skill_text)
                else:
                    other_skills.append(skill_text)
            except Exception:
                continue

        if preferred_skills:
            job.skills_preferred = preferred_skills
        if preferred_skills or other_skills:
            all_skills = preferred_skills + other_skills
            job.skills_list = all_skills
            job.skills_text = ", ".join(all_skills)

        # ---- Role / Industry / Department / Employment Type ----
        detail_rows = await page.query_selector_all(".styles_details__Y424J")
        for row in (detail_rows or []):
            try:
                label_el = await row.query_selector("label")
                span_el  = await row.query_selector("span")
                if not label_el or not span_el:
                    continue
                label = (await label_el.inner_text()).strip().rstrip(":").lower()
                value = (await span_el.inner_text()).strip().rstrip(",")

                if "role" == label:
                    job.role = value
                elif "industry" in label:
                    job.industry_type = value
                elif "department" in label:
                    job.department = value
                elif "employment" in label:
                    job.employment_type = value
                elif "role category" in label:
                    job.role_category = value
            except Exception:
                continue

        # ---- Education ----
        edu_rows = await page.query_selector_all(".styles_education__KXFkO .styles_details__Y424J")
        for row in (edu_rows or []):
            try:
                label_el = await row.query_selector("label")
                span_el  = await row.query_selector("span")
                if not label_el or not span_el:
                    continue
                label = (await label_el.inner_text()).strip().rstrip(":").lower()
                value = (await span_el.inner_text()).strip()
                if "ug" in label:
                    job.education_ug = value
                elif "pg" in label:
                    job.education_pg = value
            except Exception:
                continue

        # ---- Company rating ----
        if not job.company_rating:
            rating_text = await self._text(page, ".styles_amb-rating__4UyFL")
            if rating_text:
                try:
                    job.company_rating = float(rating_text)
                except ValueError:
                    pass

        # ---- Company logo ----
        if not job.company_logo_url:
            logo_el = await page.query_selector(
                "img.styles_jhc__comp-banner__ynBvr"
            )
            if logo_el:
                src = await logo_el.get_attribute("src")
                if src:
                    job.company_logo_url = src

        # ---- Extra: benefits, salary insights, awards ----
        benefits = await page.query_selector_all(".styles_pbc__benefit-label__z3NAT")
        if benefits:
            job.extra_data["benefits_perks"] = []
            for b in benefits:
                try:
                    text = (await b.inner_text()).strip()
                    if text:
                        job.extra_data["benefits_perks"].append(text)
                except Exception:
                    continue

        salary_insight = await self._text(page, ".styles_sic__typical-range__Mh_OW")
        if salary_insight:
            job.extra_data["salary_insight_range"] = salary_insight

        awards = await page.query_selector_all(".styles_arc__item__hg_su")
        if awards:
            job.extra_data["awards"] = []
            for award in awards:
                try:
                    year = await self._text_from(award, ".styles_arc__year__jcImB")
                    title = await self._text_from(award, ".styles_arc__title__WYLCL")
                    if year and title:
                        job.extra_data["awards"].append(f"{year} - {title}")
                except Exception:
                    continue

        # ---- Extra: company tags ----
        comp_tags = await page.query_selector_all(
            ".styles_company-info-tags__y6RDs .styles_chips__AKDM0"
        )
        if comp_tags:
            job.extra_data["company_tags"] = []
            for tag in comp_tags:
                try:
                    text = (await tag.inner_text()).strip()
                    if text:
                        job.extra_data["company_tags"].append(text)
                except Exception:
                    continue

        # ---- Extra: company website & address ----
        info_rows = await page.query_selector_all(".styles_comp-info-detail__4xVBr")
        for row in (info_rows or []):
            try:
                label_el = await row.query_selector("label")
                span_el  = await row.query_selector("span")
                if not label_el or not span_el:
                    continue
                label = (await label_el.inner_text()).strip().rstrip(":").lower()
                value = (await span_el.inner_text()).strip()
                if "link" in label:
                    job.extra_data["company_website"] = value
                    # Also grab the actual href
                    link_el = await span_el.query_selector("a")
                    if link_el:
                        href = await link_el.get_attribute("href")
                        if href:
                            job.extra_data["company_website_url"] = href
                elif "address" in label:
                    job.extra_data["company_address"] = value
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Tiny helpers
    # ------------------------------------------------------------------
    async def _text(self, page: Page, selector: str) -> str:
        """Return trimmed inner text of the first element matching *selector*."""
        try:
            el = await page.query_selector(selector)
            if el:
                return (await el.inner_text()).strip()
        except Exception:
            pass
        return ""

    async def _text_from(self, parent, selector: str) -> str:
        """Return trimmed inner text of *selector* inside a parent element handle."""
        try:
            el = await parent.query_selector(selector)
            if el:
                return (await el.inner_text()).strip()
        except Exception:
            pass
        return ""
