-- 阶段1：基础数据 + 库存核心表
-- 可在 SQLite 中直接执行：sqlite3 data/die_cutting.db < scripts/init_phase1_tables.sql

-- 计量单位
CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(16) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_units_code ON units (code);

-- 物料主数据
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    spec VARCHAR(256),
    material_type VARCHAR(32) NOT NULL DEFAULT 'RAW',
    base_unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    is_batch_managed BOOLEAN NOT NULL DEFAULT 0,
    is_roll_managed BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_materials_code ON materials (code);

-- 供应商
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    short_name VARCHAR(64),
    contact VARCHAR(64),
    phone VARCHAR(32),
    address VARCHAR(256),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_suppliers_code ON suppliers (code);

-- 客户
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    short_name VARCHAR(64),
    contact VARCHAR(64),
    phone VARCHAR(32),
    address VARCHAR(256),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_customers_code ON customers (code);

-- 仓库
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL,
    warehouse_type VARCHAR(32) NOT NULL DEFAULT 'NORMAL',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_warehouses_code ON warehouses (code);

-- 库位
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER NOT NULL,
    code VARCHAR(32) NOT NULL,
    name VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_warehouse_location UNIQUE (warehouse_id, code)
);
CREATE INDEX IF NOT EXISTS ix_locations_warehouse_id ON locations (warehouse_id);

-- 原因码
CREATE TABLE IF NOT EXISTS reason_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category VARCHAR(32) NOT NULL,
    code VARCHAR(32) NOT NULL,
    name VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_reason_category_code UNIQUE (category, code)
);
CREATE INDEX IF NOT EXISTS ix_reason_codes_category ON reason_codes (category);

-- 库存余额
CREATE TABLE IF NOT EXISTS stock_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    location_id INTEGER,
    batch_no VARCHAR(64) NOT NULL DEFAULT '',
    roll_no VARCHAR(64) NOT NULL DEFAULT '',
    qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_reserved NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_frozen NUMERIC(18, 6) NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_stock_balance_key UNIQUE (material_id, warehouse_id, location_id, batch_no, roll_no)
);
CREATE INDEX IF NOT EXISTS ix_stock_balances_material_id ON stock_balances (material_id);
CREATE INDEX IF NOT EXISTS ix_stock_balances_warehouse_id ON stock_balances (warehouse_id);

-- 库存流水（append-only）
CREATE TABLE IF NOT EXISTS stock_ledgers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type VARCHAR(32) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    source_line_id VARCHAR(64),
    material_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    location_id INTEGER,
    batch_no VARCHAR(64) NOT NULL DEFAULT '',
    roll_no VARCHAR(64) NOT NULL DEFAULT '',
    qty NUMERIC(18, 6) NOT NULL,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    direction VARCHAR(8) NOT NULL,
    original_ledger_id INTEGER,
    is_reversed BOOLEAN NOT NULL DEFAULT 0,
    reason_code VARCHAR(32),
    remark TEXT,
    created_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_stock_ledgers_source_type ON stock_ledgers (source_type);
CREATE INDEX IF NOT EXISTS ix_stock_ledgers_source_id ON stock_ledgers (source_id);
CREATE INDEX IF NOT EXISTS ix_stock_ledgers_material_id ON stock_ledgers (material_id);
CREATE INDEX IF NOT EXISTS ix_stock_ledgers_warehouse_id ON stock_ledgers (warehouse_id);
CREATE INDEX IF NOT EXISTS ix_stock_ledgers_created_at ON stock_ledgers (created_at);
CREATE INDEX IF NOT EXISTS ix_stock_ledgers_original_ledger_id ON stock_ledgers (original_ledger_id);

-- ========== 采购模块 ==========
CREATE TABLE IF NOT EXISTS purchase_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    request_date DATE NOT NULL,
    requester VARCHAR(64),
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_requests_doc_no ON purchase_requests (doc_no);

