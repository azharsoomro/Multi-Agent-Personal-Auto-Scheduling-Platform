"""AI-Times — fetches 5 AI news + 5 AI personality YouTube videos and emails an HTML digest."""
import requests
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from llm_client import query_llm
from email_utils import send_html_email, EMAIL_BASE_STYLE
from database import get_db, log_agent, VideoRecord
from config import YOUTUBE_API_KEY, EMAIL_RECIPIENT

# News-focused queries (publications, outlets, research orgs)
NEWS_QUERIES = [
    "AI news this week 2025",
    "artificial intelligence breakthrough research",
]
# Personality/educator queries (known AI creators & educators)
PERSONALITY_QUERIES = [
    "Andrej Karpathy AI tutorial",
    "Two Minute Papers AI",
    "Yannic Kilcher paper explained",
]
RESULTS_PER_QUERY = 3   # fetches a pool then trims to 5 per category


class AITimesAgent(BaseAgent):
    name = "ai_times"

    def _execute(self) -> dict:
        if not YOUTUBE_API_KEY:
            news, personalities = _mock_videos()
        else:
            news        = _search_youtube(NEWS_QUERIES,        limit=5)
            personalities = _search_youtube(PERSONALITY_QUERIES, limit=5)

        total = len(news) + len(personalities)
        with get_db() as db:
            log_agent(db, self.name, "INFO",
                      f"Fetched {len(news)} news + {len(personalities)} personality videos")
            # persist to DB (upsert by URL)
            for v in news:
                _upsert_video(db, v, "news")
            for v in personalities:
                _upsert_video(db, v, "personality")

        llm_intro = query_llm(
            f"Write a 2-sentence enthusiastic introduction for a daily AI video digest "
            f"with {len(news)} news videos and {len(personalities)} creator highlights. "
            f"Keep it under 40 words.",
            system="You are an AI newsletter editor.",
        )

        html = _build_email(news, personalities, llm_intro)
        subject = f"🤖 AI-Times Daily Digest — {datetime.now().strftime('%b %d, %Y')}"
        send_html_email(subject, html, agent_name=self.name)

        return {
            "summary": f"Sent digest with {len(news)} news + {len(personalities)} personality videos",
            "news": len(news),
            "personalities": len(personalities),
        }


def _search_youtube(queries: list[str], limit: int = 5) -> list[dict]:
    published_after = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen, videos = set(), []

    for query in queries:
        if len(videos) >= limit:
            break
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
                    "title":       snip["title"],
                    "channel":     snip["channelTitle"],
                    "published":   snip["publishedAt"][:10],
                    "url":         f"https://youtu.be/{vid_id}",
                    "thumbnail":   snip.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "description": snip.get("description", "")[:200],
                })
        except Exception:
            pass

    return videos[:limit]


def _thumb(vid_id: str) -> str:
    """YouTube thumbnail URL — mqdefault is 320×180, always available."""
    return f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg"

def _yt(vid_id: str) -> str:
    return f"https://youtu.be/{vid_id}"

