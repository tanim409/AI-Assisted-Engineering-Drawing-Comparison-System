"""Report database layer for MySQL.

Manages report schema initialization, user auth tables, and report aliases.
"""
from typing import Optional
from model.db import connect


def init_db():
    """Call once at app startup (e.g. FastAPI startup event).

    Creates tables with IF NOT EXISTS in MySQL.
    """
    with connect() as conn:
        with conn.cursor() as cursor:
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id        INT AUTO_INCREMENT PRIMARY KEY,
                    email          VARCHAR(255) NOT NULL UNIQUE,
                    password_hash  VARCHAR(255),
                    google_id      VARCHAR(255) UNIQUE,
                    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
                    INDEX idx_users_email (email),
                    INDEX idx_users_google (google_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Migration for existing databases
            try:
                cursor.execute("ALTER TABLE users MODIFY password_hash VARCHAR(255) NULL;")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE AFTER password_hash;")
            except Exception:
                pass

            # Password resets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_resets (
                    reset_token VARCHAR(255) PRIMARY KEY,
                    user_id     INT NOT NULL,
                    expires_at  DATETIME NOT NULL,
                    used        BOOLEAN NOT NULL DEFAULT FALSE,
                    INDEX idx_password_resets_user (user_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Email verifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_verifications (
                    verification_token VARCHAR(255) PRIMARY KEY,
                    user_id            INT NOT NULL,
                    expires_at         DATETIME NOT NULL,
                    used               BOOLEAN NOT NULL DEFAULT FALSE,
                    INDEX idx_email_verifications_user (user_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Report-level table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    report_id                 VARCHAR(255) PRIMARY KEY,
                    owner_user_id             INT NOT NULL,
                    content_hash              VARCHAR(255) NOT NULL,
                    status                    VARCHAR(50) NOT NULL DEFAULT 'pending',
                    total_pages               INT NOT NULL DEFAULT 0,
                    page_matching             LONGTEXT,
                    common_render_dpi         DOUBLE,
                    page_size_mismatch        BOOLEAN NOT NULL DEFAULT FALSE,
                    page_size_mismatch_details LONGTEXT,
                    created_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_owner_content_hash (owner_user_id, content_hash),
                    INDEX idx_reports_owner (owner_user_id),
                    INDEX idx_reports_status (status),
                    FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Page-level table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_pages (
                    id                          INT AUTO_INCREMENT PRIMARY KEY,
                    report_id                   VARCHAR(255) NOT NULL,
                    page_number                 INT,
                    matched_new_page_number     INT,
                    page_status                 VARCHAR(50) NOT NULL,
                    page_match_method           VARCHAR(50),
                    page_match_score            DOUBLE,
                    comparison_mode             VARCHAR(50),
                    redesign_detected           BOOLEAN NOT NULL DEFAULT FALSE,
                    alignment_match_count       INT,
                    alignment_inlier_count      INT,
                    alignment_confidence        DOUBLE,
                    alignment_error             TEXT,
                    render_dpi                  DOUBLE,
                    page_size_pts_width         DOUBLE,
                    page_size_pts_height        DOUBLE,
                    page_size_mismatch          BOOLEAN NOT NULL DEFAULT FALSE,
                    page_size_mismatch_details  LONGTEXT,
                    overall_similarity          DOUBLE,
                    overall_summary             TEXT,
                    changes                     LONGTEXT NOT NULL,
                    annotated_source_png        LONGBLOB,
                    created_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_report_pages_report (report_id),
                    FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Deduplication aliases
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_aliases (
                    alias_id  VARCHAR(255) PRIMARY KEY,
                    report_id VARCHAR(255) NOT NULL,
                    FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Async job tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id           VARCHAR(255) PRIMARY KEY,
                    owner_user_id    INT NOT NULL,
                    job_type         VARCHAR(50) NOT NULL,
                    status           VARCHAR(50) NOT NULL DEFAULT 'pending',
                    progress_message TEXT,
                    result_id        VARCHAR(255),
                    was_cached       INT,
                    error_message    TEXT,
                    drawing_id       VARCHAR(255),
                    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_jobs_owner (owner_user_id),
                    INDEX idx_jobs_status (status),
                    FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Human review data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS change_reviews (
                    review_id     VARCHAR(255) PRIMARY KEY,
                    report_id     VARCHAR(255) NOT NULL,
                    page_number   INT NOT NULL,
                    change_index  INT NOT NULL,
                    status        VARCHAR(50) NOT NULL DEFAULT 'unreviewed',
                    note          TEXT,
                    reviewed_at   DATETIME,
                    reviewer_id   VARCHAR(255),
                    UNIQUE KEY uk_report_page_change (report_id, page_number, change_index),
                    INDEX idx_change_reviews_report (report_id),
                    FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)


def resolve_report_id(report_id: str, owner_user_id: Optional[int] = None) -> str:
    """Map a report id to the underlying report id. Alias resolves to real report."""
    with connect() as conn:
        with conn.cursor() as cursor:
            if owner_user_id is not None:
                cursor.execute("""
                    SELECT ra.report_id 
                    FROM report_aliases ra
                    JOIN reports r ON r.report_id = ra.report_id
                    WHERE ra.alias_id = %s AND (r.owner_user_id IS NULL OR r.owner_user_id = %s)
                """, (report_id, owner_user_id))
            else:
                cursor.execute("SELECT report_id FROM report_aliases WHERE alias_id = %s", (report_id,))
            row = cursor.fetchone()
    return row["report_id"] if row else report_id
