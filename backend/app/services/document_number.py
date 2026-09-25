"""业务单据编号服务

规则示例：
  PO202609250001  → 采购订单
  WO202609250001  → 生产工单
  IN202609250001  → 入库单
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_number import DocumentSequence


# 单据类型前缀映射（后续可扩展）
DOC_PREFIX_MAP = {
    "PO": "PO",   # 采购订单
    "PR": "PR",   # 采购申请
    "AR": "AR",   # 到货单
    "RT": "RT",   # 采购退货
    "WO": "WO",   # 生产工单
    "IN": "IN",   # 入库
    "OUT": "OUT", # 出库
    "TR": "TR",   # 转移
    "QC": "QC",   # 质检
    "SO": "SO",   # 销售订单
    "MRP": "MRP", # MRP运算
    "OPR": "OPR", # 工序报工
    "INS": "INS", # 检验
    "QI": "QI",   # 质量异常
    "ADJ": "ADJ", # 盘点调整
}


async def generate_document_number(
    db: AsyncSession,
    doc_type: str,
    prefix: str | None = None,
    date_obj: date | None = None,
) -> str:
    """
    生成下一个单据编号。

    Args:
        db: 数据库会话
        doc_type: 单据类型（如 PO / WO / IN）
        prefix: 可选自定义前缀，默认使用 DOC_PREFIX_MAP
        date_obj: 可选业务日期，默认今天

    Returns:
        完整编号，例如 PO202609250001
    """
    if date_obj is None:
        date_obj = date.today()
    date_key = date_obj.strftime("%Y%m%d")
    actual_prefix = prefix or DOC_PREFIX_MAP.get(doc_type.upper(), doc_type.upper())

    # 查找或创建序列
    stmt = select(DocumentSequence).where(
        DocumentSequence.doc_type == doc_type.upper(),
        DocumentSequence.date_key == date_key,
    )
    result = await db.execute(stmt)
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = DocumentSequence(
            doc_type=doc_type.upper(),
            date_key=date_key,
            current_value=1,
            prefix=actual_prefix,
        )
        db.add(seq)
    else:
        seq.current_value += 1

    await db.flush()  # 获取最新值

    # 格式：前缀 + 日期 + 4位序号
    number = f"{seq.prefix}{date_key}{seq.current_value:04d}"
    return number
