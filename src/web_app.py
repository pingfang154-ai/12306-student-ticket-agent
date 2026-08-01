#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""学生票合规判断 — Web 端（FastAPI + Jinja2 服务端渲染 + JSON API）

支持两种启动方式：
  1) 在项目根目录：  uvicorn src.web_app:app --host 0.0.0.0 --port 8080
  2) 在 src/ 目录下：  uvicorn web_app:app --host 0.0.0.0 --port 8080
"""
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os, sys

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
    return templates.TemplateResponse(request, "cases.html", {
        "cases": cases,
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
