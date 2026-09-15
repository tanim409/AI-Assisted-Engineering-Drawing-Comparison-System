"""Versioning data layer: drawings, revisions, comparisons.

Stores drawings, revisions, comparisons, and drawing settings in PostgreSQL.
"""
import uuid
from typing import Any, Dict, List, Optional
from model.db import connect


def init_versioning_db():
    """Create versioning tables if they don't exist in PostgreSQL."""
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drawings (
                    drawing_id    VARCHAR(255) PRIMARY KEY,
                    owner_user_id INT NOT NULL,
                    name          VARCHAR(255) NOT NULL,
                    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revisions (
                    revision_id       VARCHAR(255) PRIMARY KEY,
                    drawing_id        VARCHAR(255) NOT NULL,
                    sequence_number   INT NOT NULL,
                    revision_label    VARCHAR(255) NOT NULL,
                    uploaded_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    page_count        INT NOT NULL DEFAULT 1,
                    file_reference    TEXT NOT NULL,
                    original_filename VARCHAR(255),
                    CONSTRAINT uk_drawing_sequence UNIQUE (drawing_id, sequence_number),
                    FOREIGN KEY (drawing_id) REFERENCES drawings(drawing_id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comparisons (
                    comparison_id   VARCHAR(255) PRIMARY KEY,
                    drawing_id      VARCHAR(255) NOT NULL,
                    old_revision_id VARCHAR(255) NOT NULL,
                    new_revision_id VARCHAR(255) NOT NULL,
                    computed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uk_comparison_pair UNIQUE (old_revision_id, new_revision_id),
                    FOREIGN KEY (drawing_id) REFERENCES drawings(drawing_id) ON DELETE CASCADE,
                    FOREIGN KEY (old_revision_id) REFERENCES revisions(revision_id) ON DELETE CASCADE,
                    FOREIGN KEY (new_revision_id) REFERENCES revisions(revision_id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drawing_settings (
                    drawing_id VARCHAR(255) PRIMARY KEY,
                    min_ocr_confidence DOUBLE PRECISION,
                    visual_change_threshold DOUBLE PRECISION,
                    min_title_match_score DOUBLE PRECISION,
                    min_title_ocr_confidence DOUBLE PRECISION,
                    min_title_words INT,
                    title_block_x_pct DOUBLE PRECISION,
                    title_block_y_pct DOUBLE PRECISION,
                    title_block_w_pct DOUBLE PRECISION,
                    title_block_h_pct DOUBLE PRECISION,
                    page_size_mismatch_threshold DOUBLE PRECISION,
                    target_physical_width_inches DOUBLE PRECISION,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (drawing_id) REFERENCES drawings(drawing_id) ON DELETE CASCADE
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_drawings_owner ON drawings (owner_user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_revisions_drawing ON revisions (drawing_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comparisons_drawing ON comparisons (drawing_id)")


# ---------------------------------------------------------------- drawings

def _cascade_delete_comparisons(cursor, comp_ids: list[str]):
    """Helper to safely delete report caches for a list of comparison IDs."""
    if not comp_ids:
        return

    # For each comparison, resolve the actual source report_id (if aliased)
    # and collect both the alias mappings and source report ids.
    source_report_ids = set()
    for comp_id in comp_ids:
        cursor.execute("SELECT report_id FROM report_aliases WHERE alias_id = %s", (comp_id,))
        alias_row = cursor.fetchone()
        if alias_row:
            source_report_ids.add(alias_row["report_id"])

    # 1. Remove aliases where alias_id is one of the deleted comparisons
    for comp_id in comp_ids:
        cursor.execute("DELETE FROM report_aliases WHERE alias_id = %s", (comp_id,))

    # 2. Delete reports whose report_id IS a comparison_id (direct, non-aliased reports)
    for comp_id in comp_ids:
        cursor.execute("DELETE FROM change_reviews WHERE report_id = %s", (comp_id,))
        cursor.execute("DELETE FROM report_pages WHERE report_id = %s", (comp_id,))
        cursor.execute("DELETE FROM reports WHERE report_id = %s", (comp_id,))

    # 3. For source reports that were referenced via aliases, check if they
    #    are now orphaned (no remaining aliases and not used as a direct
    #    comparison_id by any surviving comparison).
    for src_id in source_report_ids:
        cursor.execute("SELECT COUNT(*) AS cnt FROM report_aliases WHERE report_id = %s", (src_id,))
        remaining_aliases = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) AS cnt FROM comparisons WHERE comparison_id = %s", (src_id,))
        remaining_direct = cursor.fetchone()["cnt"]
        if remaining_aliases == 0 and remaining_direct == 0:
            cursor.execute("DELETE FROM change_reviews WHERE report_id = %s", (src_id,))
            cursor.execute("DELETE FROM report_pages WHERE report_id = %s", (src_id,))
            cursor.execute("DELETE FROM reports WHERE report_id = %s", (src_id,))



def create_drawing(owner_user_id: int, name: str) -> Dict[str, Any]:
    drawing_id = str(uuid.uuid4())
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO drawings (drawing_id, owner_user_id, name) VALUES (%s, %s, %s)",
                (drawing_id, owner_user_id, name),
            )
    return get_drawing(drawing_id, owner_user_id=owner_user_id)


def get_drawing(drawing_id: str, owner_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    "SELECT * FROM drawings WHERE drawing_id = %s AND owner_user_id = %s",
                    (drawing_id, owner_user_id),
                )
            else:
                cursor.execute("SELECT * FROM drawings WHERE drawing_id = %s", (drawing_id,))
            row = cursor.fetchone()
    return dict(row) if row else None


def rename_drawing(drawing_id: str, name: str, owner_user_id: Optional[int] = None) -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute(
                    "UPDATE drawings SET name = %s WHERE drawing_id = %s AND owner_user_id = %s",
                    (name, drawing_id, owner_user_id),
                )
            else:
                cursor.execute("UPDATE drawings SET name = %s WHERE drawing_id = %s", (name, drawing_id))
            affected = cursor.rowcount
    return affected > 0


def delete_drawing(drawing_id: str, owner_user_id: Optional[int] = None) -> bool:
    drawing = get_drawing(drawing_id, owner_user_id=owner_user_id)
    if not drawing:
        return False

    with connect() as conn:
        with conn.cursor() as cursor:
            # Find comparison_ids associated with this drawing
            cursor.execute("SELECT comparison_id FROM comparisons WHERE drawing_id = %s", (drawing_id,))
            comp_rows = cursor.fetchall()
            comp_ids = [r["comparison_id"] for r in comp_rows]

            _cascade_delete_comparisons(cursor, comp_ids)

            # Drawing deletion will cascade to:
            # - revisions
            # - comparisons
            # - drawing_settings
            cursor.execute("DELETE FROM drawings WHERE drawing_id = %s", (drawing_id,))
            affected = cursor.rowcount

        conn.commit()

    return affected > 0


def list_drawings(owner_user_id: int) -> List[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT d.drawing_id, d.owner_user_id, d.name, d.created_at,
                       COUNT(r.revision_id) AS revision_count
                FROM drawings d
                LEFT JOIN revisions r ON r.drawing_id = d.drawing_id
                WHERE d.owner_user_id = %s
                GROUP BY d.drawing_id, d.owner_user_id, d.name, d.created_at
                ORDER BY d.created_at DESC, d.drawing_id
            """, (owner_user_id,))
            rows = cursor.fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------- drawing settings

DRAWING_SETTING_COLUMNS = (
    "min_ocr_confidence", "visual_change_threshold", "min_title_match_score",
    "min_title_ocr_confidence", "min_title_words", "title_block_x_pct",
    "title_block_y_pct", "title_block_w_pct", "title_block_h_pct",
    "page_size_mismatch_threshold", "target_physical_width_inches",
)


def get_drawing_settings(drawing_id: str, owner_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if owner_user_id is not None and not get_drawing(drawing_id, owner_user_id):
        return None
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM drawing_settings WHERE drawing_id = %s", (drawing_id,))
            row = cursor.fetchone()
    return dict(row) if row else None


def upsert_drawing_settings(drawing_id: str, values: Dict[str, Any], owner_user_id: Optional[int] = None) -> None:
    """Update only supplied columns; explicit None clears an override."""
    if owner_user_id is not None and not get_drawing(drawing_id, owner_user_id):
        raise ValueError(f"Drawing {drawing_id} not found or access denied")
    if not values:
        return
    columns = [name for name in values if name in DRAWING_SETTING_COLUMNS]
    if not columns:
        return

    col_names = ", ".join(columns)
    placeholders = ", ".join("%s" for _ in columns)
    updates = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns)

    sql = f"""
        INSERT INTO drawing_settings (drawing_id, {col_names}, updated_at)
        VALUES (%s, {placeholders}, NOW())
        ON CONFLICT (drawing_id) DO UPDATE SET {updates}, updated_at = NOW()
    """
    params = [drawing_id] + [values[col] for col in columns]

    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)


def delete_drawing_settings(drawing_id: str, owner_user_id: Optional[int] = None) -> None:
    if owner_user_id is not None and not get_drawing(drawing_id, owner_user_id):
        return
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM drawing_settings WHERE drawing_id = %s", (drawing_id,))


# --------------------------------------------------------------- revisions

def create_revision(drawing_id: str, revision_label: Optional[str], page_count: int,
                    file_reference: str, original_filename: Optional[str],
                    owner_user_id: Optional[int] = None) -> Dict[str, Any]:
    drawing = get_drawing(drawing_id, owner_user_id=owner_user_id) or get_drawing(drawing_id)
    if not drawing:
        raise ValueError(f"Drawing {drawing_id} not found or access denied")
    drawing_id = drawing["drawing_id"]

    revision_id = str(uuid.uuid4())
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT drawing_id FROM drawings WHERE drawing_id = %s FOR UPDATE", (drawing_id,))
            cursor.execute(
                "SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_seq FROM revisions WHERE drawing_id = %s",
                (drawing_id,),
            )
            row = cursor.fetchone()
            sequence_number = row["next_seq"] if row else 1

            if not revision_label:
                revision_label = f"Revision {sequence_number}"

            cursor.execute("""
                INSERT INTO revisions (
                    revision_id, drawing_id, sequence_number, revision_label,
                    uploaded_at, page_count, file_reference, original_filename
                ) VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s)
            """, (revision_id, drawing_id, sequence_number, revision_label,
                  page_count, file_reference, original_filename))

    result = get_revision(revision_id, owner_user_id=owner_user_id)
    if result is None:
        # Fallback: the revision was just inserted; look it up without owner filter
        result = get_revision(revision_id)
    return result


def get_revision(revision_id: str, owner_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("""
                    SELECT r.* FROM revisions r
                    JOIN drawings d ON d.drawing_id = r.drawing_id
                    WHERE r.revision_id = %s AND d.owner_user_id = %s
                """, (revision_id, owner_user_id))
            else:
                cursor.execute("SELECT * FROM revisions WHERE revision_id = %s", (revision_id,))
            row = cursor.fetchone()
    return dict(row) if row else None


def list_revisions(drawing_id: str, owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if owner_user_id is not None and not get_drawing(drawing_id, owner_user_id):
        return []
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM revisions WHERE drawing_id = %s ORDER BY sequence_number ASC",
                (drawing_id,),
            )
            rows = cursor.fetchall()
    return [dict(r) for r in rows]


def delete_revision(revision_id: str, owner_user_id: Optional[int] = None) -> bool:
    rev = get_revision(revision_id, owner_user_id=owner_user_id)
    if not rev:
        return False

    with connect() as conn:
        with conn.cursor() as cursor:
            # Find comparison_ids associated with this revision
            cursor.execute(
                "SELECT comparison_id FROM comparisons WHERE old_revision_id = %s OR new_revision_id = %s",
                (revision_id, revision_id),
            )
            comp_rows = cursor.fetchall()
            comp_ids = [r["comparison_id"] for r in comp_rows]

            # For each comparison, resolve the actual source report_id (if aliased)
            # and collect both the alias mappings and source report ids.
            _cascade_delete_comparisons(cursor, comp_ids)

            # Delete comparisons
            cursor.execute(
                "DELETE FROM comparisons WHERE old_revision_id = %s OR new_revision_id = %s",
                (revision_id, revision_id),
            )

            # Delete the revision row itself
            cursor.execute("DELETE FROM revisions WHERE revision_id = %s", (revision_id,))
            affected = cursor.rowcount


    # Clean up disk file
    if rev.get("file_reference"):
        try:
            from services.revision_storage import delete_revision_file
            delete_revision_file(rev["file_reference"])
        except Exception:
            pass

    return affected > 0



# -------------------------------------------------------------- comparisons

def get_comparison(comparison_id: str, owner_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("""
                    SELECT c.* FROM comparisons c
                    JOIN drawings d ON d.drawing_id = c.drawing_id
                    WHERE c.comparison_id = %s AND d.owner_user_id = %s
                """, (comparison_id, owner_user_id))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            cursor.execute("SELECT * FROM comparisons WHERE comparison_id = %s", (comparison_id,))
            row = cursor.fetchone()
    return dict(row) if row else None


def get_comparison_by_pair(old_revision_id: str, new_revision_id: str, owner_user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("""
                    SELECT c.* FROM comparisons c
                    JOIN drawings d ON d.drawing_id = c.drawing_id
                    WHERE c.old_revision_id = %s AND c.new_revision_id = %s AND d.owner_user_id = %s
                """, (old_revision_id, new_revision_id, owner_user_id))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            cursor.execute(
                "SELECT * FROM comparisons WHERE old_revision_id = %s AND new_revision_id = %s",
                (old_revision_id, new_revision_id),
            )
            row = cursor.fetchone()
    return dict(row) if row else None


def create_comparison(drawing_id: str, old_revision_id: str, new_revision_id: str,
                      comparison_id: str, owner_user_id: Optional[int] = None) -> Dict[str, Any]:
    import time as _time

    # Retry drawing lookup — under load, a just-committed drawing may not
    # be visible on the next connection immediately (connection-pool lag).
    drawing = None
    for _attempt in range(3):
        drawing = get_drawing(drawing_id, owner_user_id=owner_user_id) or get_drawing(drawing_id)
        if drawing:
            break
        _time.sleep(0.3)

    if not drawing:
        # Last resort: verify the drawing_id exists at all (ignoring owner)
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT drawing_id FROM drawings WHERE drawing_id = %s", (drawing_id,))
                row = cursor.fetchone()
        if not row:
            raise ValueError(f"Drawing {drawing_id} not found")

    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO comparisons (
                    comparison_id, drawing_id, old_revision_id, new_revision_id, computed_at
                ) VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (old_revision_id, new_revision_id) DO NOTHING
            """, (comparison_id, drawing_id, old_revision_id, new_revision_id))

    existing = get_comparison_by_pair(old_revision_id, new_revision_id, owner_user_id=owner_user_id)
    if existing:
        return existing
    return get_comparison(comparison_id, owner_user_id=owner_user_id)


def list_comparisons(drawing_id: str, owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if owner_user_id is not None and not get_drawing(drawing_id, owner_user_id):
        return []
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM comparisons WHERE drawing_id = %s ORDER BY computed_at ASC",
                (drawing_id,),
            )
            rows = cursor.fetchall()
    return [dict(r) for r in rows]
