#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""学生票合规判断 — Web 端（FastAPI + Jinja2 服务端渲染 + JSON API）

支持两种启动方式：
  1) 在项目根目录：  uvicorn src.web_app:app --host 0.0.0.0 --port 8080
  2) 在 src/ 目录下：  uvicorn web_app:app --host 0.0.0.0 --port 8080
"""
from fastapi import FastAPI, Request, Form, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os, sys, subprocess, urllib.request, urllib.error

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ---- 路径适配：支持 flat 结构（旧）和 handover 分层结构（新） ----
_PROJ_ROOT = os.path.dirname(_HERE)  # 项目根目录尝试

# 1) student_rules.json：先在 src/ 同级找，再往上一层 data/ 找
_rules_candidates = [
    os.path.join(_HERE, "student_rules.json"),                   # flat: src/
    os.path.join(_PROJ_ROOT, "data", "student_rules.json"),      # handover: data/
    os.path.join(_PROJ_ROOT, "student_rules.json"),              # flat: 根目录
]
_RULES_PATH = None
for _p in _rules_candidates:
    if os.path.isfile(_p):
        _RULES_PATH = _p
        break
if _RULES_PATH is None:
    raise FileNotFoundError(f"找不到 student_rules.json，已搜索：{_rules_candidates}")

# 2) web 资源目录
_web_dir = os.path.join(_PROJ_ROOT, "web")
if not os.path.isdir(_web_dir):
    _web_dir = _HERE  # fallback to flat

_templates_dir = os.path.join(_web_dir, "templates")
if not os.path.isdir(_templates_dir):
    _templates_dir = os.path.join(_HERE, "templates")  # flat fallback

_static_dir = os.path.join(_web_dir, "static")
if not os.path.isdir(_static_dir):
    _static_dir = os.path.join(_HERE, "static")  # flat fallback

from student_ticket_checker import check_student_ticket, check_compliance, suggest, find_multiple_paths_between_cities, check_route_segments, ALLOWED_SEATS
import railway_data as R

app = FastAPI(title="学生票合规判断")

if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")
templates = Jinja2Templates(directory=_templates_dir)

with open(_RULES_PATH, encoding="utf-8") as f:
    rules = json.load(f)["student_ticket"]
    cases = rules["case_library"]

# ---- 用户上传案例存储（data/user_cases.json） ----
_USER_CASES_PATH = os.path.join(_PROJ_ROOT, "data", "user_cases.json")

def _load_user_cases():
    """读取用户上传的案例列表（文件不存在返回空列表）"""
    try:
        if os.path.isfile(_USER_CASES_PATH):
            with open(_USER_CASES_PATH, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def _save_user_case(case):
    """追加一个用户案例到 data/user_cases.json"""
    lst = _load_user_cases()
    lst.append(case)
    os.makedirs(os.path.dirname(_USER_CASES_PATH), exist_ok=True)
    with open(_USER_CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(lst, f, ensure_ascii=False, indent=2)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "allowed_seats": ALLOWED_SEATS,
    })

@app.api_route("/check", methods=["GET", "POST"], response_class=HTMLResponse)
async def check(request: Request):
    if request.method == "POST":
        form_data = await request.form()
        school = form_data.get("school", "")
        home = form_data.get("home", "")
        dep = form_data.get("dep", "")
        arr = form_data.get("arr", "")
        waypoints = form_data.getlist("waypoints")
        seat = form_data.get("seat", "")
        fresh_grad = form_data.get("fresh_grad") == "true"
        new_home = form_data.get("new_home", "").strip()
    else:  # GET：支持带参数预填充 / 直接可查验的链接
        q = request.query_params
        school = q.get("school", "")
        home = q.get("home", "")
        dep = q.get("dep", "")
        arr = q.get("arr", "")
        waypoints = [w.strip() for w in q.get("waypoints", "").split(",") if w.strip()]
        seat = q.get("seat", "")
        fresh_grad = q.get("fresh_grad") == "true"
        new_home = q.get("new_home", "").strip()

    waypoints = [w for w in waypoints if w.strip()]
    all_stations = [dep] + waypoints + [arr]
    inp = {"school": school, "home": home, "dep": dep, "arr": arr,
           "waypoints": waypoints,
           "seat": seat.strip() or None, "fresh_grad": fresh_grad,
           "new_home": new_home or None}

    # 有途经站 → 调用 route segments
    nonempty = [s for s in all_stations if s.strip()]
    if len(nonempty) > 2:
        report = check_route_segments(school, home, nonempty,
                                       seat if seat.strip() else None, fresh_grad)
        return templates.TemplateResponse(request, "index.html", {
            "allowed_seats": ALLOWED_SEATS,
            "route_report": report,
            "input": inp,
        })

    # 无途经站 → 原有逻辑
    paths = find_multiple_paths_between_cities(school, new_home or home, K=5)
    report = check_student_ticket(school, home, dep, arr,
                                   seat if seat.strip() else None, fresh_grad)
    if new_home:
        r2 = check_compliance(school, home, dep, arr, seat if seat.strip() else None, fresh_grad,
                              new_home_city=new_home)
        tips2 = suggest(school, new_home or home, dep, arr, seat if seat.strip() else None, r2)
        report["suggestions"] = report.get("suggestions", []) + ["--- 改家后新区间判断 ---"] + tips2
        report["result"]["using_new_home"] = True
    return templates.TemplateResponse(request, "index.html", {
        "allowed_seats": ALLOWED_SEATS,
        "report": report,
        "input": inp,
        "paths": paths,
    })

@app.post("/api/check")
async def api_check(school: str = Form(...), home: str = Form(...),
                    dep: str = Form(...), arr: str = Form(...),
                    seat: str = Form(""), fresh_grad: bool = Form(False),
                    new_home: str = Form("")):
    report = check_student_ticket(school, home, dep, arr,
                                   seat if seat.strip() else None, fresh_grad)
    if new_home.strip():
        r2 = check_compliance(school, home, dep, arr, seat if seat.strip() else None, fresh_grad,
                              new_home_city=new_home.strip())
        report["new_home_result"] = r2
    return JSONResponse(report)

@app.get("/api/stations")
async def api_stations():
    return JSONResponse({
        "stations": sorted(R.STATION_INFO.keys()),
        "count": len(R.STATION_INFO),
        "cities": sorted(R.CITY_TO_STATIONS.keys()),
        "city_count": len(R.CITY_TO_STATIONS),
        "station_cities": {s: R.STATION_INFO[s].get("city","") for s in R.STATION_INFO},
    })

@app.get("/cases", response_class=HTMLResponse)
async def case_list(request: Request):
    all_cases = cases + _load_user_cases()
    return templates.TemplateResponse(request, "cases.html", {
        "cases": all_cases,
        "builtin_count": len(cases),
    })

@app.post("/api/user_case")
def user_case(body: dict = Body(default={})):
    """保存用户分享的真实购票案例（纯文本，不接车站/城市数据库）"""
    school = (body.get("school") or "").strip()
    home = (body.get("home") or "").strip()
    dep = (body.get("dep") or "").strip()
    arr = (body.get("arr") or "").strip()
    description = (body.get("description") or "").strip()
    if not (school and home and dep and arr):
        return JSONResponse({"error": "请完整填写学校、家庭、出发、到达四个城市"})
    if not description:
        return JSONResponse({"error": "请填写您的经历描述"})
    if len(description) > 200:
        return JSONResponse({"error": "描述不能超过 200 字"})
    case = {
        "title": f"用户分享：{school} ↔ {home}，购票 {dep} → {arr}",
        "scenario": f"学校所在地 {school}，家庭所在地 {home}，购票区间 {dep} → {arr}",
        "judgment": "用户分享案例（内容由用户自行描述，尚未经系统自动判定）",
        "user_description": description,
        "user_submitted": True,
    }
    _save_user_case(case)
    return JSONResponse({"ok": True, "message": "案例已收录，感谢您的分享！"})

# =====================================================================
# AI 辅助判定 — 多平台转发接口
# 前端仅将 API Key 保存在内存（刷新即清除），本接口只做透传，不落盘。
# =====================================================================
_AI_ENDPOINTS = {
    "doubao":   "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "glm":      "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    "chatgpt":  "https://api.openai.com/v1/chat/completions",
    "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "hunyuan":  "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
    "wenxin":   "https://qianfan.baidubce.com/v2/chat/completions",
}
_AI_MODELS = {
    "doubao":   "doubao-pro-32k",
    "deepseek": "deepseek-chat",
    "glm":      "glm-4-flash",
    "chatgpt":  "gpt-4o-mini",
    "gemini":   "gemini-1.5-flash",
    "hunyuan":  "hunyuan-lite",
    "wenxin":   "ernie-4.0-turbo-8k",
}

@app.post("/api/ai_check")
def ai_check(body: dict = Body(default={})):
    # 注意：这里用同步 def（非 async）——内部 urllib 阻塞调用会在线程池中执行，
    # 避免卡住 uvicorn 事件循环（async def + 同步阻塞 IO 会导致整站无响应）。
    platform = (body.get("platform") or "").strip().lower()
    api_key = (body.get("api_key") or "").strip()
    prompt = (body.get("prompt") or "").strip()
    web_search = bool(body.get("web_search"))
    if platform not in _AI_ENDPOINTS:
        return JSONResponse({"error": f"不支持的 AI 服务商：{platform}"})
    if not api_key:
        return JSONResponse({"error": "缺少 API Key"})
    if not prompt:
        return JSONResponse({"error": "缺少分析内容"})

    system_msg = ("你是一位中国铁路客运规则专家，回答须基于《铁路旅客运输规程》第十六条"
                  "与学生票优惠区间规则，做到准确、简明。")
    if web_search:
        system_msg += "（用户已开启联网搜索意图，若平台支持工具调用可自行联网核实最新政策。）"

    payload = {
        "model": _AI_MODELS[platform],
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    req = urllib.request.Request(
        _AI_ENDPOINTS[platform],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        return JSONResponse({"error": f"上游服务返回 {e.code}: {detail}"})
    except Exception as e:
        return JSONResponse({"error": f"请求上游失败：{e}"})

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        return JSONResponse({"error": "上游返回格式异常，无法解析 AI 回复"})
    return JSONResponse({"content": content})

# =====================================================================
# 12306 列车信息查询 — 接入 12306 官方公开 API（车次/时刻/余票/公布票价）
# 让 AI 深度查询基于真实列车数据回答，而非仅依赖规则条文。
# =====================================================================
_TRAIN_QUERY_SCRIPT = os.path.join(
    os.path.expanduser("~"),
    ".workbuddy", "project-resources",
    "p_9e590f9aea7c425aae5599b35f842df3",
    "skill_2053079107781726208", "scripts", "query.mjs",
)
_STATIONS_SCRIPT = os.path.join(
    os.path.expanduser("~"),
    ".workbuddy", "project-resources",
    "p_9e590f9aea7c425aae5599b35f842df3",
    "skill_2053079107781726208", "scripts", "stations.mjs",
)
_STATIONS_CACHE = {}  # 站名 → station_code

def _run_train_query(from_name, to_name, date=None):
    """调用 12306 skill 的 query.mjs，返回真实列车列表（车次/时刻/余票）"""
    if not os.path.isfile(_TRAIN_QUERY_SCRIPT):
        return {"error": "12306 查询脚本不可用"}
    cmd = ["node", _TRAIN_QUERY_SCRIPT, from_name, to_name, "--json"]
    if date:
        cmd += ["--date", date]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return {"error": f"12306 查询执行失败：{e}"}
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout or "查询失败").strip()[:300]}
    try:
        trains = json.loads(proc.stdout)
    except Exception:
        return {"error": "12306 返回解析失败"}
    return {"trains": trains}

def _station_code(name):
    """通过 stations.mjs 将站名/城市名解析为 12306 车站代码（带缓存）"""
    if not name:
        return ""
    if name in _STATIONS_CACHE:
        return _STATIONS_CACHE[name]
    if not os.path.isfile(_STATIONS_SCRIPT):
        return ""
    try:
        proc = subprocess.run(
            ["node", _STATIONS_SCRIPT, name], capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = (proc.stdout or "").strip().splitlines()
        if out:
            info = json.loads(out[0])
            _STATIONS_CACHE[name] = info.get("station_code", "")
            return _STATIONS_CACHE[name]
    except Exception:
        pass
    return ""

def _fetch_train_price(date, train_no, from_name, to_name):
    """查询指定车次/区间的公布票价（12306 官方票价接口）
    from_name/to_name 为站名，内部解析为车站代码"""
    from_code = _station_code(from_name)
    to_code = _station_code(to_name)
    if not (from_code and to_code):
        return {}
    base = "https://kyfw.12306.cn/otn/leftTicketPrice/query"
    params = (
        f"leftTicketDTO.train_date={date}"
        f"&leftTicketDTO.train_no={train_no}"
        f"&leftTicketDTO.from_station={from_code}"
        f"&leftTicketDTO.to_station={to_code}"
        f"&leftTicketDTO.seat_types=A1&leftTicketDTO.ticket_type=1"
    )
    req = urllib.request.Request(
        base + "?" + params,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://kyfw.12306.cn/otn/leftTicketPrice/init",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}
    if not data.get("status") or not data.get("data"):
        return {}
    dto = data["data"][0].get("queryLeftNewDTO", {})
    prices = {}
    for key in ("swz_price", "tz_price", "zy_price", "ze_price", "gr_price",
                "rw_price", "yw_price", "rz_price", "yz_price", "wz_price"):
        if dto.get(key) and str(dto[key]) != "-1":
            prices[key] = dto[key]
    return prices

@app.post("/api/train_info")
def train_info(body: dict = Body(default={})):
    """查询真实列车信息：车次/时刻/余票 + 公布票价。
    入参：{from, to, date?}   from/to 可为城市或车站名
    """
    from_name = (body.get("from") or "").strip()
    to_name = (body.get("to") or "").strip()
    date = (body.get("date") or "").strip() or None
    if not from_name or not to_name:
        return JSONResponse({"error": "缺少出发/到达站"})

    result = _run_train_query(from_name, to_name, date)
    if "error" in result:
        return JSONResponse({"error": result["error"]})

    trains = result["trains"]
    # 若未指定日期则取当天（query.mjs 默认），票价按同一日期查询
    travel_date = date or _today_str()
    enriched = []
    for t in trains[:12]:  # 最多取前 12 趟避免请求过慢
        prices = _fetch_train_price(travel_date, t["trainNo"], t.get("fromStation", ""), t.get("toStation", ""))
        enriched.append({**t, "prices": prices})
    return JSONResponse({"trains": enriched, "date": travel_date, "count": len(enriched)})

# ---- 常见中转枢纽候选（城市名，query.mjs 会解析到主站） ----
_HUB_CITIES = [
    "北京", "上海", "广州", "武汉", "西安", "郑州", "长沙", "南京", "杭州",
    "成都", "重庆", "沈阳", "济南", "南昌", "合肥", "福州", "昆明", "贵阳",
    "兰州", "太原", "石家庄", "天津", "南宁", "乌鲁木齐", "西宁", "呼和浩特",
]

def _parse_hhmm(s):
    """'HH:MM' → 分钟数（当日）；异常值（24:00 等）返回 None"""
    try:
        h, m = s.split(":")
        h = int(h)
        if h >= 24:
            return None
        return h * 60 + int(m)
    except Exception:
        return None

def _dur_minutes(raw):
    """'HH:MM' 历时 → 分钟数"""
    try:
        h, m = raw.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 0

def _build_transfer_plan(from_trains, hub_name, to_trains, travel_date):
    """在给定枢纽 hub 下，从 from_trains 与 to_trains 中挑选时间可衔接的组合。
    换乘缓冲默认 40 分钟；支持次日换乘（arrive 时间早于出发时视为次日）。
    按「总行程时间最短」原则：总耗时 = 第一段历时 + 换乘等待 + 第二段历时。
    返回组合列表 [{hub, first, second, wait_min, same_day, total_min}]
    """
    plans = []
    for ft in from_trains:
        arr = _parse_hhmm(ft.get("arriveTime"))
        if arr is None:
            continue
        for tt in to_trains:
            dep = _parse_hhmm(tt.get("departTime"))
            if dep is None:
                continue
            # 同日换乘 or 次日换乘
            wait = dep - arr
            same_day = True
            if wait < 0:
                wait += 24 * 60
                same_day = False
            if wait < 40:  # 换乘缓冲不足
                continue
            if wait > 24 * 60 - 60:  # 等待过长（>23h）不推荐
                continue
            total_min = _dur_minutes(ft.get("duration")) + wait + _dur_minutes(tt.get("duration"))
            plans.append({
                "hub": hub_name,
                "date": travel_date,
                "first": ft,
                "second": tt,
                "wait_min": wait,
                "same_day": same_day,
                "total_min": total_min,
            })
    return plans

def _audit_transfer_compliance(plan, school_city, home_city):
    """用本地学生票区间引擎审核中转方案的每段区间合规性。
    返回 {segments: [{dep, arr, ok, ticket_type, reason}], overall_ok, has_student, has_adult}
    """
    try:
        from student_ticket_checker import check_route_segments
    except Exception:
        return None
    stations = [plan["first"].get("fromStation", ""),
                plan["second"].get("fromStation", ""),  # 换乘站（第一段到达 = 第二段出发）
                plan["second"].get("toStation", "")]
    # 若换乘站字段不完整，用枢纽名兜底
    if not stations[0] or not stations[1]:
        stations = [plan["first"].get("fromStation", ""), plan["hub"],
                    plan["second"].get("toStation", "")]
    res = check_route_segments(school_city, home_city, stations)
    if not res or "segments" not in res:
        return None
    segs = []
    for s in res["segments"]:
        segs.append({
            "dep": s.get("dep", ""),
            "arr": s.get("arr", ""),
            "ok": bool(s.get("ok")),
            "ticket_type": s.get("ticket_type", "学生票" if s.get("ok") else "成人票"),
            "reason": s.get("reason", ""),
        })
    return {
        "segments": segs,
        "overall_ok": bool(res.get("has_adult_segments") is False),
        "has_student": bool(res.get("has_student_segments")),
        "has_adult": bool(res.get("has_adult_segments")),
    }

# ---- 学生票票价折算（12306 官方规则） ----
# 硬座/硬卧：公布价 5 折（硬卧 = 硬卧公布价 - 硬座公布价×0.5）
# 二等座/一等座等：公布价 7.5 折；软座/软卧按公布价（通常不设学生票）
_STUDENT_DISCOUNT = {
    "yz": 0.5,   # 硬座 5 折
    "yw": 0.5,   # 硬卧按「全价-硬座半价」计算
    "ze": 0.75,  # 二等座 7.5 折
    "zy": 0.75,  # 一等座 7.5 折
    "rz": 0.75,  # 软座按公布价（无学生价，7.5 折为参考）
    "rw": 1.0,   # 软卧公布价
    "gr": 1.0,   # 高级软卧公布价
    "dw": 1.0,   # 动卧公布价
    "wz": 1.0,   # 无座按硬座半价
}

def _price_yuan(raw):
    """12306 票价（分单位字符串）→ 元；无效返回 None"""
    try:
        v = int(str(raw).strip())
        if v <= 0:
            return None
        return v / 10.0
    except Exception:
        return None

def _seat_price_for(plan, seat_key):
    """取单趟列车指定席别公布票价（元）；无该席别返回 None"""
    prices = plan.get("prices") or {}
    raw = prices.get(seat_key + "_price")
    return _price_yuan(raw)

def _leg_student_price(leg, is_student):
    """计算单段行程的票价（学生票/成人票）。
    优先取：硬座→硬卧→二等座→一等座；该段合规且为学生票时按折扣价，否则公布价。
    返回 {price, seat_label, is_student}
    """
    # 席别优先级：硬座最便宜，其次硬卧、二等座
    for seat in ("yz", "yw", "ze", "zy"):
        raw_price = _seat_price_for(leg, seat)
        if raw_price is None:
            continue
        if seat == "yz" and is_student:
            price = raw_price * 0.5
            return {"price": round(price, 1), "seat_label": "硬座", "is_student": True}
        if seat == "yw" and is_student:
            # 硬卧学生票 = 硬卧公布价 - 硬座公布价 × 0.5
            yz = _seat_price_for(leg, "yz") or 0
            price = raw_price - yz * 0.5
            return {"price": round(price, 1), "seat_label": "硬卧", "is_student": True}
        if seat == "ze" and is_student:
            price = raw_price * 0.75
            return {"price": round(price, 1), "seat_label": "二等座", "is_student": True}
        if seat == "zy" and is_student:
            price = raw_price * 0.75
            return {"price": round(price, 1), "seat_label": "一等座", "is_student": True}
        # 成人票：取该段最便宜席别
        return {"price": raw_price, "seat_label": _SEAT_LABEL[seat], "is_student": False}
    return None

_SEAT_LABEL = {"yz": "硬座", "yw": "硬卧", "ze": "二等座", "zy": "一等座",
               "rz": "软座", "rw": "软卧", "dw": "动卧", "gr": "高级软卧", "wz": "无座"}

def _compute_plan_price(plan, audit):
    """计算中转方案总票价（两段合计，按合规审核标注学生/成人）。
    返回 {total, legs: [{dep, arr, price, seat_label, is_student}], has_price}
    """
    legs = []
    for idx, leg in enumerate((plan["first"], plan["second"])):
        # 该段是否可用学生票：audit 中对应段 ok
        is_student = False
        if audit and audit.get("segments") and idx < len(audit["segments"]):
            is_student = bool(audit["segments"][idx].get("ok"))
        info = _leg_student_price(leg, is_student)
        if info is None:
            return {"total": None, "legs": [], "has_price": False}
        legs.append({
            "dep": leg.get("fromStation", ""),
            "arr": leg.get("toStation", ""),
            "price": info["price"],
            "seat_label": info["seat_label"],
            "is_student": info["is_student"],
        })
    total = round(sum(l["price"] for l in legs), 1)
    return {"total": total, "legs": legs, "has_price": True}

@app.post("/api/direct_route")
def direct_route(body: dict = Body(default={})):
    """判断 from↔to 是否有直达列车；无直达时给出中转建议。
    三层逻辑：
      1) 直达 → 直接返回
      2) 无直达 → 12306 查枢纽中转 → 本地引擎审核每段合规性（不合规过滤/部分合规标注）
      3) 12306 方案全部不合规 → 本地引擎先生成合规路径 → 12306 查车次兜底
    入参：{from, to, date?, hubs?, school?, home?}
    返回：{direct, transfers, date, has_direct, source}
    """
    from_name = (body.get("from") or "").strip()
    to_name = (body.get("to") or "").strip()
    date = (body.get("date") or "").strip() or None
    school_city = (body.get("school") or from_name or "").strip()
    home_city = (body.get("home") or to_name or "").strip()
    if not from_name or not to_name:
        return JSONResponse({"error": "缺少出发/到达站"})
    travel_date = date or _today_str()

    # 1) 直达查询
    direct_res = _run_train_query(from_name, to_name, travel_date)
    if "error" in direct_res:
        return JSONResponse({"error": direct_res["error"]})
    direct_trains = direct_res["trains"]

    # 2) 若有直达则直接返回（无需中转）
    if direct_trains:
        return JSONResponse({
            "direct": direct_trains,
            "transfers": [],
            "date": travel_date,
            "has_direct": True,
            "source": "direct",
        })

    # 3) 无直达 → 中转方案。优先用本地引擎路径上的枢纽（精准候选，查询快且合规率高）
    all_plans = []
    hub_list = body.get("hubs") or _HUB_CITIES
    hub_list = [h for h in hub_list if h != from_name and h != to_name]

    # 3.0) 本地引擎路径上的枢纽（优先候选）
    priority_hubs = _path_hub_candidates(school_city, home_city, hub_list)

    def _query_hub(hub):
        """查询单枢纽的两段车次并生成可衔接组合"""
        first_res = _run_train_query(from_name, hub, travel_date)
        if "error" in first_res or not first_res["trains"]:
            return []
        second_res = _run_train_query(hub, to_name, travel_date)
        if "error" in second_res or not second_res["trains"]:
            return []
        return _build_transfer_plan(first_res["trains"], hub, second_res["trains"], travel_date)

    def _query_hubs_parallel(hubs, max_workers, collect_target):
        out = []
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = [ex.submit(_query_hub, hub) for hub in hubs]
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        out.extend(fut.result())
                    except Exception:
                        pass
                    if len(out) >= collect_target:
                        for f2 in futures:
                            f2.cancel()
                        break
        except Exception:
            for hub in hubs:
                out.extend(_query_hub(hub))
                if len(out) >= collect_target:
                    break
        return out

    # 先用本地路径枢纽查询（通常 4~12 个，快且准；多收集以便覆盖价格最优候选）
    if priority_hubs:
        all_plans = _query_hubs_parallel(priority_hubs[:12], 6, 8)
    # 本地枢纽方案不足时，再补查默认枢纽列表
    if len(all_plans) < 4:
        remain = [h for h in hub_list if h not in priority_hubs]
        all_plans.extend(_query_hubs_parallel(remain[:10], 8, 10 - len(all_plans)))

    # 3.1) 按总行程时间排序（路径最短原则），同日换乘优先
    all_plans.sort(key=lambda p: (p["same_day"] is False, p["total_min"]))
    candidates = all_plans[:8]

    # 3.2) 本地引擎审核每段合规性 + 计算票价
    audited = []
    for p in candidates:
        audit = _audit_transfer_compliance(p, school_city, home_city)
        if audit is None:
            # 引擎不可用 → 保留但不标注
            audited.append({**p, "audit": None})
            continue
        p["audit"] = audit
        # 全程均不合规 → 不予输出（过滤）
        if audit["has_adult"] and not audit["has_student"]:
            continue
        # 查询两段公布票价并计算总票价（含学生票折算）
        for leg in (p["first"], p["second"]):
            leg["prices"] = _fetch_train_price(
                travel_date, leg.get("trainNo", ""),
                leg.get("fromStation", ""), leg.get("toStation", ""))
        p["price_info"] = _compute_plan_price(p, audit)
        audited.append(p)

    if audited:
        # 3.3) 三类推荐标准选择：路径最短 / 时间最短 / 价格最优
        recommendations = _select_recommendations(audited)
        return JSONResponse({
            "direct": [],
            "transfers": audited[:8],
            "date": travel_date,
            "has_direct": False,
            "source": "12306",
            "recommendations": recommendations,
        })

    # 4) 本地化兜底：12306 方案全部不合规 → 本地引擎先生成合规路径 → 查 12306 车次
    fallback = _local_fallback_transfers(from_name, to_name, school_city, home_city, travel_date)
    fallback_recs = _select_recommendations(fallback)
    return JSONResponse({
        "direct": [],
        "transfers": fallback,
        "date": travel_date,
        "has_direct": False,
        "source": "local_fallback",
        "recommendations": fallback_recs,
    })

def _select_recommendations(plans):
    """从审核通过的方案中按三类标准各选最优：
      - 时间最短：总行程时间 total_min 最小（同日换乘优先）
      - 价格最优：总票价 total 最小（学生票折算后）
      - 路径最短：本地路径枢纽优先（若方案带 local_path 或审计路径更贴近本地路径）
    返回 [{idx, label, reason, plan}]，label ∈ {时间最短, 价格最优, 路径最短}
    """
    if not plans:
        return []
    recs = []
    seen_label = set()

    def _add(label, plan, reason):
        if label in seen_label:
            return
        seen_label.add(label)
        recs.append({
            "label": label,
            "reason": reason,
            "hub": plan.get("hub", ""),
            "total_min": plan.get("total_min"),
            "price": (plan.get("price_info") or {}).get("total"),
            "same_day": plan.get("same_day", True),
        })

    # 时间最短
    best_time = min(plans, key=lambda p: (p.get("same_day") is False, p.get("total_min", 10**9)))
    _add("时间最短", best_time,
         f"总行程约 {round(best_time.get('total_min', 0) / 60)} 小时"
         + ("（当日换乘）" if best_time.get("same_day") else "（次日换乘）"))

    # 价格最优：仅取有票价且合规的方案
    priced = [p for p in plans if (p.get("price_info") or {}).get("has_price")]
    if priced:
        best_price = min(priced, key=lambda p: p["price_info"]["total"])
        _add("价格最优", best_price,
             f"两段合计约 ¥{best_price['price_info']['total']}"
             + ("（全程学生票）" if best_price.get("audit") and best_price["audit"]["overall_ok"]
                else "（含成人票区间）"))
    else:
        _add("价格最优", best_time, "票价信息暂不可用，参考时间最短方案")

    # 路径最短：优先本地路径上的枢纽（local_path 中出现的枢纽）
    path_plans = [p for p in plans if p.get("local_path")]
    if path_plans:
        def _path_rank(p):
            try:
                lp = p.get("local_path", [])
                return min((abs(lp.index(p["hub"])) for _ in [0] if p["hub"] in lp), default=len(lp))
            except Exception:
                return 10**9
        best_path = min(path_plans, key=_path_rank)
        _add("路径最短", best_path, f"沿学校↔家庭最优路径经「{best_path.get('hub')}」中转")
    else:
        # 无本地路径信息 → 用总耗时最短近似（路径短通常时间短）
        _add("路径最短", best_time, "沿本地铁路网络最短路径中转")

    return recs

def _path_hub_candidates(school_city, home_city, hub_list):
    """用本地引擎生成 school↔home 路径，提取路径上的枢纽候选（供 12306 中转查询）。
    返回候选列表（去重，query.mjs 可解析城市或精确站名）：
      1. 枢纽城市（_HUB_CITIES 命中）— 全保留
      2. 路径中后段（30%~90%）且在多条路径中出现的「关键站」— 如广通北站
    起点附近的中小站（荆州/恩施等）不参与，避免浪费查询配额。
    """
    try:
        from student_ticket_checker import find_multiple_paths_between_cities
    except Exception:
        return []
    paths = find_multiple_paths_between_cities(school_city, home_city, K=3)
    if not paths:
        return []
    from collections import Counter
    freq = Counter(s for p in paths for s in p)

    hubs = []       # 枢纽城市
    key_stations = []  # 关键中转站（中后段 + 高频）
    seen_hub = set()
    seen_st = set()

    for path in paths:
        n = len(path)
        for idx, st in enumerate(path):
            if st in seen_hub or st in seen_st:
                continue
            matched = None
            for h in hub_list:
                if st == h or st.startswith(h) or h in st:
                    matched = h
                    break
            else:
                if st.endswith(("东", "南", "西", "北")) and st[:-1] in hub_list:
                    matched = st[:-1]
            if matched:
                if matched not in seen_hub:
                    seen_hub.add(matched)
                    hubs.append(matched)
                seen_hub.add(st)
                continue
            # 关键站：中后段(30%~95%) + 站名 ≤6 字 + 多条路径出现 或 路径中段高频
            ratio = idx / n if n else 0
            if 0.3 <= ratio <= 0.95 and st.endswith("站") and len(st) <= 6 and (freq[st] >= 2 or (ratio >= 0.7 and freq[st] >= 1)):
                seen_st.add(st)
                key_stations.append((ratio, st))
    # 关键站排序：优先路径后半段（≥0.7，接近终点的跨线枢纽如广通北），
    # 再按频率降序、位置升序
    key_stations.sort(key=lambda x: (0 if x[0] >= 0.7 else 1, -freq[x[1]], x[0]))
    return hubs + [s for _, s in key_stations[:6]]

def _local_fallback_transfers(from_name, to_name, school_city, home_city, travel_date):
    """本地兜底：本地引擎生成合规路径 → 提取路径上的枢纽站作中转候选 → 查 12306 车次。
    返回中转方案列表（含 source=local 与合规标注）。
    """
    try:
        from student_ticket_checker import find_multiple_paths_between_cities, check_route_segments
    except Exception:
        return []
    # 本地引擎生成多条合规路径（前 3 条）
    paths = find_multiple_paths_between_cities(school_city, home_city, K=3)
    if not paths:
        return []

    # 从路径中提取「枢纽站」（与 _HUB_CITIES 关联的城市键/别名匹配），保证有跨线车次
    hub_candidates = []
    seen = set()
    for path in paths:
        if len(path) < 3:
            continue
        for station in path:
            if station in seen:
                continue
            # 判断该站是否属于某个枢纽城市（精确匹配或前缀匹配）
            is_hub = False
            for h in _HUB_CITIES:
                if station == h or station.startswith(h) or h in station:
                    is_hub = True
                    break
            # 也允许常见的「X东/X南/X西/X北」枢纽站名直接匹配
            if not is_hub and station.endswith(("东", "南", "西", "北")):
                base = station[:-1]
                if base in _HUB_CITIES:
                    is_hub = True
            if is_hub:
                hub_candidates.append(station)
                seen.add(station)

    if not hub_candidates:
        # 无枢纽站 → 退回取各路径中段站
        for path in paths:
            if len(path) >= 3:
                hub_candidates.append(path[len(path) // 2])
                seen.add(path[len(path) // 2])

    plans = []
    def _query_hub(hub):
        first_res = _run_train_query(from_name, hub, travel_date)
        if "error" in first_res or not first_res["trains"]:
            return []
        second_res = _run_train_query(hub, to_name, travel_date)
        if "error" in second_res or not second_res["trains"]:
            return []
        subs = _build_transfer_plan(first_res["trains"], hub, second_res["trains"], travel_date)
        out = []
        for p in subs:
            audit = _audit_transfer_compliance(p, school_city, home_city)
            if audit and audit["has_adult"] and not audit["has_student"]:
                continue  # 兜底也过滤全程不合规
            p["audit"] = audit
            p["source"] = "local"
            p["local_path"] = paths[0] if paths else []
            # 计算两段票价（含学生票折算）
            for leg in (p["first"], p["second"]):
                leg["prices"] = _fetch_train_price(
                    travel_date, leg.get("trainNo", ""),
                    leg.get("fromStation", ""), leg.get("toStation", ""))
            p["price_info"] = _compute_plan_price(p, audit)
            out.append(p)
        return out

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(_query_hub, hub) for hub in hub_candidates[:4]]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    plans.extend(fut.result())
                except Exception:
                    pass
                if len(plans) >= 3:
                    for f2 in futures:
                        f2.cancel()
                    break
    except Exception:
        for hub in hub_candidates[:3]:
            plans.extend(_query_hub(hub))
            if len(plans) >= 3:
                break
    plans.sort(key=lambda p: (p["same_day"] is False, p["total_min"]))
    return plans[:3]

def _today_str():
    import datetime
    return datetime.date.today().strftime("%Y-%m-%d")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
