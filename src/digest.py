import datetime
import logging
import os
import os.path
import sqlite3
from typing import Any
from urllib.parse import parse_qs, urlparse

import jinja2
import requests
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Email, HtmlContent, Mail, To

logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)

PROGRESS_INTERVAL = 10
N_TOP_STORIES = 50


class Storage:
    """
    A simple SQLite database to store HN stories.
    """

    def __init__(self, fname: str):
        self.conn = sqlite3.connect(fname)
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER UNIQUE,
                title TEXT,
                url TEXT,
                score INTEGER,
                comments INTEGER,
                published INTEGER
            )
            """
        )

    def filter_known_stories(self, ids: list[int]) -> list[int]:
        """
        Check if any of the stories are already in the database.

        Return a list of IDs of the stories that are already known.
        """

        cur = self.conn.cursor()

        ids_tuple = tuple(set(int(id) for id in ids))

        cur.execute(
            f"SELECT id FROM stories WHERE id IN {tuple(ids)}",
        )
        row = cur.fetchall()
        return [r[0] for r in row]


    def store_story(self, item: dict[str, Any]) -> bool:
        """
        Store a single HN story in the database.
        """

        cur = self.conn.cursor()

        cur.execute(
            """
            INSERT INTO stories (id, title, url, score, comments, published)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["title"],
                item.get("url", ""),
                item["score"],
                item["comments"],
                item["time"],
            )
        )
        self.conn.commit()
        return True


def get_top_story_ids() -> list[int]:
    """
    Fetch IDs from the HN top stories.
    """

    base_url = os.environ.get("HN_BASE_URL")
    url = f"{base_url}/topstories.json"

    response = requests.get(url)
    if not response.ok:
        log.error(f"Failed to fetch top stories: {response.status_code}")
        return []

    return response.json()


def get_stories_for_ids(hn_ids: list[int]) -> list[dict[str, Any]]:
    """
    Fetch HN story contents for the given IDs.
    """

    base_url = os.environ.get("HN_BASE_URL")
    stories = []

    for i, hn_id in enumerate(hn_ids):
        url = f"{base_url}/item/{hn_id}.json"

        if i % PROGRESS_INTERVAL == 0:
            log.info(f"Fetching article {(i + 1)}/{len(hn_ids)} ...")

        response = requests.get(url)
        if not response.ok:
            log.warning(f"Failed to fetch article {hn_id}: {response.status_code}")
            continue
        item = response.json()
        if item.get("type") != "story":
            continue
        item["comments"] = item["descendants"]
        item["hnlink"] = f"https://news.ycombinator.com/item?id={hn_id}"
        stories.append(item)

    return stories


def prepare_daily_digest(items: list[dict[str, Any]]) -> str:
    """
    Prepare the daily digest email with the new stories.
    """
    template_path = os.path.join(os.path.dirname(__file__), "template.html")
    template = jinja2.Template(open(template_path).read())
    return template.render(
        items=items,
        date=datetime.date.today().strftime("%A, %B %d, %Y"),
    )


def send_daily_digest(content: str) -> None:
    """
    Send a daily digest email with the new articles using Sendgrid.
    """

    # Fetch the Sendgrid API key from the environment
    api_key = os.environ.get("SENDGRID_API_KEY")

    from_email = os.environ.get("FROM_EMAIL")
    recipient = os.environ.get("RECIPIENT_EMAIL")

    # Initialize the Sendgrid client
    sg = SendGridAPIClient(api_key)

    # Send the email
    message = Mail(
        Email(from_email),
        To(recipient),
        "Hacker News Daily Digest",
        HtmlContent(content),
    )
    response = sg.send(message)
    if response.status_code != 202:
        log.error(f"Failed to send email: {response.status_code}")


def run_daily_digest():
    """
    Run the daily digest process.
    """

    load_dotenv()
    db_path = os.environ.get("DB_PATH")
    storage = Storage(db_path)

    top_story_ids = get_top_story_ids()
    known_story_ids = set(storage.filter_known_stories(top_story_ids))
    new_story_ids = [ id for id in top_story_ids if id not in known_story_ids]
    new_stories = get_stories_for_ids(new_story_ids)

    for article in new_stories:
        storage.store_story(article)

    sorted_stories = sorted(new_stories, key=lambda x: x["score"] + x["comments"], reverse=True)
    top_sorted_stories = sorted_stories[:N_TOP_STORIES]

    if new_stories:
        content = prepare_daily_digest(top_sorted_stories)
        send_daily_digest(content)


if __name__ == "__main__":
    run_daily_digest()
