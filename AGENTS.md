# AGENTS.md - 12306 学生票合规判定 Agent

## 项目概览

12306 学生票合规判定 Web 应用，判断学生票购票区间是否落在学校与家庭优惠区间的合理径路上，支持反向购票识别、改家庭所在地、联程分段等建议。

## 技术栈

- **后端**: Python 3.12 + FastAPI + Jinja2 (服务端渲染)
- **服务器**: Uvicorn
- **前端**: HTML/CSS + ECharts (图表)

## 目录结构

```
├── src/
│   ├── web_app.py                 # FastAPI Web 应用主入口
│   ├── student_ticket_checker.py  # 合规引擎核心
│   ├── railway_data.py            # 铁路数据层（权威拓扑源）
│   └── test_cases.py              # 27 条回归测试用例
├── data/                          # JSON 数据文件（规则、站点、线路等）
├── web/
│   ├── templates/                 # Jinja2 HTML 模板
│   └── static/                    # 静态资源 (CSS, 图片)
├── requirements.txt               # Python 依赖
├── .coze                          # Coze 构建/运行配置
└── start.sh                       # 启动脚本
```

## 构建与运行

```bash
# 安装依赖
pip3 install -r requirements.txt

# 启动服务（开发环境，端口从环境变量读取）
python3 -m uvicorn src.web_app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT}

# 运行回归测试
cd src && python3 student_ticket_checker.py --test
```

## API 接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（学生票查询表单） |
| `/check` | GET/POST | 学生票合规判断（支持表单和查询参数） |
| `/cases` | GET | 案例库页面 |
| `/api/stations` | GET | 获取站点列表（JSON） |
| `/api/ai_check` | POST | AI 辅助判定代理（转发至多平台 API） |
| `/static/*` | GET | 静态资源 |

## 关键文件说明

- `src/railway_data.py`: 权威拓扑源，包含 LINE_ORDER、GRAPH、STATION_INFO 等
- `src/student_ticket_checker.py`: 合规引擎，提供 check_student_ticket、check_compliance、suggest 等核心函数
- `data/student_rules.json`: 规则层（席别白名单、每年4次限制、新生毕业生规则、案例库）
