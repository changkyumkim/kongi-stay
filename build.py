"""
hotels.json 을 읽어서 index.html 을 굽는다.

아고다 API 로 사진·성급·평점·리뷰수·제휴링크를 받아 붙인다.
API 가 실패해도 사이트는 만들어진다 (펫 조건만으로).

실행: python build.py
필요: AGODA_SITE_ID, AGODA_API_KEY, AGODA_API_URL (환경변수 또는 .env)
"""
import os
import json
import html
import sys
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    print("requests 가 없습니다: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))

SITE_ID = os.getenv("AGODA_SITE_ID", "").strip()
API_KEY = os.getenv("AGODA_API_KEY", "").strip()
API_URL = os.getenv("AGODA_API_URL", "").strip()


# ── 아고다 ────────────────────────────────────────────
def fetch_agoda(hids):
    """hotelId 목록으로 조회. 실패하면 빈 dict 를 돌려주고 사이트는 계속 만든다."""
    if not (SITE_ID and API_KEY and API_URL and hids):
        print("  아고다 설정이 없거나 hid 가 없습니다. 사진 없이 만듭니다.")
        return {}

    ci = (datetime.now(KST) + timedelta(days=30)).strftime("%Y-%m-%d")
    co = (datetime.now(KST) + timedelta(days=32)).strftime("%Y-%m-%d")

    payload = {
        "criteria": {
            "additional": {
                "currency": "KRW",
                "language": "ko-kr",
                "occupancy": {"numberOfAdult": 2, "numberOfChildren": 0},
            },
            "checkInDate": ci,
            "checkOutDate": co,
            "hotelId": hids,
        }
    }
    headers = {
        "Authorization": f"{SITE_ID}:{API_KEY}",
        "Accept-Encoding": "gzip,deflate",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=40)
    except Exception as e:
        print(f"  아고다 호출 실패: {e}")
        return {}

    if r.status_code != 200:
        print(f"  아고다 응답 {r.status_code} — 사진 없이 만듭니다.")
        return {}

    try:
        results = r.json().get("results", [])
    except Exception:
        print("  아고다 응답을 읽지 못했습니다.")
        return {}

    out = {}
    for x in results:
        out[int(x.get("hotelId"))] = {
            "img": (x.get("imageURL") or "").replace("http://", "https://"),
            "link": x.get("landingURL") or "",
            "star": x.get("starRating"),
            "score": x.get("reviewScore"),
            "count": x.get("reviewCount"),
            "agoda_name": x.get("hotelName") or "",
        }
    print(f"  아고다에서 {len(out)}곳 받았습니다.")
    return out


# ── 조각 ──────────────────────────────────────────────
def e(v):
    return html.escape(str(v)) if v is not None else ""


def won(n):
    return f"{int(n):,}"


def fact(label, value, missing="확인 필요"):
    if value is None or value == "":
        return (f'<div class="fact"><span>{label}</span>'
                f'<b class="none">{missing}</b></div>')
    return f'<div class="fact"><span>{label}</span><b>{value}</b></div>'


def card(h, ag):
    hid = h.get("agoda_hid")
    a = ag.get(hid, {}) if hid else {}

    img = a.get("img", "")
    link = a.get("link") or (
        f"https://www.agoda.com/ko-kr/partners/partnersearch.aspx"
        f"?cid={SITE_ID}&hid={hid}&currency=KRW" if (hid and SITE_ID) else ""
    )

    w = h.get("max_weight_kg")
    ht = h.get("max_height_cm")

    limits = []
    if w is not None:
        limits.append(f"{w}kg 이하")
    if ht is not None:
        limits.append(f"체고 {ht}cm 이하")
    limit_line = " · ".join(limits) if limits else "체중 기준 확인 필요"

    meta = []
    if a.get("star"):
        meta.append(f'{a["star"]:g}성급')
    if a.get("score"):
        cnt = f' ({won(a["count"])}건)' if a.get("count") else ""
        meta.append(f'평점 {a["score"]}{cnt}')

    fee = None
    if h.get("extra_fee_krw") is not None:
        fee = (f'{won(h["extra_fee_krw"])}원'
               + (f' · {e(h["fee_unit"])}' if h.get("fee_unit") else "")) \
            if h["extra_fee_krw"] else "없음"

    dep = None
    if h.get("deposit_krw") is not None:
        dep = f'{won(h["deposit_krw"])}원' if h["deposit_krw"] else "없음"

    vac = None
    if h.get("vaccine_proof") is not None:
        vac = "필요" if h["vaccine_proof"] else "필요 없음"

    com = None
    if h.get("common_area_ok") is not None:
        com = "가능" if h["common_area_ok"] else "제한 있음"

    adv = None
    if h.get("advance_days") is not None:
        adv = f'{h["advance_days"]}일 전까지' if h["advance_days"] else "조건 없음"

    pets = f'{h["max_pets"]}마리' if h.get("max_pets") is not None else None

    note_html = "".join(
        f'<p class="note">{e(p.strip())}</p>'
        for p in str(h.get("note") or "").split("\n") if p.strip())

    city = (h.get("city") or "").strip()
    region = (h.get("region") or "").strip()
    place = city if (not region or region in city) else (city + " · " + region if city else region)

    return f"""
<article class="hotel" id="h{hid if hid else ''}" data-w="{w if w is not None else ''}" data-h="{ht if ht is not None else ''}">
  {f'<img class="photo" src="{e(img)}" alt="{e(h["name"])} 사진" loading="lazy">' if img else '<div class="photo ph"></div>'}
  <div class="body">
    <div class="verdict"></div>
    <h2>{e(h.get("name"))}</h2>
    <p class="where">{e(place)}{" · " + " · ".join(meta) if meta else ""}</p>
    <p class="limit">{e(limit_line)}</p>

    <div class="facts">
      {fact("같이 갈 수 있는 마릿수", pets)}
      {fact("추가 요금", fee)}
      {fact("보증금", dep)}
      {fact("접종 증명", vac)}
      {fact("로비·식당 동반", com)}
      {fact("미리 예약", adv)}
    </div>

    {f'<p class="blocked"><b>받지 않는 경우</b> — {e(h["breed_blocked"])}</p>' if h.get("breed_blocked") else ""}
    {f'<p class="extra">{e(h["amenity"])}</p>' if h.get("amenity") else ""}
    {f'<p class="extra">{e(h["facility"])}</p>' if h.get("facility") else ""}
    {f'<div class="tip-wrap"><span class="tip">{e(h["tip"])}</span></div>' if h.get("tip") else ""}
    {note_html}

    {f'<a class="cta" href="{e(link)}" target="_blank" rel="nofollow sponsored noopener">아고다에서 방 보기</a>' if link else ""}

    <p class="src">
      {f'<a href="{e(h["source_url"])}" target="_blank" rel="noopener nofollow">호텔 공식 규정</a>' if h.get("source_url") else "출처 확인 필요"}
      {" · " + e(h["checked_on"]) + " 확인" if h.get("checked_on") else ""}
    </p>
  </div>
</article>"""


# ── 페이지 ────────────────────────────────────────────
def build_page(hotels, ag, stamp):
    cards = "\n".join(card(h, ag) for h in hotels)
    n = len(hotels)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>우리 아이가 갈 수 있는 호텔 — 콩이스테이</title>
<meta name="description" content="호텔마다 다른 반려견 체중·체고 기준을 우리 아이 크기로 갈라서 보여드립니다. 추가요금과 보증금까지 한눈에 비교하세요.">
<meta property="og:title" content="우리 아이가 갈 수 있는 호텔">
<meta property="og:description" content="우리 아이 크기를 넣으면 갈 수 있는 곳만 보여드려요.">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
:root{{
  --paper:#F4F2EC; --card:#FFFFFF; --ink:#1C2321; --muted:#6E736F;
  --line:#DFDCD2; --sage:#3D6B5C; --sage-lt:#E8EFEB;
  --warn:#B4472F; --warn-lt:#FBEDE9; --tight:#9A6B1F; --tight-lt:#F7EFDE;
  --track:#C6C2B6;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  background:var(--paper);color:var(--ink);
  font-family:"Pretendard Variable",Pretendard,-apple-system,system-ui,sans-serif;
  font-feature-settings:"tnum" 1;line-height:1.6;
}}
.wrap{{max-width:760px;margin:0 auto;padding:40px 20px 72px}}

.head{{margin-bottom:30px}}
.head h1{{font-size:clamp(26px,5vw,36px);font-weight:800;letter-spacing:-.035em;line-height:1.25}}
.head p{{color:var(--muted);font-size:14.5px;margin-top:10px;max-width:52ch}}

.panel{{
  background:var(--card);border:1px solid var(--line);border-radius:4px;
  padding:22px 22px 18px;margin-bottom:14px;
}}
.dials{{display:flex;gap:28px;flex-wrap:wrap}}
.dial{{flex:1 1 200px;min-width:180px}}
.dial label{{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}}
.dial .v{{font-size:26px;font-weight:800;letter-spacing:-.02em;color:var(--sage)}}
.dial .v small{{font-size:13px;font-weight:600;color:var(--muted);margin-left:2px}}
input[type=range]{{-webkit-appearance:none;appearance:none;width:100%;height:22px;background:transparent;cursor:pointer;margin-top:4px}}
input[type=range]::-webkit-slider-runnable-track{{height:3px;background:var(--line)}}
input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:var(--sage);margin-top:-7.5px;border:3px solid var(--card);box-shadow:0 0 0 1px var(--sage)}}
input[type=range]::-moz-range-track{{height:3px;background:var(--line)}}
input[type=range]::-moz-range-thumb{{width:12px;height:12px;border-radius:50%;background:var(--sage);border:3px solid var(--card);box-shadow:0 0 0 1px var(--sage)}}
input[type=range]:focus-visible{{outline:2px solid var(--ink);outline-offset:4px}}
input[type=range]{{height:34px}}
input[type=range]::-webkit-slider-runnable-track{{height:6px;background:var(--track);border-radius:3px}}
input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;width:26px;height:26px;border-radius:50%;background:var(--sage);margin-top:-10px;border:3px solid var(--card);box-shadow:0 0 0 2px var(--sage)}}
input[type=range]::-moz-range-track{{height:6px;background:var(--track);border-radius:3px}}
input[type=range]::-moz-range-thumb{{width:20px;height:20px;border-radius:50%;background:var(--sage);border:3px solid var(--card);box-shadow:0 0 0 2px var(--sage)}}
.hint{{font-size:12.5px;color:var(--muted);margin-top:12px}}
.gap{{display:block;height:14px}}
.count{{margin-top:16px;padding-top:14px;border-top:1px solid var(--line);font-size:14.5px;font-weight:600}}
.count b{{color:var(--sage);font-size:18px}}

