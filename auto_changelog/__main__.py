import re
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, SecretStr, BaseSettings


class Settings(BaseSettings):
    input_changelog_file: Path = Path("CHANGELOG.md")
    input_latest_changes_position: str = "# Changelog\n\n"
    input_latest_changes_title: str = "## Latest changes"
    input_replace_regex: str = r"(?<=## Latest Changes\n)[\s\S]*(?=\n## )"
    input_changelog_body: Optional[str] = None
    input_archive_regex: str = r"(?<=## )Latest Changes(?=\n)"
    input_archive_title: Optional[str] = None


logging.basicConfig(level=logging.INFO)

settings = Settings()  # type: ignore
logging.debug(f"Settings: {settings.json()}")

if not settings.input_changelog_file.is_file():
    logging.error(f"Input changelog file not found: {settings.input_changelog_file}")
    sys.exit(1)

source = settings.input_changelog_file.read_text()

new_content: str
if settings.input_archive_title:
    new_content, replaced = re.subn(
        settings.input_archive_regex, settings.input_archive_title, source, count=1
    )
    if not replaced:
        logging.error(f"Archive title not found: {replaced}")
        sys.exit(0)
elif settings.input_changelog_body:
    new_content, replaced = re.subn(
        settings.input_replace_regex,
        "\n" + settings.input_changelog_body.strip("\n") + "\n",
        source,
        count=1,
    )
    if not replaced:
        logging.warning(f"Changelog body not found: {replaced}, insert new one")
        match = re.search(settings.input_latest_changes_position, source)
        if not match:
            logging.error(f"Latest changes position not found: {match}")
            sys.exit(1)
        pre_content = source[: match.end()]
        post_content = source[match.end() :]
        new_content = (
            pre_content
            + settings.input_latest_changes_title
            + "\n\n"
            + settings.input_changelog_body.strip("\n")
            + "\n\n"
            + post_content
        )
else:
    logging.error("Error input changelog body or archive title")
    sys.exit(1)

settings.input_changelog_file.write_text(new_content)
logging.info(f"Committing changes to: {settings.input_changelog_file}")

subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
subprocess.run(["git", "add", str(settings.input_changelog_file)], check=True)
subprocess.run(["git", "commit", "-m", ":memo: Update release notes"], check=True)
logging.info(f"Pushing changes: {settings.input_changelog_file}")
subprocess.run(["git", "push"], check=True)
logging.info("Finished")
