# HallSpan 考场间距排座

在考室网格上按最小曼哈顿距离排座，同试卷套不得四邻相邻，并输出违规与统计。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4900 |
| API | http://localhost:9900 |
| API 文档 | http://localhost:9900/docs |
| Postgres | localhost:5450 |

健康检查：`GET http://localhost:9900/api/health`

## 使用说明

1. 在「考室」「考生」「试卷套」确认基础数据。
2. 打开「排座图」执行间距排座。
3. 在「违规」查看间距或同卷相邻问题。
4. 在「统计」查看占用与违规汇总。

## 锁定位

- 在「排座图」点击已入座课桌可锁定/解锁该考生（🔒）；锁定只改当前最新方案。
- 重新排座时被锁考生必须留在原格，新图、违规、统计与锁位一致（「保锁」）。
- 若新约束（如调大最小间距）使锁位已不合法，整场排座失败（HTTP 409）且不新增方案，绝不拆掉锁位硬排别人。
- 解锁后下一次排座才允许重排原格；历史方案上的锁标记不会被后续新排回刷。
- 相关接口：`POST /api/seating/lock`、`GET /api/seating/plans`、`GET /api/seating/plans/{id}`、`PUT /api/halls/{id}`。

## 开发与测试

```bash
docker compose exec api pytest -q
```
