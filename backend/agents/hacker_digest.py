"""Hacker Digest — fetches top HN stories, summarizes with LLM, emails digest.

Custom agent: uses Hacker News public API (no key needed) + local Qwen3.
Solves the real problem of information overload from HN — delivers only what matters.
"""
import requests
from datetime import datetime
from agents.base_agent import BaseAgent
from llm_client import query_llm
from email_utils import send_html_email, EMAIL_BASE_STYLE
from database import get_db, log_agent

HN_TOP_URL    = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL   = "https://hacker-news.firebaseio.com/v0/item/{}.json"
STORIES_LIMIT = 30  # fetch top 30, summarize best


class HackerDigestAgent(BaseAgent):
    name = "hacker_digest"

    def _execute(self) -> dict:
        stories = _fetch_top_stories(STORIES_LIMIT)
        with get_db() as db:
            log_agent(db, self.name, "INFO", f"Fetched {len(stories)} stories from HN")

        # LLM rates and summarizes each story title/url
        curated = _curate_stories(stories)
        overall = _generate_overview(curated)

        html = _build_email(curated, overall)
        subject = f"🔥 Hacker Digest — {datetime.now().strftime('%b %d, %Y')}"
        send_html_email(subject, html, agent_name=self.name)

        return {
            "summary": f"Sent digest of {len(curated)} curated stories",
            "total_fetched": len(stories),
            "curated": len(curated),
        }


def _fetch_top_stories(limit: int) -> list[dict]:
    ids = requests.get(HN_TOP_URL, timeout=10).json()[:limit]
    stories = []
    for sid in ids:
        try:
            item = requests.get(HN_ITEM_URL.format(sid), timeout=8).json()
            if item and item.get("type") == "story" and item.get("title"):
                stories.append({
                    "id":      sid,
                    "title":   item.get("title", ""),
                    "url":     item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "score":   item.get("score", 0),
                    "comments":item.get("descendants", 0),
                    "by":      item.get("by", ""),
                    "hn_url":  f"https://news.ycombinator.com/item?id={sid}",
                })
        except Exception:
            pass
    return sorted(stories, key=lambda x: x["score"], reverse=True)


def _curate_stories(stories: list[dict]) -> list[dict]:
    """Add a one-line takeaway to each of the top 10 stories (by score)."""
    import json
    top10 = stories[:10]
    curated = []
    for s in top10:
        prompt = (
            f"In one sentence (max 15 words), why does this Hacker News story matter "
            f"to a software engineer?\nTitle: {s['title']}\nOutput only the sentence."
        )
        try:
            takeaway = query_llm(prompt, system="You are a concise tech writer. One sentence only.")
            takeaway = takeaway.strip().strip('"')
        except Exception:
            takeaway = ""
        curated.append({**s, "takeaway": takeaway})
    return curated


def _generate_overview(curated: list[dict]) -> str:
    titles = ", ".join(s["title"] for s in curated[:5])
    return query_llm(
        f"In 2 sentences, summarize today's tech conversation on Hacker News. "
        f"Top stories include: {titles}. Be specific and insightful.",
        system="You are a tech journalist writing a brief daily overview."
    )


def _build_email(stories: list[dict], overview: str) -> str:
    cards = ""
    for i, s in enumerate(stories, 1):
        cards += f"""
        <div class="card" style="border-color:{'#f97316' if i <= 3 else '#4f46e5'}">
          <h3>#{i} &nbsp;<a href="{s['url']}" style="color:#1a1a2e;text-decoration:none;">{s['title']}</a></h3>
          <p>
            <span class="tag">▲ {s['score']}</span>
            <span class="tag">💬 {s['comments']}</span>
            <span class="tag">by {s['by']}</span>
            &nbsp;&nbsp;<a href="{s['hn_url']}" style="color:#4f46e5;font-size:12px;">HN Discussion →</a>
          </p>
          {f'<p style="margin-top:8px;font-style:italic;color:#555">{s["takeaway"]}</p>' if s.get("takeaway") else ""}
        </div>"""

    return f"""<!DOCTYPE html><html><head>{EMAIL_BASE_STYLE}</head><body>
    <div class="container">
      <div class="header" style="background:linear-gradient(135deg,#7c2d12,#c2410c);">
        <h1>🔥 Hacker Digest</h1>
        <div class="sub">Top {len(stories)} stories from Hacker News &bull;
             {datetime.now().strftime('%A, %B %d, %Y')}</div>
      </div>
      <div class="body">
        <div class="card" style="border-color:#c2410c;background:#fff7ed;">
          <h3>🤖 Today's Tech Pulse</h3>
          <p>{overview}</p>
        </div>
        {cards}
      </div>
      <div class="footer">Hacker Digest Agent &bull; Data from Hacker News API &bull; Curated by Qwen3</div>
    </div></body></html>"""
