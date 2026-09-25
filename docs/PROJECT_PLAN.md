# 模切流程系统 — 从计划到完结全流程

依据《模切流程系统-初版开发清单》展开的完整项目交付。

## 一、核心原则（清单约束）

1. 库存以 **append-only stock_ledger** 为唯一真相源，禁止直接改余额
2. 工程版本 **RELEASED 后冻结**（BOM/工艺/排版锁定进工单）
3. 业务单据可追溯：`source_type` + `source_id`
4. 期间锁定后禁止出入库写入
5. 不设登录鉴权（按业务方要求）

## 二、阶段与交付对照

| 阶段 | 内容 | 代码位置 |
|------|------|----------|
| Phase 0 基础 | FastAPI、SQLAlchemy、单号、审计、统一响应 | `backend/app/core`, `models/audit`, `document_number` |
| Phase 1 采购库存 | 采购申请/订单/到货/IQC/退货、库存 in/out/transfer/adjust | `api/purchase`, `api/inventory`, `services/*` |
| Phase 2 工程 | 产品版本、BOM、工艺路线、排版、模具 | `api/engineering`, `models/engineering` |
| Phase 3 MRP | 销售订单、BOM 展开、净需求、PURCHASE/PRODUCE 建议 | `api/planning`, `services/planning` |
| Phase 4 生产 | 工单锁定版本、领退料、报工顺序、成品入库、WIP | `api/production`, `services/production` |
| Phase 5 质量成本 | 质量异常、追溯、标准成本、工单成本 | `api/quality`, `api/costing` |
| Phase 6 统计 | 日报、报表、Excel 导出钩子 | `api/reporting` |
| Phase 7 稳定 | 期间锁定、Docker、盘点调拨、看板、打包脚本 | `api/period`, `docker-compose`, `packaging/` |

## 三、业务闭环

```
主数据(物料/仓/供应商)
  → 工程(产品版本 BOM 工艺发布)
    → 销售订单 → MRP(采购建议+生产建议)
      → PO确认 → 到货 → IQC入库
      → 工单下达 → 领料(可进WIP) → 按序报工 → 成品入库 → 完工
        → 质量异常/追溯 → 成本归集 → 期间关账
```

## 四、前端页面清单

首页、物料、供应商、仓库、产品BOM、销售MRP、采购订单、到货IQC、采购退货、
库存余额、库存流水、盘点调拨、生产工单、生产看板、质量、报表、期间

## 五、运行方式

- 开发：backend uvicorn + frontend vite
- 容器：docker compose up --build
- Windows 单机：见 packaging/desktop/build_exe.ps1
- Android：见 packaging/android/README.md
