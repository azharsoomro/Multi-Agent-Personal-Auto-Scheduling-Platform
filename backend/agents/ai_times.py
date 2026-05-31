"""AI-Times — fetches top AI YouTube videos and emails an HTML digest."""
import requests
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from llm_client import query_llm
from email_utils import send_html_email, EMAIL_BASE_STYLE
from database import get_db, log_agent
from config import YOUTUBE_API_KEY, EMAIL_RECIPIENT

SEARCH_QUERIES = [
    "artificial intelligence 2025",
    "large language models tutorial",
    "AI agents automation",
    "machine learning breakthrough",
]
RESULTS_PER_QUERY = 5


class AITimesAgent(BaseAgent):
    name = "ai_times"

    def _execute(self) -> dict:
        if not YOUTUBE_API_KEY:
            # demo mode — return mock data so the agent still works
            videos = _mock_videos()
        else:
            videos = _fetch_youtube_videos()

        with get_db() as db:
            log_agent(db, self.name, "INFO", f"Fetched {len(videos)} videos")

        llm_intro = query_llm(
            f"Write a 2-sentence enthusiastic introduction for a daily AI video digest "
            f"featuring {len(videos)} curated videos. Keep it under 40 words.",
            system="You are an AI newsletter editor.",
        )

        html = _build_email(videos, llm_intro)
        subject = f"🤖 AI-Times Daily Digest — {datetime.now().strftime('%b %d, %Y')}"
        send_html_email(subject, html, agent_name=self.name)

        return {"summary": f"Sent digest with {len(videos)} videos", "count": len(videos)}


def _fetch_youtube_videos() -> list[dict]:
    published_after = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen, videos = set(), []

    for query in SEARCH_QUERIES:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "relevance",
            "publishedAfter": published_after,
            "maxResults": RESULTS_PER_QUERY,
            "key": YOUTUBE_API_KEY,
        }
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/search",
                             params=params, timeout=15)
            r.raise_for_status()
            for item in r.json().get("items", []):
                vid_id = item["id"].get("videoId", "")
                if not vid_id or vid_id in seen:
                    continue
                seen.add(vid_id)
                snip = item["snippet"]
                videos.append({
                    "title":     snip["title"],
                    "channel":   snip["channelTitle"],
                    "published": snip["publishedAt"][:10],
                    "url":       f"https://youtu.be/{vid_id}",
                    "thumbnail": snip.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "description": snip.get("description", "")[:200],
                })
        except Exception:
            pass

    return videos[:20]


def _mock_videos() -> list[dict]:
    return [
        {
            "title": "Qwen3: The Best Open Source LLM Yet?",
            "channel": "AI Explained",
            "published": datetime.now().strftime("%Y-%m-%d"),
            "url": "https://youtu.be/example1",
            "thumbnail": "",
            "description": "Deep dive into Qwen3's capabilities and benchmarks.",
        },
        {
            "title": "Building Multi-Agent Systems with Local LLMs",
            "channel": "Andrej Karpathy",
            "published": datetime.now().strftime("%Y-%m-%d"),
            "url": "https://youtu.be/example2",
            "thumbnail": "",
            "description": "A practical guide to orchestrating AI agents locally.",
        },
        {
            "title": "GPT-5 vs Local Models: Surprising Results",
            "channel": "Two Minute Papers",
            "published": datetime.now().strftime("%Y-%m-%d"),
            "url": "https://youtu.be/example3",
            "thumbnail": "",
            "description": "Comparing frontier models against open-source alternatives.",
        },
    ]


def _build_email(videos: list[dict], intro: str) -> str:
    cards = ""
    for v in videos:
        thumb = f'<img src="{v["thumbnail"]}" style="width:100%;border-radius:6px;margin-bottom:10px;">' \
                if v.get("thumbnail") else ""
        cards += f"""
        <div class="card">
          {thumb}
          <h3><a href="{v['url']}" style="color:#4f46e5;text-decoration:none;">{v['title']}</a></h3>
          <p><span class="tag">{v['channel']}</span>
             <span class="tag">{v['published']}</span></p>
          <p style="margin-top:8px;">{v['description']}</p>
        </div>"""

    return f"""<!DOCTYPE html><html><head>{EMAIL_BASE_STYLE}</head><body>
    <div class="container">
      <div class="header">
        <h1>🤖 AI-Times Daily Digest</h1>
        <div class="sub">{datetime.now().strftime('%A, %B %d, %Y')} &bull; {len(videos)} videos curated</div>
      </div>
      <div class="body">
        <p style="color:#555;font-size:14px;line-height:1.7;">{intro}</p>
        {cards}
      </div>
      <div class="footer">Powered by Multi-Agent Platform &bull; Local AI (Qwen3 via Ollama)</div>
    </div></body></html>"""