CREATE TABLE IF NOT EXISTS purchase_request_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL DEFAULT 1,
    material_id INTEGER NOT NULL,
    qty NUMERIC(18, 6) NOT NULL,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    required_date DATE,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_request_lines_request_id ON purchase_request_lines (request_id);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    supplier_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    expected_date DATE,
    currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
    remark TEXT,
    request_id INTEGER,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_orders_doc_no ON purchase_orders (doc_no);
CREATE INDEX IF NOT EXISTS ix_purchase_orders_supplier_id ON purchase_orders (supplier_id);

CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL DEFAULT 1,
    material_id INTEGER NOT NULL,
    qty NUMERIC(18, 6) NOT NULL,
    qty_received NUMERIC(18, 6) NOT NULL DEFAULT 0,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    unit_price NUMERIC(18, 6),
    expected_date DATE,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_order_lines_order_id ON purchase_order_lines (order_id);

CREATE TABLE IF NOT EXISTS arrival_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    order_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    arrival_date DATE NOT NULL,
    warehouse_id INTEGER NOT NULL,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_arrival_notes_doc_no ON arrival_notes (doc_no);
CREATE INDEX IF NOT EXISTS ix_arrival_notes_order_id ON arrival_notes (order_id);

CREATE TABLE IF NOT EXISTS arrival_note_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arrival_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL DEFAULT 1,
    order_line_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    qty NUMERIC(18, 6) NOT NULL,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    batch_no VARCHAR(64) NOT NULL DEFAULT '',
    roll_no VARCHAR(64) NOT NULL DEFAULT '',
    qc_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    qty_passed NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_failed NUMERIC(18, 6) NOT NULL DEFAULT 0,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_arrival_note_lines_arrival_id ON arrival_note_lines (arrival_id);

CREATE TABLE IF NOT EXISTS iqc_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    arrival_line_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    result VARCHAR(16) NOT NULL,
    qty_inspected NUMERIC(18, 6) NOT NULL,
    qty_passed NUMERIC(18, 6) NOT NULL,
    qty_failed NUMERIC(18, 6) NOT NULL,
    inspector VARCHAR(64),
    inspect_date DATE NOT NULL,
    defect_codes VARCHAR(256),
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_iqc_records_doc_no ON iqc_records (doc_no);
CREATE INDEX IF NOT EXISTS ix_iqc_records_arrival_line_id ON iqc_records (arrival_line_id);

-- ========== 采购退货 + 价格历史 ==========
CREATE TABLE IF NOT EXISTS purchase_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    supplier_id INTEGER NOT NULL,
    order_id INTEGER,
    return_date DATE NOT NULL,
    warehouse_id INTEGER NOT NULL,
    reason_code VARCHAR(32),
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_returns_doc_no ON purchase_returns (doc_no);
CREATE INDEX IF NOT EXISTS ix_purchase_returns_supplier_id ON purchase_returns (supplier_id);

CREATE TABLE IF NOT EXISTS purchase_return_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL DEFAULT 1,
    material_id INTEGER NOT NULL,
    qty NUMERIC(18, 6) NOT NULL,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    batch_no VARCHAR(64) NOT NULL DEFAULT '',
    roll_no VARCHAR(64) NOT NULL DEFAULT '',
    order_line_id INTEGER,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_return_lines_return_id ON purchase_return_lines (return_id);

CREATE TABLE IF NOT EXISTS purchase_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    unit_price NUMERIC(18, 6) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
    effective_date DATE NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'PO',
    source_id VARCHAR(64) NOT NULL,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_price_history_supplier_id ON purchase_price_history (supplier_id);
CREATE INDEX IF NOT EXISTS ix_purchase_price_history_material_id ON purchase_price_history (material_id);

-- ========== 阶段2 工程模块 ==========
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    customer_id INTEGER,
    customer_part_no VARCHAR(64),
    material_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_products_code ON products (code);

CREATE TABLE IF NOT EXISTS product_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    version_code VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    drawing_no VARCHAR(64),
    drawing_rev VARCHAR(32),
    released_at DATETIME,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_product_version UNIQUE (product_id, version_code)
);
CREATE INDEX IF NOT EXISTS ix_product_versions_product_id ON product_versions (product_id);

