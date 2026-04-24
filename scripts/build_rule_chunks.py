# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/24 21:10
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
5号窗口：规则文档 chunk 构建脚本

作用：
1. 读取 docs/rules/ 或 data/rules/ 下的规则 Markdown 文档；
2. 调用 app.rag.ingest.ingest_service.ingest_rules_to_db；
3. 将规则文档切分结果写入 rule_chunk 表；
4. 同时可选生成 data/rag/rule_chunks.jsonl，兼容旧版 baseline 检索器。

运行方式：
python -m scripts.build_rule_chunks

常用参数：
python -m scripts.build_rule_chunks --max-chars 600 --overlap 1
python -m scripts.build_rule_chunks --rules-dir docs/rules
python -m scripts.build_rule_chunks --keep-existing
python -m scripts.build_rule_chunks --no-jsonl
"""

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.rag.ingest.ingest_service import ingest_rules_to_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="构建规则文档 rule_chunk，并写入数据库。"
    )

    parser.add_argument(
        "--rules-dir",
        type=str,
        default=None,
        help="规则文档目录。默认优先使用 docs/rules，不存在则使用 data/rules。",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="JSONL/manifest 输出目录。默认 data/rag。",
    )

    parser.add_argument(
        "--max-chars",
        type=int,
        default=600,
        help="单个 chunk 最大字符数，默认 600。",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=1,
        help="chunk 之间保留的重叠段落数，默认 1。",
    )

    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="保留已有 rule_chunk，不清空重建。默认会清空后重建。",
    )

    parser.add_argument(
        "--no-jsonl",
        action="store_true",
        help="只写数据库，不生成 data/rag/rule_chunks.jsonl。",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    rules_dir = Path(args.rules_dir).resolve() if args.rules_dir else None
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None

    replace_existing = not args.keep_existing
    save_jsonl_file = not args.no_jsonl

    print("=" * 80)
    print("5号窗口：规则文档 chunk 构建开始")
    print(f"rules_dir        : {rules_dir or '默认：docs/rules 或 data/rules'}")
    print(f"output_dir       : {output_dir or '默认：data/rag'}")
    print(f"max_chars        : {args.max_chars}")
    print(f"overlap          : {args.overlap}")
    print(f"replace_existing : {replace_existing}")
    print(f"save_jsonl_file  : {save_jsonl_file}")
    print("=" * 80)

    db = SessionLocal()

    try:
        result = ingest_rules_to_db(
            db=db,
            rules_dir=rules_dir,
            output_dir=output_dir,
            max_chars=args.max_chars,
            overlap_paragraphs=args.overlap,
            replace_existing=replace_existing,
            save_jsonl_file=save_jsonl_file,
        )

        print("\n规则文档 chunk 构建完成。")
        print(f"规则目录      : {result['rules_dir']}")
        print(f"输出目录      : {result['output_dir']}")
        print(f"文档数量      : {result['doc_count']}")
        print(f"chunk 数量    : {result['chunk_count']}")
        print(f"DB 写入数量   : {result['db_inserted']}")
        print(f"是否清空重建  : {result['replace_existing']}")
        print(f"chunks 文件   : {result['chunks_path']}")
        print(f"manifest 文件 : {result['manifest_path']}")

    except Exception:
        db.rollback()
        print("\n规则文档 chunk 构建失败，事务已回滚。")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()