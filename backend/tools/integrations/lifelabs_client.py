"""LifeLabs MyCareCompass crawler (scaffold).

LifeLabs exposes **no public patient API** for pulling your own results into an
app. The options are:

  * MyCareCompass  - the consumer portal that shows results in a browser.
  * Access Form    - request hard copies / exports by hand.
  * Excelleris Rover / eOrder - provider/EMR integrations only (partner onboarding,
    HL7/XML), not a consumer OAuth/FHIR API.

So for a consumer app the only "automatic" route is to drive the MyCareCompass
portal as the patient (with their own credentials) and download the result
documents, then feed them through the same parser the upload path uses
(:mod:`backend.tools.integrations.lifelabs_pdf`).

This module is a **scaffold**: the interface is defined and wired to the API, but
the browser automation is intentionally left unimplemented for now (the project
is focused on the PDF-upload path first). When implemented it should:

  * Use Playwright with a **persistent context** rooted at
    ``settings.lifelabs_session_dir`` so an MFA/login challenge only has to be
    completed once and the saved session/cookies are reused afterwards.
  * Log in against ``settings.lifelabs_base_url`` (Ontario:
    ``https://on.mycarecompass.lifelabs.com``) using credentials from settings.
  * Enumerate available reports, download each PDF, and return raw bytes that the
    service layer dedupes (by SHA-256) and parses.

NOTE: Crawling an authenticated portal may be subject to the portal's Terms of
Use even when you are accessing your own records. Prefer the upload path; treat
this as an opt-in convenience the account owner explicitly enables.

To implement, add the optional dependency group: ``pip install -e '.[crawler]'``
then ``playwright install chromium``.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings


@dataclass
class RemoteReport:
    """A result document discovered on the portal, ready to ingest."""

    external_id: str
    filename: str
    content: bytes
    collected_label: str | None = None


class LifeLabsCrawlerNotImplemented(NotImplementedError):
    """Raised while the portal crawler is still a scaffold."""


class LifeLabsClient:
    """Drives MyCareCompass to fetch a patient's own result documents.

    Construct with the account credentials (defaults pulled from settings) and
    call :meth:`fetch_reports`. Currently a stub - see module docstring.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        base_url: str | None = None,
        session_dir: str | None = None,
    ) -> None:
        self.username = username or settings.lifelabs_username
        self.password = password or settings.lifelabs_password
        self.base_url = base_url or settings.lifelabs_base_url
        self.session_dir = session_dir or settings.lifelabs_session_dir

    async def fetch_reports(self) -> list[RemoteReport]:
        """Log in, enumerate and download result documents.

        Not yet implemented - use the PDF upload endpoint
        (``POST /lab-records/upload``) instead.
        """
        raise LifeLabsCrawlerNotImplemented(
            "MyCareCompass crawling is not implemented yet. LifeLabs has no public "
            "patient API; for now download the PDF from the portal and upload it via "
            "POST /lab-records/upload. Portal automation is planned via Playwright "
            "(see backend/tools/integrations/lifelabs_client.py)."
        )
