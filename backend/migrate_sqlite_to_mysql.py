"""One-time migration script to move existing data from reports.db (SQLite) to MySQL.

Preserves all primary keys, drawing IDs, report IDs, job IDs, and foreign keys.
Existing data is owned by default migration user (user_id = 1).
"""
import os
import sqlite3
from pathlib import Path
from model.db import connect
from model.report_db import init_db
from model.versioning_db import init_versioning_db
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SQLITE_DB_PATH = Path(__file__).parent / "model" / "reports.db"


def migrate():
    print("[Migration] Initializing MySQL tables...")
    init_db()
    init_versioning_db()

    with connect() as conn:
        with conn.cursor() as cursor:
            # Ensure default migration user exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = 1 OR email = %s", ("migration_admin@system.local",))
            admin_user = cursor.fetchone()
            if not admin_user:
                dummy_hash = pwd_context.hash("MigrationPass123!")
                cursor.execute("""
                    INSERT INTO users (user_id, email, password_hash, email_verified, created_at, is_active)
                    VALUES (1, 'migration_admin@system.local', %s, TRUE, NOW(), TRUE)
                """, (dummy_hash,))
                print("[Migration] Created default migration user (user_id = 1)")
            else:
                print(f"[Migration] Using existing migration user (user_id = {admin_user['user_id']})")

    if not SQLITE_DB_PATH.exists():
        print(f"[Migration] SQLite database file {SQLITE_DB_PATH} not found. Skipping row copy.")
        return

    print(f"[Migration] Reading data from {SQLITE_DB_PATH}...")
    s_conn = sqlite3.connect(SQLITE_DB_PATH)
    s_conn.row_factory = sqlite3.Row

    with connect() as conn:
        with conn.cursor() as cursor:
            # 1. drawings
            drawings = s_conn.execute("SELECT * FROM drawings").fetchall()
            for d in drawings:
                cursor.execute("""
                    INSERT INTO drawings (drawing_id, owner_user_id, name, created_at)
                    VALUES (%s, 1, %s, %s)
                    ON DUPLICATE KEY UPDATE name=VALUES(name)
                """, (d["drawing_id"], d["name"], d["created_at"]))
            print(f"[Migration] Migrated {len(drawings)} drawings")

            # 2. revisions
            revisions = s_conn.execute("SELECT * FROM revisions").fetchall()
            for r in revisions:
                cursor.execute("""
                    INSERT INTO revisions (
                        revision_id, drawing_id, sequence_number, revision_label,
                        uploaded_at, page_count, file_reference, original_filename
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE revision_label=VALUES(revision_label)
                """, (
                    r["revision_id"], r["drawing_id"], r["sequence_number"], r["revision_label"],
                    r["uploaded_at"], r["page_count"], r["file_reference"], r["original_filename"]
                ))
            print(f"[Migration] Migrated {len(revisions)} revisions")

            # 3. comparisons
            comparisons = s_conn.execute("SELECT * FROM comparisons").fetchall()
            for c in comparisons:
                cursor.execute("""
                    INSERT INTO comparisons (
                        comparison_id, drawing_id, old_revision_id, new_revision_id, computed_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE computed_at=VALUES(computed_at)
                """, (c["comparison_id"], c["drawing_id"], c["old_revision_id"], c["new_revision_id"], c["computed_at"]))
            print(f"[Migration] Migrated {len(comparisons)} comparisons")

            # 4. drawing_settings
            try:
                settings = s_conn.execute("SELECT * FROM drawing_settings").fetchall()
                for s in settings:
                    cursor.execute("""
                        INSERT INTO drawing_settings (
                            drawing_id, min_ocr_confidence, visual_change_threshold, min_title_match_score,
                            min_title_ocr_confidence, min_title_words, title_block_x_pct, title_block_y_pct,
                            title_block_w_pct, title_block_h_pct, page_size_mismatch_threshold,
                            target_physical_width_inches, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE updated_at=VALUES(updated_at)
                    """, (
                        s["drawing_id"], s["min_ocr_confidence"], s["visual_change_threshold"], s["min_title_match_score"],
                        s["min_title_ocr_confidence"], s["min_title_words"], s["title_block_x_pct"], s["title_block_y_pct"],
                        s["title_block_w_pct"], s["title_block_h_pct"], s["page_size_mismatch_threshold"],
                        s["target_physical_width_inches"], s["updated_at"]
                    ))
                print(f"[Migration] Migrated {len(settings)} drawing settings")
            except sqlite3.OperationalError:
                pass

            # 5. reports
            reports = s_conn.execute("SELECT * FROM reports").fetchall()
            for rep in reports:
                cursor.execute("""
                    INSERT INTO reports (
                        report_id, owner_user_id, content_hash, status, total_pages,
                        page_matching, common_render_dpi, page_size_mismatch, page_size_mismatch_details, created_at
                    ) VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE status=VALUES(status)
                """, (
                    rep["report_id"], rep["content_hash"], rep["status"], rep["total_pages"],
                    rep["page_matching"], rep["common_render_dpi"], rep["page_size_mismatch"],
                    rep["page_size_mismatch_details"], rep["created_at"]
                ))
            print(f"[Migration] Migrated {len(reports)} reports")

            # 6. report_pages
            report_pages = s_conn.execute("SELECT * FROM report_pages").fetchall()
            for rp in report_pages:
                rp_dict = dict(rp)
                cursor.execute("""
                    INSERT INTO report_pages (
                        id, report_id, page_number, matched_new_page_number, page_status,
                        page_match_method, page_match_score, comparison_mode, redesign_detected,
                        alignment_match_count, alignment_inlier_count, alignment_confidence, alignment_error,
                        render_dpi, page_size_pts_width, page_size_pts_height, page_size_mismatch,
                        page_size_mismatch_details, overall_similarity, overall_summary, changes,
                        annotated_source_png, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE page_status=VALUES(page_status)
                """, (
                    rp_dict.get("id"), rp_dict.get("report_id"), rp_dict.get("page_number"), rp_dict.get("matched_new_page_number"),
                    rp_dict.get("page_status"), rp_dict.get("page_match_method"), rp_dict.get("page_match_score"),
                    rp_dict.get("comparison_mode"), rp_dict.get("redesign_detected", 0), rp_dict.get("alignment_match_count"),
                    rp_dict.get("alignment_inlier_count"), rp_dict.get("alignment_confidence"), rp_dict.get("alignment_error"),
                    rp_dict.get("render_dpi"), rp_dict.get("page_size_pts_width"), rp_dict.get("page_size_pts_height"),
                    rp_dict.get("page_size_mismatch", 0), rp_dict.get("page_size_mismatch_details"),
                    rp_dict.get("overall_similarity"), rp_dict.get("overall_summary"), rp_dict.get("changes"),
                    rp_dict.get("annotated_source_png"), rp_dict.get("created_at")
                ))
            print(f"[Migration] Migrated {len(report_pages)} report pages")

            # 7. report_aliases
            try:
                aliases = s_conn.execute("SELECT * FROM report_aliases").fetchall()
                for a in aliases:
                    cursor.execute("""
                        INSERT INTO report_aliases (alias_id, report_id)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE report_id=VALUES(report_id)
                    """, (a["alias_id"], a["report_id"]))
                print(f"[Migration] Migrated {len(aliases)} report aliases")
            except sqlite3.OperationalError:
                pass

            # 8. jobs
            try:
                jobs = s_conn.execute("SELECT * FROM jobs").fetchall()
                for j in jobs:
                    j_dict = dict(j)
                    cursor.execute("""
                        INSERT INTO jobs (
                            job_id, owner_user_id, job_type, status, progress_message,
                            result_id, was_cached, error_message, drawing_id, created_at, updated_at
                        ) VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE status=VALUES(status)
                    """, (
                        j_dict.get("job_id"), j_dict.get("job_type"), j_dict.get("status"), j_dict.get("progress_message"),
                        j_dict.get("result_id"), j_dict.get("was_cached"), j_dict.get("error_message"),
                        j_dict.get("drawing_id"), j_dict.get("created_at"), j_dict.get("updated_at")
                    ))
                print(f"[Migration] Migrated {len(jobs)} jobs")
            except sqlite3.OperationalError:
                pass

            # 9. change_reviews
            try:
                reviews = s_conn.execute("SELECT * FROM change_reviews").fetchall()
                for r in reviews:
                    cursor.execute("""
                        INSERT INTO change_reviews (
                            review_id, report_id, page_number, change_index, status, note, reviewed_at, reviewer_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE status=VALUES(status)
                    """, (
                        r["review_id"], r["report_id"], r["page_number"], r["change_index"],
                        r["status"], r["note"], r["reviewed_at"], r["reviewer_id"]
                    ))
                print(f"[Migration] Migrated {len(reviews)} change reviews")
            except sqlite3.OperationalError:
                pass

    s_conn.close()
    print("[Migration] Migration completed successfully!")


if __name__ == "__main__":
    migrate()