CREATE TABLE IF NOT EXISTS bom_headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_version_id INTEGER NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS bom_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bom_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL DEFAULT 1,
    material_id INTEGER NOT NULL,
    qty_per NUMERIC(18, 6) NOT NULL,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    scrap_rate NUMERIC(8, 4) NOT NULL DEFAULT 0,
    is_alternative BOOLEAN NOT NULL DEFAULT 0,
    alt_group VARCHAR(32),
    priority INTEGER NOT NULL DEFAULT 1,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_bom_lines_bom_id ON bom_lines (bom_id);

CREATE TABLE IF NOT EXISTS process_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_version_id INTEGER NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS process_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    seq INTEGER NOT NULL DEFAULT 10,
    step_code VARCHAR(32) NOT NULL,
    step_name VARCHAR(64) NOT NULL,
    step_type VARCHAR(32) NOT NULL DEFAULT 'GENERAL',
    work_center VARCHAR(64),
    std_time_sec NUMERIC(12, 2),
    mold_id INTEGER,
    param_json TEXT,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_process_steps_route_id ON process_steps (route_id);

CREATE TABLE IF NOT EXISTS molds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    mold_type VARCHAR(32) NOT NULL DEFAULT 'DIE',
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    life_limit INTEGER,
    life_used INTEGER NOT NULL DEFAULT 0,
    product_id INTEGER,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_molds_code ON molds (code);

CREATE TABLE IF NOT EXISTS nesting_layouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_version_id INTEGER NOT NULL,
    layout_code VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    material_id INTEGER NOT NULL,
    sheet_width NUMERIC(12, 4),
    sheet_length NUMERIC(12, 4),
    parts_per_sheet INTEGER NOT NULL DEFAULT 1,
    utilization_rate NUMERIC(8, 4),
    is_default BOOLEAN NOT NULL DEFAULT 0,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_version_layout UNIQUE (product_version_id, layout_code)
);
CREATE INDEX IF NOT EXISTS ix_nesting_layouts_product_version_id ON nesting_layouts (product_version_id);

-- ========== 阶段3 计划/MRP ==========
CREATE TABLE IF NOT EXISTS sales_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    required_date DATE,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sales_orders_doc_no ON sales_orders (doc_no);

CREATE TABLE IF NOT EXISTS sales_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL DEFAULT 1,
    product_id INTEGER NOT NULL,
    product_version_id INTEGER,
    material_id INTEGER,
    qty NUMERIC(18, 6) NOT NULL,
    qty_shipped NUMERIC(18, 6) NOT NULL DEFAULT 0,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    required_date DATE,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sales_order_lines_order_id ON sales_order_lines (order_id);

CREATE TABLE IF NOT EXISTS mrp_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DONE',
    sales_order_id INTEGER,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mrp_runs_run_no ON mrp_runs (run_no);

CREATE TABLE IF NOT EXISTS mrp_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    gross_qty NUMERIC(18, 6) NOT NULL,
    on_hand_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    reserved_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    on_order_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    net_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    suggestion_type VARCHAR(16) NOT NULL DEFAULT 'NONE',
    suggestion_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    source_type VARCHAR(32),
    source_id VARCHAR(64),
    parent_material_id INTEGER,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mrp_requirements_run_id ON mrp_requirements (run_id);
CREATE INDEX IF NOT EXISTS ix_mrp_requirements_material_id ON mrp_requirements (material_id);

-- ========== 阶段4 生产 ==========
CREATE TABLE IF NOT EXISTS work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    product_id INTEGER NOT NULL,
    product_version_id INTEGER NOT NULL,
    bom_id INTEGER,
    route_id INTEGER,
    nesting_id INTEGER,
    plan_qty NUMERIC(18, 6) NOT NULL,
    completed_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    scrap_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    warehouse_id INTEGER,
    fg_warehouse_id INTEGER,
    wip_warehouse_id INTEGER,
    plan_start DATE,
    plan_end DATE,
    sales_order_id INTEGER,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_work_orders_doc_no ON work_orders (doc_no);

