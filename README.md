# 12306 学生票合规判定 Agent — 第三版（第一、二版合并）

一个判断「学生票购票区间」是否落在「学校 ↔ 家庭」优惠区间合理径路上的合规引擎，
并给出反向购票识别、改家庭所在地、联程分段等建议。

本目录是 **第一版 + 第二版的合并完整版**：

- 数据层与合规引擎采用**第二版（v2.2，更新、更全、含山东/青海/冀黑湘苏津增量合并、修复跨廊道路径搜索）**；
- 规则层 `student_rules.json` 从**第一版**补回（第二版原始交付中缺失该文件，导致引擎无法导入）；
- Web 演示前端（`web_app.py` + `web/`）、构建/启动脚本、补充文档从**第一版**并入。

---

## 目录结构

```
交接文件夹第三版（含一、二合并）/
├── README.md                      # 本文件
├── README_第一版.md               # 第一版原始说明
├── README_新对话交接.md           # 第二版对话级交接说明
├── PROJECT_SUMMARY.md             # 项目总览与开发日志（第二版）
├── requirements.txt               # Web / 构建依赖
├── start.sh                       # 启动脚本（第一版）
├── src/
│   ├── railway_data.py            # 数据层（权威拓扑源，v2.2）
│   ├── student_ticket_checker.py  # 合规引擎（区间判断 / 反向 / 建议 / 廊道探测）
│   ├── test_cases.py              # 27 条回归用例
│   └── web_app.py                 # FastAPI + Jinja2 Web 演示（第一版）
├── data/
│   ├── lines_order.json           # 线路 → 有序车站列表
│   ├── graph_adjacency.json       # 邻接表
│   ├── station_info.json          # 车站 → 城市/省份 等信息
│   ├── city_to_stations.json      # 城市 → 车站列表
│   ├── hub_stations.json          # 枢纽站
│   ├── student_rules.json         # 规则层（席别白名单/每年4次/新生毕业生/案例库）★本次补回
│   ├── city_aliases.json          # 城市别名（辅助，引擎当前不读取）
│   ├── station_aliases.json       # 车站别名（辅助，引擎当前不读取）
│   └── railway_data.json          # 数据层备份（辅助）
├── web/
│   ├── templates/index.html       # 单区间判断页面
│   ├── templates/cases.html       # 案例库页面
│   └── static/style.css
├── skill/
│   └── railway-data-province-merge/SKILL.md   # 分省数据增量合并 SOP
├── context/
│   └── project_context_summary.md            # 项目背景摘要
├── docs/
│   ├── railway_map_visual_audit_2025.md       # 全国铁路图宏观审计
│   ├── student_rules_analysis.md              # 规则抽取分析（第一版）
│   ├── deployment_guide.md                    # 部署指南（第一版）
│   ├── data_quality_report.md                 # 数据质量报告（第一版）
│   └── broken_endpoints_review.md             # 断头端点复核（第一版）
├── merge_shandong_qinghai.py    # 山东/青海增量合并范例
├── merge_remaining_8_cities.py  # 冀黑湘苏津 8 城合并范例
└── legacy/                      # 旧构建流水线（不可在本机直接运行，会回退数据）
    ├── build_v2.py              # 从 Excel 全量重建 railway_data.py（依赖原 /root/uploads 路径）
    ├── railway_data_v2.0.bak
    └── railway_data_v2.1.bak
```

> 引擎以 `src/railway_data.py` 为权威拓扑源（LINE_ORDER / GRAPH / STATION_INFO 等 Python 对象）。
> `data/*.json` 是派生/辅助数据；`city_aliases.json`、`station_aliases.json`、`railway_data.json` 当前未被引擎读取，仅作备份与参考。

---

## 快速开始

### 1) 运行回归测试（无需任何依赖）

```bash
cd src
python student_ticket_checker.py --test
```

预期输出：`测试结果：通过 27/27，失败 0`

（已在合并后从本目录 src/ 实测通过。）

### 2) 交互式单条判断

```bash
cd src
python student_ticket_checker.py
```

按提示输入：学校城市、家庭城市、出发站、到达站、席别（可空）、是否新生/毕业生。

### 3) 启动 Web 演示（FastAPI + ECharts 前端）

```bash
pip install -r requirements.txt
# 方式 A（推荐）：在项目根目录执行
cd src && uvicorn web_app:app --host 0.0.0.0 --port 8080
# 方式 B：直接运行
cd src && python web_app.py
```

浏览器打开 http://127.0.0.1:8080 —— 可进行单区间判断、查看案例库、调用 `/api/check`。

---

## 本次合并做的关键修复

- **补齐规则层 `student_rules.json`**：第二版原始 `src/`、`data/` 均缺失该文件，引擎第 39 行
  `json.load(.../student_rules.json)["student_ticket"]` 会抛 `FileNotFoundError` 而无法导入。
  第一版含完整规则层（13 份官方规程抽取 + 10 个案例），两版引擎读取的 key 完全一致，
  已直接并入 `data/student_rules.json`，**无需改动引擎**即恢复 27/27 测试。

- **Web 前端兼容验证**：`web_app.py` 依赖 `check_student_ticket / check_compliance / suggest /
  find_multiple_paths_between_cities / check_route_segments / ALLOWED_SEATS`，
  这些符号在第二版引擎中均已存在（函数签名一致），故前端可直接驱动第二版数据层。

---

## 数据层改动铁律（后续维护必守）

1. **增量只加不删**：合并省份数据时 `to_add = merged - original`，绝不删除旧边/旧站。
2. **Dijkstra 只走「属于某条线」的边**：新连接必须以线路形式存在（含合成联络线），不能只往 `GRAPH` 加裸边。
3. **再生 `railway_data.py` 按内容标记截取 tail**（以 `LINE_NAME_ALIAS` / `def resolve_location` 定位），绝不用行号，否则会重复 `GRAPH=`。
4. **每次数据层改动后必须跑** `python -u src/student_ticket_checker.py --test`，27 条全绿才交付。
5. **枢纽解析必须 100%**（192/192）。

分省增量合并标准流程见 `skill/railway-data-province-merge/SKILL.md`。

---

## 数据层现状（v2.2）

253 条线路 / 1530 车站 / 330 城市 / 32 省级行政区 / 1528 图节点 / 192 枢纽站 100% 可解析。

## 后续可推进方向

- 继续按 SOP 合并更多分省 Excel，逐年复核新开通线路/车站。
- 功能扩展：多区间联程最优化建议、候补/中转时间约束、优惠区间自动推荐。
- 若需重建数据层，请使用 `skill/` 的增量合并流程，**不要**直接运行 `legacy/build_v2.py`（会回退到旧数据且依赖原构建服务器路径）。
