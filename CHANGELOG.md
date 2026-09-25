# Changelog

## v1.0.3

- 采购订单：待到货数量汇总与明细
- 采购价格历史页（按供应商/物料筛选）
- 仓库页快捷仓间调拨

## v1.0.2 (仓库与采购)

- 仓库：库位维护、按仓库存合计卡片、类型 WIP/QC/SCRAP
- 采购：申请 PR、申请转 PO、多行订单+单价、状态筛选、确认

## v1.0.1 (优化)

- CI：`main` 分支 push 自动触发 Windows EXE / Android APK 构建
- 报表：新增工单、库存余额 Excel 导出
- 生产看板：30 秒自动刷新
- CORS：默认兼容本机 8000 与通配（便于 EXE）
- 启动器：等待健康检查后再打开浏览器

## v1.0.0

- 完整业务闭环：主数据 → 工程 → MRP → 采购/IQC → 生产/WIP → 质量成本 → 期间
- Docker Compose、种子数据、GitHub Release（源码 / EXE / Debug APK）