def _mock_videos() -> tuple[list[dict], list[dict]]:
    """
    Uses real YouTube video IDs so thumbnails load and links open on YouTube.
    All 10 IDs are unique to avoid DB UNIQUE constraint violations.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # ── 5 AI News / Research videos ──────────────────────────────────────────
    news = [
        {
            "title": "Let's build GPT: from scratch, in code, spelled out",
            "channel": "Andrej Karpathy", "published": today,
            "url": _yt("kCc8FmEb1nY"), "thumbnail": _thumb("kCc8FmEb1nY"),
            "description": "Complete walkthrough of building a GPT language model from scratch in PyTorch, "
                           "following 'Attention is All You Need'.",
        },
        {
            "title": "But what is a neural network? | Deep learning chapter 1",
            "channel": "3Blue1Brown", "published": today,
            "url": _yt("aircAruvnKk"), "thumbnail": _thumb("aircAruvnKk"),
            "description": "The foundation of modern AI explained visually — from biological neurons "
                           "to gradient descent and backpropagation.",
        },
        {
            "title": "Attention in transformers, visually explained | Chapter 6",
            "channel": "3Blue1Brown", "published": today,
            "url": _yt("eMlx5fFNoYc"), "thumbnail": _thumb("eMlx5fFNoYc"),
            "description": "How the attention mechanism works inside GPT and every modern large language model.",
        },
        {
            "title": "Intro to Large Language Models",
            "channel": "Andrej Karpathy", "published": today,
            "url": _yt("zjkBMFhNj_g"), "thumbnail": _thumb("zjkBMFhNj_g"),
            "description": "One-hour general-audience introduction to LLMs — what they are, "
                           "how they work, and where the field is heading.",
        },
        {
            "title": "The spelled-out intro to neural networks and backpropagation",
            "channel": "Andrej Karpathy", "published": today,
            "url": _yt("VMj-3S1tku0"), "thumbnail": _thumb("VMj-3S1tku0"),
            "description": "Building micrograd from scratch: a tiny scalar-valued autograd engine "
                           "and neural network library in pure Python.",
        },
    ]

    # ── 5 AI Personality / Creator videos ────────────────────────────────────
    personalities = [
        {
            "title": "The spelled-out intro to language modeling: building makemore",
            "channel": "Andrej Karpathy", "published": today,
            "url": _yt("PaCmpygFfXo"), "thumbnail": _thumb("PaCmpygFfXo"),
            "description": "Part 1 of the makemore series — character-level language model "
                           "trained on names, built from scratch.",
        },
        {
            "title": "Mamba and S4 Explained: Architecture, Parallel Scan, Kernel Fusion",
            "channel": "Yannic Kilcher", "published": today,
            "url": _yt("8Q_tqwpTpVU"), "thumbnail": _thumb("8Q_tqwpTpVU"),
            "description": "Deep dive into state space models as a transformer alternative "
                           "for efficiently handling very long sequences.",
        },
        {
            "title": "GPT-4 Technical Report — Paper Explained",
            "channel": "Yannic Kilcher", "published": today,
            "url": _yt("bCz4OMemCcA"), "thumbnail": _thumb("bCz4OMemCcA"),
            "description": "Yannic breaks down the GPT-4 technical report, safety evaluations, "
                           "and what is and isn't disclosed.",
        },
        {
            "title": "AlphaCode 2 and the Future of AI Coding",
            "channel": "Two Minute Papers", "published": today,
            "url": _yt("wjZofJX0v4M"), "thumbnail": _thumb("wjZofJX0v4M"),
            "description": "DeepMind's AlphaCode 2 reaches competitive programming performance — "
                           "Two Minute Papers breaks down what changed.",
        },
        {
            "title": "Sam Altman: OpenAI CEO on GPT-4, ChatGPT, and the Future of AI",
            "channel": "Lex Fridman", "published": today,
            "url": _yt("L_Guz73e6fw"), "thumbnail": _thumb("L_Guz73e6fw"),
            "description": "3-hour conversation covering AGI timelines, safety, RLHF, "
                           "compute scaling laws, and what comes after GPT-4.",
        },
    ]
    return news, personalities


def _upsert_video(db, v: dict, category: str):
    try:
        existing = db.query(VideoRecord).filter_by(url=v["url"]).first()
        if not existing:
            db.add(VideoRecord(
                title=v["title"], channel=v["channel"], url=v["url"],
                thumbnail=v.get("thumbnail", ""), description=v.get("description", ""),
                published=v["published"], category=category,
            ))
            db.flush()
    except Exception:
        db.rollback()


def _video_card(v: dict, badge_color: str) -> str:
    thumb = (f'<img src="{v["thumbnail"]}" '
             f'style="width:100%;border-radius:6px;margin-bottom:10px;">'
             if v.get("thumbnail") else "")
    return f"""
    <div class="card" style="border-color:{badge_color}">
      {thumb}
      <h3><a href="{v['url']}" style="color:#1a1a2e;text-decoration:none;">{v['title']}</a></h3>
      <p><span class="tag" style="background:{badge_color}">{v['channel']}</span>
         <span class="tag" style="background:#6b7280">{v['published']}</span></p>
      <p style="margin-top:8px;color:#555;font-size:13px;">{v['description']}</p>
    </div>"""


def _build_email(news: list[dict], personalities: list[dict], intro: str) -> str:
    news_cards = "".join(_video_card(v, "#1d4ed8") for v in news)
    pers_cards = "".join(_video_card(v, "#7c3aed") for v in personalities)

    return f"""<!DOCTYPE html><html><head>{EMAIL_BASE_STYLE}</head><body>
    <div class="container">
      <div class="header">
        <h1>🤖 AI-Times Daily Digest</h1>
        <div class="sub">{datetime.now().strftime('%A, %B %d, %Y')} &bull;
             {len(news)} news &bull; {len(personalities)} creator picks</div>
      </div>
      <div class="body">
        <p style="color:#555;font-size:14px;line-height:1.7;">{intro}</p>

        <h2 style="color:#1d4ed8;font-size:16px;margin:24px 0 12px;">
          📰 AI News ({len(news)} videos)</h2>
        {news_cards}

        <h2 style="color:#7c3aed;font-size:16px;margin:24px 0 12px;">
          🎙️ Creator Highlights ({len(personalities)} videos)</h2>
        {pers_cards}
      </div>
      <div class="footer">Powered by Multi-Agent Platform &bull; Local AI (Qwen3 via Ollama)</div>
    </div></body></html>"""
