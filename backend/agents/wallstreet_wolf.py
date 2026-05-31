"""Wallstreet Wolf — tracks 20+ stocks, generates LLM commentary, emails daily report."""
import yfinance as yf
from datetime import datetime
from agents.base_agent import BaseAgent
from llm_client import query_llm
from email_utils import send_html_email, EMAIL_BASE_STYLE
from database import get_db, log_agent, StockSnapshot
from config import STOCK_TICKERS


class WallstreetWolfAgent(BaseAgent):
    name = "wallstreet_wolf"

    def _execute(self) -> dict:
        snapshots = _fetch_stocks(STOCK_TICKERS, self.name)
        commentary = _generate_market_commentary(snapshots)
        _save_snapshots(snapshots, self.name)
        html = _build_email(snapshots, commentary)
        subject = f"📈 Wallstreet Wolf — Market Report {datetime.now().strftime('%b %d, %Y')}"
        send_html_email(subject, html, agent_name=self.name)

        gainers = [s for s in snapshots if s["change_pct"] > 0]
        losers  = [s for s in snapshots if s["change_pct"] < 0]
        return {
            "summary": f"Tracked {len(snapshots)} stocks — {len(gainers)} up, {len(losers)} down",
            "count": len(snapshots),
            "gainers": len(gainers),
            "losers": len(losers),
        }


def _fetch_stocks(tickers: list[str], agent_name: str) -> list[dict]:
    snapshots = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            price      = float(getattr(info, "last_price", 0) or 0)
            prev_close = float(getattr(info, "previous_close", price) or price)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            volume     = float(getattr(info, "three_month_average_volume", 0) or 0)
            market_cap = float(getattr(info, "market_cap", 0) or 0)
            snapshots.append({
                "ticker":     ticker,
                "price":      round(price, 2),
                "change_pct": round(change_pct, 2),
                "volume":     volume,
                "market_cap": market_cap,
            })
        except Exception as e:
            with get_db() as db:
                log_agent(db, agent_name, "WARN", f"{ticker}: {e}")
    return snapshots


def _generate_market_commentary(snapshots: list[dict]) -> str:
    top5 = sorted(snapshots, key=lambda x: abs(x["change_pct"]), reverse=True)[:5]
    summary_lines = [
        f"{s['ticker']}: ${s['price']} ({'+' if s['change_pct'] >= 0 else ''}{s['change_pct']}%)"
        for s in top5
    ]
    prompt = (
        "You are a sharp Wall Street analyst. Given today's top movers:\n"
        + "\n".join(summary_lines)
        + "\n\nWrite a punchy 3-sentence market commentary. Be specific, insightful, no fluff."
    )
    return query_llm(prompt, system="You are a Wall Street analyst writing a daily market brief.")


def _save_snapshots(snapshots: list[dict], agent_name: str):
    with get_db() as db:
        for s in snapshots:
            db.add(StockSnapshot(
                ticker=s["ticker"],
                price=s["price"],
                change_pct=s["change_pct"],
                volume=s["volume"],
                market_cap=s.get("market_cap"),
            ))
        log_agent(db, agent_name, "INFO", f"Saved {len(snapshots)} stock snapshots")


def _stock_row(s: dict) -> str:
    sign  = "+" if s["change_pct"] >= 0 else ""
    cls   = "up" if s["change_pct"] >= 0 else "down"
    arrow = "▲" if s["change_pct"] >= 0 else "▼"
    mc    = f"${s['market_cap']/1e9:.1f}B" if s.get("market_cap") else "—"
    return (
        f'<tr>'
        f'<td style="padding:8px;font-weight:700;color:#1a1a2e">{s["ticker"]}</td>'
        f'<td style="padding:8px">${s["price"]:.2f}</td>'
        f'<td style="padding:8px" class="{cls}">{arrow} {sign}{s["change_pct"]:.2f}%</td>'
        f'<td style="padding:8px;color:#888">{mc}</td>'
        f'</tr>'
    )


def _build_email(snapshots: list[dict], commentary: str) -> str:
    sorted_snaps = sorted(snapshots, key=lambda x: x["change_pct"], reverse=True)
    rows = "".join(_stock_row(s) for s in sorted_snaps)

    gainers = len([s for s in snapshots if s["change_pct"] > 0])
    losers  = len([s for s in snapshots if s["change_pct"] < 0])
    avg_chg = sum(s["change_pct"] for s in snapshots) / len(snapshots) if snapshots else 0

    return f"""<!DOCTYPE html><html><head>{EMAIL_BASE_STYLE}</head><body>
    <div class="container">
      <div class="header" style="background:linear-gradient(135deg,#064e3b,#065f46);">
        <h1>📈 Wallstreet Wolf</h1>
        <div class="sub">Daily Market Report &bull; {datetime.now().strftime('%A, %B %d, %Y')}</div>
      </div>
      <div class="body">
        <div style="text-align:center;margin-bottom:24px;">
          <div class="metric"><div class="val">{len(snapshots)}</div><div class="lbl">Stocks Tracked</div></div>
          <div class="metric"><div class="val up">{gainers}</div><div class="lbl">Gainers</div></div>
          <div class="metric"><div class="val down">{losers}</div><div class="lbl">Losers</div></div>
          <div class="metric"><div class="val {'up' if avg_chg >= 0 else 'down'}">{'+' if avg_chg >= 0 else ''}{avg_chg:.2f}%</div><div class="lbl">Avg Change</div></div>
        </div>

        <div class="card" style="border-color:#065f46;background:#f0fdf4;">
          <h3>🤖 AI Market Commentary</h3>
          <p>{commentary}</p>
        </div>

        <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:16px;">
          <tr style="background:#f8f9fa;font-weight:600;">
            <th style="padding:8px;text-align:left">Ticker</th>
            <th style="padding:8px;text-align:left">Price</th>
            <th style="padding:8px;text-align:left">Change</th>
            <th style="padding:8px;text-align:left">Mkt Cap</th>
          </tr>
          {rows}
        </table>
      </div>
      <div class="footer">Wallstreet Wolf &bull; Data via Yahoo Finance &bull; Commentary by Qwen3</div>
    </div></body></html>"""