CREATE TABLE IF NOT EXISTS work_order_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    qty_required NUMERIC(18, 6) NOT NULL,
    qty_issued NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_returned NUMERIC(18, 6) NOT NULL DEFAULT 0,
    unit VARCHAR(16) NOT NULL DEFAULT 'PCS',
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_work_order_materials_work_order_id ON work_order_materials (work_order_id);

CREATE TABLE IF NOT EXISTS work_order_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    seq INTEGER NOT NULL DEFAULT 10,
    step_code VARCHAR(32) NOT NULL,
    step_name VARCHAR(64) NOT NULL,
    step_type VARCHAR(32) NOT NULL DEFAULT 'GENERAL',
    mold_id INTEGER,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    qty_good NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_reject NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_scrap NUMERIC(18, 6) NOT NULL DEFAULT 0,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_work_order_operations_work_order_id ON work_order_operations (work_order_id);

CREATE TABLE IF NOT EXISTS operation_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    work_order_id INTEGER NOT NULL,
    operation_id INTEGER NOT NULL,
    qty_good NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_reject NUMERIC(18, 6) NOT NULL DEFAULT 0,
    qty_scrap NUMERIC(18, 6) NOT NULL DEFAULT 0,
    report_date DATE NOT NULL,
    operator_name VARCHAR(64),
    downtime_min NUMERIC(10, 2),
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_operation_reports_doc_no ON operation_reports (doc_no);
CREATE INDEX IF NOT EXISTS ix_operation_reports_work_order_id ON operation_reports (work_order_id);

-- ========== 阶段5 质量与成本 ==========
CREATE TABLE IF NOT EXISTS defect_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL,
    category VARCHAR(32) NOT NULL DEFAULT 'GENERAL',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS inspection_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    inspect_type VARCHAR(16) NOT NULL,
    result VARCHAR(16) NOT NULL,
    material_id INTEGER,
    work_order_id INTEGER,
    operation_id INTEGER,
    batch_no VARCHAR(64) NOT NULL DEFAULT '',
    qty_inspected NUMERIC(18, 6) NOT NULL,
    qty_passed NUMERIC(18, 6) NOT NULL,
    qty_failed NUMERIC(18, 6) NOT NULL,
    defect_codes VARCHAR(256),
    inspector VARCHAR(64),
    inspect_date DATE NOT NULL,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_inspection_records_inspect_type ON inspection_records (inspect_type);

CREATE TABLE IF NOT EXISTS quality_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN',
    issue_type VARCHAR(32) NOT NULL DEFAULT 'DEFECT',
    material_id INTEGER,
    work_order_id INTEGER,
    batch_no VARCHAR(64) NOT NULL DEFAULT '',
    qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    defect_codes VARCHAR(256),
    description TEXT,
    disposition VARCHAR(32),
    warehouse_id INTEGER,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS material_standard_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL UNIQUE,
    unit_cost NUMERIC(18, 6) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS work_order_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL UNIQUE,
    material_cost NUMERIC(18, 4) NOT NULL DEFAULT 0,
    scrap_cost NUMERIC(18, 4) NOT NULL DEFAULT 0,
    mold_cost NUMERIC(18, 4) NOT NULL DEFAULT 0,
    process_cost NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_cost NUMERIC(18, 4) NOT NULL DEFAULT 0,
    completed_qty NUMERIC(18, 6) NOT NULL DEFAULT 0,
    unit_cost NUMERIC(18, 6) NOT NULL DEFAULT 0,
    currency VARCHAR(8) NOT NULL DEFAULT 'CNY',
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);


-- ========== 阶段7 期间锁定 ==========
CREATE TABLE IF NOT EXISTS accounting_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN',
    locked_at DATETIME,
    locked_by VARCHAR(64),
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_period_year_month UNIQUE (year, month)
);


CREATE TABLE IF NOT EXISTS material_suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT 1,
    lead_time_days INTEGER,
    remark TEXT,
    created_by VARCHAR(64),
    updated_by VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_material_supplier UNIQUE (material_id, supplier_id)
);
CREATE INDEX IF NOT EXISTS ix_material_suppliers_material_id ON material_suppliers (material_id);
