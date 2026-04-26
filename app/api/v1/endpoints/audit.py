# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 12:10
IDE       :PyCharm
作者      :董宏升

审核接口
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
import pandas as pd

from app.db.session import get_db
from app.models.product_clean import ProductClean
from app.schemas.audit import AuditRunRequest, AuditRunResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/run", response_model=AuditRunResponse)
def run_audit(
        request: AuditRunRequest,
        db: Session = Depends(get_db),
):
    """
    最小审核入口：
    - 指定 clean_ids：审核指定 product_clean 记录
    - 不指定 clean_ids：按 limit 抽取前 N 条记录
    """

    if request.clean_ids:
        stmt = (
            select(ProductClean)
            .where(ProductClean.id.in_(request.clean_ids))
            .order_by(ProductClean.id.asc())
        )
    else:
        stmt = (
            select(ProductClean)
            .order_by(ProductClean.id.asc())
            .limit(request.limit)
        )

    rows = list(db.scalars(stmt).all())
    if not rows:
        raise HTTPException(status_code=404, detail="未找到可审核的 product_clean 数据")

    frame = pd.DataFrame(
        [
            {
                "clean_id": row.id,
                "normalized_brand": getattr(row, "standardized_brand", None),
                "normalized_spec": getattr(row, "normalized_spec", None),
                "normalized_platform": getattr(row, "clean_platform", None),
                "price": getattr(row, "clean_price", None),
                "clean_title": getattr(row, "clean_title", None),
                "clean_spec": getattr(row, "clean_spec", None),

                # 规则引擎当前最小辅助列
                "title_spec_hint": "",
                "title_spec_mismatch_flag": False,
                "missing_normalized_spec_flag": (
                        str(getattr(row, "normalized_spec", "") or "").strip() == ""
                ),
            }
            for row in rows
        ]
    )

    service = AuditService(db)
    result = service.run_audit(
        normalized_df=frame,
        persist_all_results=request.persist_all_results,
        auto_commit=True,
    )

    return AuditRunResponse(
        success=True,
        total_input_records=len(rows),
        total_audit_results=result["total_audit_results"],
        summary=result["summary"],
    )
