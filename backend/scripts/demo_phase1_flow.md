# 阶段1 完整闭环演示脚本

本地启动后端后，可用 curl 或 Swagger (`/docs`) 按下列顺序验证。

## 0. 健康检查
```bash
curl http://localhost:8000/api/v1/health
```

## 1. 基础数据
```bash
# 单位
curl -X POST http://localhost:8000/api/v1/master/units \
  -H 'Content-Type: application/json' \
  -d '{"code":"PCS","name":"个"}'

# 物料
curl -X POST http://localhost:8000/api/v1/master/materials \
  -H 'Content-Type: application/json' \
  -d '{"code":"M001","name":"PET膜","material_type":"RAW","base_unit":"PCS","is_batch_managed":true}'

# 供应商
curl -X POST http://localhost:8000/api/v1/master/suppliers \
  -H 'Content-Type: application/json' \
  -d '{"code":"S001","name":"示例供应商"}'

# 仓库：原料仓 + 待检仓 + 隔离仓
curl -X POST http://localhost:8000/api/v1/master/warehouses \
  -H 'Content-Type: application/json' \
  -d '{"code":"WH01","name":"原料仓","warehouse_type":"NORMAL"}'
curl -X POST http://localhost:8000/api/v1/master/warehouses \
  -H 'Content-Type: application/json' \
  -d '{"code":"QC01","name":"待检仓","warehouse_type":"QC"}'
curl -X POST http://localhost:8000/api/v1/master/warehouses \
  -H 'Content-Type: application/json' \
  -d '{"code":"HOLD01","name":"隔离仓","warehouse_type":"QC"}'
```

## 2. 采购订单 → 确认（自动写价格历史）
```bash
curl -X POST http://localhost:8000/api/v1/purchase/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "supplier_id": 1,
    "order_date": "2026-09-25",
    "lines": [{"material_id": 1, "qty": 1000, "unit_price": 1.25}]
  }'

curl -X POST http://localhost:8000/api/v1/purchase/orders/1/confirm
```

## 3. 到货登记
```bash
curl -X POST http://localhost:8000/api/v1/purchase/arrivals \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id": 1,
    "arrival_date": "2026-09-25",
    "warehouse_id": 2,
    "lines": [{
      "order_line_id": 1,
      "material_id": 1,
      "qty": 1000,
      "batch_no": "B20260925"
    }]
  }'
```

## 4. IQC 合格入库（产生 stock_ledger）
```bash
curl -X POST http://localhost:8000/api/v1/purchase/iqc \
  -H 'Content-Type: application/json' \
  -d '{
    "arrival_line_id": 1,
    "result": "PASSED",
    "qty_inspected": 1000,
    "qty_passed": 980,
    "qty_failed": 20,
    "inspect_date": "2026-09-25",
    "target_warehouse_id": 1,
    "hold_warehouse_id": 3
  }'
```

## 5. 验证库存
```bash
curl "http://localhost:8000/api/v1/inventory/balances?material_id=1"
curl "http://localhost:8000/api/v1/inventory/ledgers?source_type=PURCHASE_IN"
curl "http://localhost:8000/api/v1/inventory/ledgers?source_type=QC_HOLD"
```

## 6. 采购退货（出库）
```bash
curl -X POST http://localhost:8000/api/v1/purchase/returns \
  -H 'Content-Type: application/json' \
  -d '{
    "supplier_id": 1,
    "return_date": "2026-09-25",
    "warehouse_id": 1,
    "order_id": 1,
    "reason_code": "QUALITY",
    "lines": [{"material_id": 1, "qty": 50, "batch_no": "B20260925"}]
  }'

curl -X POST http://localhost:8000/api/v1/purchase/returns/1/confirm

# 验证出库流水
curl "http://localhost:8000/api/v1/inventory/ledgers?source_type=PURCHASE_RETURN"
```

## 7. 价格历史
```bash
curl "http://localhost:8000/api/v1/purchase/price-history?material_id=1"
```

## 验收检查清单
- [ ] IQC 合格后 `stock_ledgers` 有 `PURCHASE_IN` 流水
- [ ] 不合格有 `QC_HOLD` 流水（若指定隔离仓）
- [ ] 退货确认后有 `PURCHASE_RETURN` 出库流水
- [ ] 余额 = 流水汇总，不可直接改余额
- [ ] 负库存出库被拦截（409）
- [ ] 冲销接口可用：`POST /inventory/ledgers/{id}/reverse`