.hotel{{
  background:var(--card);border:1px solid var(--line);border-radius:4px;
  margin-bottom:14px;overflow:hidden;
}}
.hotel.no{{opacity:.55}}
.photo{{width:100%;height:220px;object-fit:cover;object-position:center 35%;display:block;background:var(--line)}}
.photo.ph{{background:linear-gradient(135deg,#E6E3DA,#D8D5CA)}}
.body{{padding:20px 22px 22px}}

.verdict{{font-size:12.5px;font-weight:700;margin-bottom:9px}}
.verdict.ok{{color:var(--sage)}}
.verdict.tight{{color:var(--tight)}}
.verdict.no{{color:var(--warn)}}

.hotel h2{{font-size:20px;font-weight:800;letter-spacing:-.025em}}
.where{{font-size:13px;color:var(--muted);margin-top:3px}}
.limit{{
  display:inline-block;font-size:13px;font-weight:700;margin-top:12px;
  padding:4px 12px;border-radius:3px;background:var(--sage-lt);color:var(--sage);
}}

.facts{{display:grid;grid-template-columns:repeat(2,1fr);gap:9px 24px;margin-top:17px;font-size:13.5px}}
.fact{{display:flex;justify-content:space-between;gap:10px;border-bottom:1px dotted var(--line);padding-bottom:5px}}
.fact span{{color:var(--muted)}}
.fact b{{font-weight:700;text-align:right}}
.fact b.none{{color:var(--muted);font-weight:500}}

.blocked{{font-size:13px;background:var(--warn-lt);color:#8A3423;padding:10px 13px;border-radius:3px;margin-top:15px}}
.extra{{font-size:13px;color:#4A4F4B;margin-top:9px}}
.note{{font-size:13.5px;color:#4A4F4B;margin-top:13px;line-height:1.7}}
.tip{{
  font-size:14px;font-weight:600;color:#2A2E2B;line-height:1.65;
  display:block;
  background:#F7E6A3;
  border-left:4px solid #DFB63F;
  padding:11px 13px;
}}
.tip-wrap{{margin-top:15px}}

.cta{{
  display:inline-block;margin-top:18px;font-size:13.5px;font-weight:700;
  padding:10px 20px;border:1.5px solid var(--ink);border-radius:3px;
  color:var(--ink);text-decoration:none;
}}
.cta:hover{{background:var(--ink);color:var(--card)}}
.cta:focus-visible{{outline:2px solid var(--sage);outline-offset:3px}}
.hotel.no .cta{{border-color:var(--line);color:var(--muted);pointer-events:none}}

.src{{font-size:11.5px;color:var(--muted);margin-top:14px}}
.src a{{color:var(--muted)}}

.foldbtn{{
  display:block;width:100%;margin:6px 0 14px;padding:13px 16px;
  background:transparent;border:1px dashed var(--line);border-radius:4px;
  color:var(--muted);font-family:inherit;font-size:13.5px;font-weight:600;
  cursor:pointer;text-align:center;
}}
.foldbtn:hover{{border-style:solid;color:var(--ink)}}
.foldbtn[hidden]{{display:none}}
.hotel.hide{{display:none}}
.foot{{margin-top:30px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);line-height:1.8}}

@media(prefers-color-scheme:dark){{
  :root{{
    --paper:#16181A; --card:#1F2225; --ink:#E9E7E1; --muted:#9CA29E;
    --line:#343A3C; --track:#4C5356; --sage:#84C0A8; --sage-lt:#23332E;
    --warn:#E79079; --warn-lt:#33221D; --tight:#DDB56C; --tight-lt:#2E2719;
  }}
  .photo{{background:#2A2E30}}
  .photo.ph{{background:linear-gradient(135deg,#2C3033,#23272A)}}
  .blocked{{color:#F0A88F}}
  .extra{{color:#B9BFBB}}
  .note{{color:#C3C9C5}}
  .cta:hover{{background:var(--ink);color:#16181A}}
}}
@media(max-width:520px){{
  .facts{{grid-template-columns:1fr}}
  .photo{{height:150px}}
  .head h1{{font-size:clamp(22px,6.5vw,26px);letter-spacing:-.045em}}
}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>
</head>
<body>
<div class="wrap">

<header class="head">
  <h1>우리 아이가 갈 수 있는 호텔</h1>
  <p>호텔마다 받아주는 강아지 크기가 다릅니다. 우리 아이 몸무게와 키를 넣으면 갈 수 있는 곳과 안 되는 곳을 갈라서 보여드려요.</p>
</header>

<section class="panel">
  <div class="dials">
    <div class="dial">
      <label for="w">몸무게</label>
      <div class="v" id="wv">8<small>kg</small></div>
      <input type="range" id="w" min="1" max="45" step="0.5" value="8" aria-label="반려견 몸무게">
    </div>
    <div class="dial">
      <label for="h">체고 (바닥에서 어깨까지)</label>
      <div class="v" id="hv">32<small>cm</small></div>
      <input type="range" id="h" min="10" max="80" step="1" value="32" aria-label="반려견 체고">
    </div>
  </div>
  <p class="hint">↔ 손잡이를 좌우로 움직여 보세요</p>
  <p class="count" id="count"></p>
</section>

<main id="list">
{cards}
</main>
<button class="foldbtn" id="fold" hidden></button>

<p class="foot">
  반려동물 규정은 호텔이 예고 없이 바꿉니다. 예약 전에 호텔에 다시 확인해 주세요.
  각 호텔마다 확인한 날짜와 출처를 함께 적어두었습니다.<span class="gap"></span>
  이 페이지의 링크로 예약이 이루어지면 운영자가 일정 수수료를 받습니다.
  호텔 사진과 평점은 아고다 제공입니다.<br>
  {stamp} 갱신 · 호텔 {n}곳
</p>

</div>

<script>
const list = document.getElementById("list");
const cards = [...list.querySelectorAll(".hotel")];
const fold = document.getElementById("fold");
let opened = false;

function paint(blocked){{
  blocked.forEach(c => c.classList.toggle("hide", !opened));
  if(blocked.length === 0){{
    fold.hidden = true;
    return;
  }}
  fold.hidden = false;
  fold.textContent = opened
    ? "조건이 안 맞는 곳 접기"
    : `조건이 안 맞는 곳 ${{blocked.length}}군데 보기`;
}}

fold.addEventListener("click", () => {{
  opened = !opened;
  paint(cards.filter(c => c.classList.contains("no")));
}});

function apply(){{
  const w = parseFloat(document.getElementById("w").value);
  const h = parseInt(document.getElementById("h").value, 10);
  let pass = 0;

  cards.forEach(c => {{
    const mw = c.dataset.w === "" ? null : parseFloat(c.dataset.w);
    const mh = c.dataset.h === "" ? null : parseFloat(c.dataset.h);
    const overW = mw !== null && w > mw;
    const overH = mh !== null && h > mh;
    const no = overW || overH;
    const tight = !no && ((mw !== null && w/mw > .85) || (mh !== null && h/mh > .85));

    c.classList.toggle("no", no);
    const v = c.querySelector(".verdict");
    if(no){{
      const why = [];
      if(overW) why.push(`몸무게 ${{mw}}kg 이하만 받아요`);
      if(overH) why.push(`체고 ${{mh}}cm 이하만 받아요`);
      v.className = "verdict no";
      v.textContent = why.join(" · ");
    }} else if(tight){{
      v.className = "verdict tight";
      v.textContent = "아슬아슬하게 통과해요";
      pass++;
    }} else {{
      v.className = "verdict ok";
      v.textContent = "갈 수 있어요";
      pass++;
    }}
  }});

  const ok = cards.filter(c => !c.classList.contains("no"));
  const blocked = cards.filter(c => c.classList.contains("no"));
  [...ok, ...blocked].forEach(c => list.appendChild(c));

  if(ok.length === 0) opened = true;
  paint(blocked);

  document.getElementById("count").innerHTML = pass
    ? `${{w}}kg · ${{h}}cm 라면 <b>${{pass}}곳</b> 갈 수 있어요`
    : `${{w}}kg · ${{h}}cm 를 받아주는 곳이 아직 없어요`;
}}

document.getElementById("w").addEventListener("input", ev => {{
  document.getElementById("wv").innerHTML = ev.target.value + "<small>kg</small>";
  apply();
}});
document.getElementById("h").addEventListener("input", ev => {{
  document.getElementById("hv").innerHTML = ev.target.value + "<small>cm</small>";
  apply();
}});

const q = new URLSearchParams(location.search);
const qw = parseFloat(q.get("w"));
if(qw > 0){{
  const ws = document.getElementById("w");
  ws.value = Math.min(Math.max(qw, 1), 45);
  document.getElementById("wv").innerHTML = ws.value + "<small>kg</small>";
}}

apply();

if(location.hash.length > 1){{
  const t = document.getElementById(location.hash.slice(1));
  if(t){{
    if(t.classList.contains("hide")){{
      opened = true;
      paint(cards.filter(c => c.classList.contains("no")));
    }}
    setTimeout(() => t.scrollIntoView({{behavior: "smooth", block: "start"}}), 80);
  }}
}}
</script>
</body>
</html>
"""


def main():
    with open(os.path.join(HERE, "hotels.json"), encoding="utf-8") as f:
        data = json.load(f)

    hotels = data.get("hotels", [])
    print(f"호텔 {len(hotels)}곳을 읽었습니다.")
    if not hotels:
        print("hotels.json 에 호텔이 없습니다.")
        sys.exit(1)

    hids = [h["agoda_hid"] for h in hotels
            if h.get("agoda_hid") not in (None, "")]
    ag = fetch_agoda(hids)

    stamp = datetime.now(KST).strftime("%Y-%m-%d")
    page = build_page(hotels, ag, stamp)

    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"만들었습니다: index.html ({len(page):,}자)")


if __name__ == "__main__":
    main()
