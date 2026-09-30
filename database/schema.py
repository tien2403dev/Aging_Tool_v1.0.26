
from datetime import datetime
from pathlib import Path
from typing import Union

from database.connection import create_connection


# ============================================================
# SCHEMA VERSION
# ============================================================

SCHEMA_VERSION = 17

AUTO_SEND_MAIL_SCHEMA_VERSION = 12
FILTER_CACHE_SCHEMA_VERSION = 4
IMPORT_STATUS_SCHEMA_VERSION = 5
AUTO_IMPORT_SCHEMA_VERSION = 6
MAIL_PARTY_SCHEMA_VERSION = 7
MAIL_CREDENTIAL_SCHEMA_VERSION = 8
MAIL_TEMPLATE_SCHEMA_VERSION = 9
MAIL_SEND_SCHEMA_VERSION = 10
MAIL_HISTORY_SCHEMA_VERSION = 11
ALARM_TRACKING_SCHEMA_VERSION = 13
ALARM_STATUS_SCHEMA_VERSION = 14
MACHINE_SLOT_YIELD_SCHEMA_VERSION = 15
MACHINE_SLOT_YIELD_ALARM_SCHEMA_VERSION = 16
MAIL_UNIFIED_ALARM_SCHEMA_VERSION = 17


# ============================================================
# SCHEMA VERSION TABLE
# ============================================================

CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
)
"""


# ============================================================
# PRIME DATA
# ============================================================

CREATE_PRIME_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS prime_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    DATE TEXT NOT NULL
        CHECK (
            length(DATE) = 8
            AND DATE NOT GLOB '*[^0-9]*'
        ),

    TIME TEXT NOT NULL
        CHECK (
            length(TIME) = 8
            AND TIME GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]'
            AND CAST(substr(TIME, 1, 2) AS INTEGER) BETWEEN 0 AND 23
        ),

    PARTNO TEXT NOT NULL,

    LOTNO TEXT,

    INTERFACE TEXT,

    RESULT TEXT NOT NULL
        CHECK (RESULT IN ('PASS', 'FAIL')),

    SCRAPCODE TEXT,

    QTY INTEGER NOT NULL DEFAULT 1
        CHECK (
            typeof(QTY) = 'integer'
            AND QTY = 1
        ),

    EQP TEXT NOT NULL
        CHECK (length(EQP) = 7),

    Chamber INTEGER NOT NULL
        CHECK (Chamber IN (1, 2)),

    Slot INTEGER NOT NULL
        CHECK (
            typeof(Slot) = 'integer'
            AND Slot BETWEEN 1 AND 240
        ),

    MODEL TEXT NOT NULL
        CHECK (length(MODEL) = 5),

    TIER TEXT,

    CHECK (
        (
            Slot BETWEEN 1 AND 120
            AND Chamber = 1
        )
        OR
        (
            Slot BETWEEN 121 AND 240
            AND Chamber = 2
        )
    )
)
"""


# ============================================================
# CUM DATA
# ============================================================

CREATE_CUM_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS cum_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    DATE TEXT NOT NULL
        CHECK (
            length(DATE) = 8
            AND DATE NOT GLOB '*[^0-9]*'
        ),

    TIME TEXT NOT NULL
        CHECK (
            length(TIME) = 8
            AND TIME GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]'
            AND CAST(substr(TIME, 1, 2) AS INTEGER) BETWEEN 0 AND 23
        ),

    LOTID TEXT,

    PRODUCT TEXT NOT NULL,

    EQPID TEXT NOT NULL,

    INQTY INTEGER NOT NULL
        CHECK (
            typeof(INQTY) = 'integer'
            AND INQTY >= 0
        ),

    OUTQTY INTEGER NOT NULL
        CHECK (
            typeof(OUTQTY) = 'integer'
            AND OUTQTY >= 0
        ),

    FAILQTY INTEGER NOT NULL
        CHECK (
            typeof(FAILQTY) = 'integer'
            AND FAILQTY >= 0
        ),

    YIELD REAL NOT NULL
        CHECK (
            typeof(YIELD) IN ('integer', 'real')
        ),

    SCRAP TEXT NOT NULL DEFAULT '',

    MODEL TEXT NOT NULL
        CHECK (length(MODEL) = 5),

    TIER TEXT NOT NULL
)
"""


# ============================================================
# CUM SCRAP DETAIL
# ============================================================

CREATE_CUM_SCRAP_DETAIL_TABLE = """
CREATE TABLE IF NOT EXISTS cum_scrap_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    cum_data_id INTEGER NOT NULL,

    scrap_code TEXT NOT NULL
        CHECK (
            length(scrap_code) = 4
            AND scrap_code NOT GLOB '*[^0-9]*'
        ),

    qty INTEGER NOT NULL
        CHECK (
            typeof(qty) = 'integer'
            AND qty BETWEEN 1 AND 99
        ),

    FOREIGN KEY (cum_data_id)
        REFERENCES cum_data(id)
        ON DELETE CASCADE,

    UNIQUE (
        cum_data_id,
        scrap_code
    )
)
"""


# ============================================================
# SLOT FAIL ALARM
# ============================================================

CREATE_SLOT_FAIL_ALARM_TABLE = """
CREATE TABLE IF NOT EXISTS slot_fail_alarm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    alarm_date TEXT NOT NULL
        CHECK (
            length(alarm_date) = 8
            AND alarm_date NOT GLOB '*[^0-9]*'
        ),

    eqp TEXT NOT NULL,

    chamber INTEGER NOT NULL
        CHECK (chamber IN (1, 2)),

    slot INTEGER NOT NULL
        CHECK (slot BETWEEN 1 AND 240),

    start_prime_id INTEGER NOT NULL,
    end_prime_id INTEGER NOT NULL,

    start_datetime TEXT NOT NULL,
    end_datetime TEXT NOT NULL,

    fail_qty INTEGER NOT NULL
        CHECK (fail_qty >= 2),

    scrap_codes TEXT NOT NULL DEFAULT '',
    models TEXT NOT NULL DEFAULT '',
    lotids TEXT NOT NULL DEFAULT '',

    UNIQUE (
        eqp,
        chamber,
        slot,
        start_prime_id,
        end_prime_id
    )
)
"""


# ============================================================
# MACHINE SLOT YIELD TARGET
# ============================================================

CREATE_MACHINE_SLOT_YIELD_TARGET_TABLE = """
CREATE TABLE IF NOT EXISTS machine_slot_yield_target (
    id INTEGER PRIMARY KEY
        CHECK (id = 1),

    target_15 REAL NOT NULL DEFAULT 95.0
        CHECK (
            target_15 >= 0
            AND target_15 <= 100
        ),

    target_30 REAL NOT NULL DEFAULT 95.0
        CHECK (
            target_30 >= 0
            AND target_30 <= 100
        ),

    updated_at TEXT NOT NULL
)
"""


# ============================================================
# MACHINE SLOT YIELD ALARM
# ============================================================

CREATE_MACHINE_SLOT_YIELD_ALARM_TABLE = """
CREATE TABLE IF NOT EXISTS machine_slot_yield_alarm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    alarm_date TEXT NOT NULL,

    machine TEXT NOT NULL,

    slot INTEGER NOT NULL,

    start_datetime TEXT NOT NULL DEFAULT '',

    end_datetime TEXT NOT NULL DEFAULT '',

    yield_15 REAL,

    target_15 REAL NOT NULL DEFAULT 0,

    yield_30 REAL,

    target_30 REAL NOT NULL DEFAULT 0,

    total_test INTEGER NOT NULL DEFAULT 0,

    pass_count INTEGER NOT NULL DEFAULT 0,

    fail_count INTEGER NOT NULL DEFAULT 0,

    yield_percent REAL,

    reason TEXT NOT NULL DEFAULT '',

    scrap_codes TEXT NOT NULL DEFAULT '',

    model TEXT NOT NULL DEFAULT '',

    status TEXT NOT NULL DEFAULT 'Chưa tiến hành',

    date_complete TEXT NOT NULL DEFAULT '',

    quick_check_result TEXT NOT NULL DEFAULT '',

    cal_check_result TEXT NOT NULL DEFAULT '',

    engineer_action TEXT NOT NULL DEFAULT '',

    monitor_day1 TEXT NOT NULL DEFAULT '',

    monitor_day2 TEXT NOT NULL DEFAULT '',

    monitor_day3 TEXT NOT NULL DEFAULT '',

    comment TEXT NOT NULL DEFAULT '',

    engineer TEXT NOT NULL DEFAULT '',

    created_at TEXT NOT NULL,

    updated_at TEXT NOT NULL,

    UNIQUE (
        alarm_date,
        machine,
        slot
    )
)
"""


# ============================================================
# IMPORT LOCK
# ============================================================

CREATE_IMPORT_LOCK_TABLE = """
CREATE TABLE IF NOT EXISTS import_lock (
    lock_name TEXT PRIMARY KEY
        CHECK (lock_name = 'GLOBAL_IMPORT_LOCK'),

    batch_id TEXT NOT NULL,

    import_type TEXT NOT NULL
        CHECK (import_type IN ('PRIME', 'CUM')),

    file_name TEXT NOT NULL,

    machine_name TEXT NOT NULL,

    windows_user TEXT NOT NULL,

    process_id INTEGER NOT NULL,

    acquired_at TEXT NOT NULL,

    heartbeat_at TEXT NOT NULL,

    expires_at TEXT NOT NULL
)
"""


# ============================================================
# DATA IMPORT STATUS
# ============================================================

CREATE_DATA_IMPORT_STATUS_TABLE = """
CREATE TABLE IF NOT EXISTS data_import_status (
    data_type TEXT NOT NULL
        CHECK (data_type IN ('PRIME', 'CUM')),

    data_date TEXT NOT NULL
        CHECK (
            length(data_date) = 8
            AND data_date NOT GLOB '*[^0-9]*'
        ),

    load_time TEXT NOT NULL,

    PRIMARY KEY (
        data_type,
        data_date
    )
) WITHOUT ROWID
"""


# ============================================================
# AUTO IMPORT
# ============================================================

CREATE_AUTO_IMPORT_SCHEDULER_TABLE = """
CREATE TABLE IF NOT EXISTS auto_import_scheduler (
    id INTEGER PRIMARY KEY
        CHECK (id = 1),

    enable_auto_import INTEGER NOT NULL DEFAULT 0
        CHECK (enable_auto_import IN (0, 1)),

    import_time TEXT NOT NULL DEFAULT '03:00'
        CHECK (
            length(import_time) = 5
            AND import_time GLOB '[0-2][0-9]:[0-5][0-9]'
            AND CAST(substr(import_time, 1, 2) AS INTEGER)
                BETWEEN 0 AND 23
        ),

    log_folder TEXT NOT NULL DEFAULT '',

    last_import_date TEXT
        CHECK (
            last_import_date IS NULL
            OR (
                length(last_import_date) = 8
                AND last_import_date NOT GLOB '*[^0-9]*'
            )
        )
)
"""


# ============================================================
# MAIL SENDER
# ============================================================

CREATE_MAIL_SENDER_TABLE = """
CREATE TABLE IF NOT EXISTS mail_sender (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id TEXT NOT NULL
        COLLATE NOCASE,

    display_name TEXT NOT NULL,

    password TEXT NOT NULL,

    enabled INTEGER NOT NULL DEFAULT 0
        CHECK (enabled IN (0, 1)),

    created_at TEXT NOT NULL,

    updated_at TEXT NOT NULL,

    UNIQUE (user_id)
)
"""


# ============================================================
# MAIL RECIPIENT
# ============================================================

CREATE_MAIL_RECIPIENT_TABLE = """
CREATE TABLE IF NOT EXISTS mail_recipient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id TEXT NOT NULL
        COLLATE NOCASE,

    display_name TEXT NOT NULL,

    recipient_type TEXT NOT NULL DEFAULT 'NONE'
        CHECK (
            recipient_type IN (
                'RECEIVER',
                'CC',
                'NONE'
            )
        ),

    created_at TEXT NOT NULL,

    updated_at TEXT NOT NULL,

    UNIQUE (user_id)
)
"""


# ============================================================
# MAIL TEMPLATE
# ============================================================

CREATE_MAIL_TEMPLATE_TABLE = """
CREATE TABLE IF NOT EXISTS mail_template (
    id INTEGER PRIMARY KEY
        CHECK (id = 1),

    subject TEXT NOT NULL
        CHECK (length(trim(subject)) > 0),

    heading TEXT NOT NULL DEFAULT '',

    closing TEXT NOT NULL DEFAULT ''
)
"""


# ============================================================
# MAIL SLOT SEND HISTORY - V17
# ============================================================

CREATE_MAIL_SLOT_SEND_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS mail_slot_send_history (
    alarm_date TEXT NOT NULL
        CHECK (
            length(alarm_date) = 8
            AND alarm_date NOT GLOB '*[^0-9]*'
        ),

    alarm_type TEXT NOT NULL
        CHECK (
            alarm_type IN (
                'SLOT_FAIL',
                'MACHINE_SLOT_YIELD'
            )
        ),

    eqp TEXT NOT NULL DEFAULT '',

    machine TEXT NOT NULL DEFAULT '',

    slot INTEGER NOT NULL
        CHECK (
            typeof(slot) = 'integer'
            AND slot BETWEEN 1 AND 240
        ),

    sent_at TEXT NOT NULL,

    PRIMARY KEY (
        alarm_date,
        alarm_type,
        eqp,
        machine,
        slot
    )
) WITHOUT ROWID
"""


# ============================================================
# MAIL SEND LOCK
# ============================================================

CREATE_MAIL_SEND_LOCK_TABLE = """
CREATE TABLE IF NOT EXISTS mail_send_lock (
    id INTEGER PRIMARY KEY
        CHECK (id = 1),

    lock_token TEXT NOT NULL,

    expires_at TEXT NOT NULL
)
"""


# ============================================================
# MAIL SEND HISTORY
# ============================================================

CREATE_MAIL_SEND_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS mail_send_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    alarm_date TEXT NOT NULL
        CHECK (
            length(alarm_date) = 8
            AND alarm_date NOT GLOB '*[^0-9]*'
        ),

    sent_at TEXT NOT NULL,

    sender TEXT NOT NULL,

    receivers TEXT NOT NULL,

    cc TEXT NOT NULL DEFAULT '',

    result TEXT NOT NULL DEFAULT 'Success'
        CHECK (result = 'Success'),

    subject TEXT NOT NULL,

    html_content TEXT NOT NULL
)
"""


# ============================================================
# AUTO SEND MAIL
# ============================================================

CREATE_AUTO_SEND_MAIL_SCHEDULER_TABLE = """
CREATE TABLE IF NOT EXISTS auto_send_mail_scheduler (
    id INTEGER PRIMARY KEY
        CHECK (id = 1),

    enable_auto_send INTEGER NOT NULL DEFAULT 0
        CHECK (enable_auto_send IN (0, 1)),

    send_time TEXT NOT NULL DEFAULT '08:00'
        CHECK (
            length(send_time) = 5
            AND send_time GLOB '[0-2][0-9]:[0-5][0-9]'
            AND CAST(
                substr(send_time, 1, 2)
                AS INTEGER
            ) BETWEEN 0 AND 23
        )
)
"""


# ============================================================
# FILTER CACHE
# ============================================================

CREATE_FILTER_EQP_OPTION_TABLE = """
CREATE TABLE IF NOT EXISTS filter_eqp_option (
    eqp TEXT PRIMARY KEY,

    row_count INTEGER NOT NULL
        CHECK (row_count >= 0)
)
"""


CREATE_FILTER_CHAMBER_OPTION_TABLE = """
CREATE TABLE IF NOT EXISTS filter_chamber_option (
    chamber INTEGER PRIMARY KEY
        CHECK (chamber IN (1, 2)),

    row_count INTEGER NOT NULL
        CHECK (row_count >= 0)
)
"""


CREATE_FILTER_SCRAP_CODE_OPTION_TABLE = """
CREATE TABLE IF NOT EXISTS filter_scrap_code_option (
    scrap_code TEXT PRIMARY KEY,

    prime_row_count INTEGER NOT NULL DEFAULT 0
        CHECK (prime_row_count >= 0),

    cum_row_count INTEGER NOT NULL DEFAULT 0
        CHECK (cum_row_count >= 0)
)
"""


CREATE_FILTER_MODEL_OPTION_TABLE = """
CREATE TABLE IF NOT EXISTS filter_model_option (
    model TEXT PRIMARY KEY,

    row_count INTEGER NOT NULL
        CHECK (row_count >= 0)
)
"""


# ============================================================
# INDEXES
#
# QUAN TRỌNG:
# Không tạo index mail_slot_send_history ở đây.
# Vì database cũ chưa có alarm_type.
#
# Index Mail V17 sẽ được tạo SAU KHI migration.
# ============================================================

CREATE_INDEXES = (
    """
    CREATE INDEX IF NOT EXISTS idx_prime_data_date
    ON prime_data (DATE)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_data_date
    ON cum_data (DATE)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_scrap_detail_code
    ON cum_scrap_detail (
        scrap_code,
        cum_data_id
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_data_date_tier
    ON prime_data (DATE, TIER)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_data_date_lotno
    ON prime_data (DATE, LOTNO)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_data_date_tier
    ON cum_data (DATE, TIER)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_data_date_lotid_tier
    ON cum_data (DATE, LOTID, TIER)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_data_eqpid_date_tier
    ON cum_data (
        EQPID,
        DATE,
        TIER
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_data_eqp_date_tier
    ON prime_data (
        EQP,
        DATE,
        TIER
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_data_tier_date_eqp_result
    ON prime_data (
        TIER,
        DATE,
        EQP,
        RESULT
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_data_tier_date_eqp_scrap_fail
    ON prime_data (
        TIER,
        DATE,
        EQP,
        SCRAPCODE
    )
    WHERE RESULT = 'FAIL'
      AND SCRAPCODE <> ''
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_data_tier_date_eqpid_qty
    ON cum_data (
        TIER,
        DATE,
        EQPID,
        INQTY,
        OUTQTY
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_yield_slot_scrap_cover
    ON prime_data (
        EQP,
        Chamber,
        TIER,
        DATE,
        Slot,
        RESULT,
        SCRAPCODE
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_data_tier_date_eqp_model_result
    ON prime_data (
        TIER,
        DATE,
        EQP,
        MODEL,
        RESULT
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_model_scrap_cover
    ON prime_data (
        TIER,
        DATE,
        MODEL,
        SCRAPCODE,
        RESULT
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_import_match
    ON prime_data (
        DATE,
        EQP,
        TIME,
        Slot
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_data_date_lotid_tier
    ON cum_data (
        DATE,
        LOTID,
        TIER
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_cum_data_lotid_date_tier
    ON cum_data (
        LOTID,
        DATE,
        TIER
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_alarm_event_order
    ON prime_data (
        EQP,
        Chamber,
        Slot,
        DATE,
        TIME,
        id
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_prime_fail_history
    ON prime_data (
        EQP,
        Chamber,
        Slot,
        DATE,
        TIME
    )
    WHERE RESULT = 'FAIL'
      AND TIER IS NOT NULL
      AND TIER <> '2'
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_slot_fail_alarm_date
    ON slot_fail_alarm (
        alarm_date,
        end_datetime
    )
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS
    ux_mail_sender_single_enabled
    ON mail_sender (enabled)
    WHERE enabled = 1
    """,

    """
    CREATE INDEX IF NOT EXISTS
    idx_mail_recipient_type
    ON mail_recipient (
        recipient_type,
        display_name
    )
    """,
)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def _ensure_mail_template_columns(connection) -> None:
    """
    Bảo đảm database cũ vẫn có đầy đủ cột Mail Template.

    Một số database cũ đã có bảng ``mail_template`` nhưng chỉ có
    cột ``subject``. Khi schema_version đã ở v9/v17, câu lệnh
    CREATE TABLE IF NOT EXISTS không bổ sung cột mới. Khi đó
    sqlite3.Row truy cập row["heading"] / row["closing"] sẽ báo:
        No item with that key

    Hàm này chạy mỗi lần khởi động và chỉ bổ sung cột còn thiếu,
    không xóa hay thay đổi dữ liệu template hiện có.
    """

    columns = {
        str(row[1]).lower()
        for row in connection.execute(
            "PRAGMA table_info(mail_template)"
        ).fetchall()
    }

    if "subject" not in columns:
        connection.execute(
            "ALTER TABLE mail_template ADD COLUMN subject TEXT NOT NULL DEFAULT ''"
        )

    if "heading" not in columns:
        connection.execute(
            "ALTER TABLE mail_template ADD COLUMN heading TEXT NOT NULL DEFAULT ''"
        )

    if "closing" not in columns:
        connection.execute(
            "ALTER TABLE mail_template ADD COLUMN closing TEXT NOT NULL DEFAULT ''"
        )


def initialize_database(
    database_path: Union[str, Path],
) -> None:
    """
    Tạo database và các bảng nếu chưa tồn tại.

    Không xóa dữ liệu cũ.

    Schema hiện tại:
        v17

    v17 hỗ trợ Mail cho:
        - Slot Fail Alarm
        - Machine Slot Yield Alarm
    """

    connection = create_connection(database_path)

    try:
        connection.execute("BEGIN IMMEDIATE")

        # ----------------------------------------------------
        # Schema Version
        # ----------------------------------------------------

        connection.execute(
            CREATE_SCHEMA_VERSION_TABLE
        )

        # ----------------------------------------------------
        # Core
        # ----------------------------------------------------

        connection.execute(
            CREATE_PRIME_DATA_TABLE
        )

        connection.execute(
            CREATE_CUM_DATA_TABLE
        )

        connection.execute(
            CREATE_CUM_SCRAP_DETAIL_TABLE
        )

        # ----------------------------------------------------
        # Alarm
        # ----------------------------------------------------

        connection.execute(
            CREATE_SLOT_FAIL_ALARM_TABLE
        )

        connection.execute(
            CREATE_MACHINE_SLOT_YIELD_TARGET_TABLE
        )

        connection.execute(
            CREATE_MACHINE_SLOT_YIELD_ALARM_TABLE
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO machine_slot_yield_target (
                id,
                target_15,
                target_30,
                updated_at
            )
            VALUES (
                1,
                95.0,
                95.0,
                ?
            )
            """,
            (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ),
        )

        # ----------------------------------------------------
        # Import
        # ----------------------------------------------------

        connection.execute(
            CREATE_IMPORT_LOCK_TABLE
        )

        connection.execute(
            CREATE_DATA_IMPORT_STATUS_TABLE
        )

        connection.execute(
            CREATE_AUTO_IMPORT_SCHEDULER_TABLE
        )

        # ----------------------------------------------------
        # Mail
        # ----------------------------------------------------

        connection.execute(
            CREATE_MAIL_SENDER_TABLE
        )

        connection.execute(
            CREATE_MAIL_RECIPIENT_TABLE
        )

        connection.execute(
            CREATE_MAIL_TEMPLATE_TABLE
        )

        # ----------------------------------------------------
        # Repair old Mail Template schema
        # ----------------------------------------------------
        # CREATE TABLE IF NOT EXISTS không bổ sung cột cho
        # database cũ. Bắt buộc kiểm tra trước khi đọc template.
        _ensure_mail_template_columns(
            connection
        )

        connection.execute(
            CREATE_MAIL_SLOT_SEND_HISTORY_TABLE
        )

        connection.execute(
            CREATE_MAIL_SEND_LOCK_TABLE
        )

        connection.execute(
            CREATE_MAIL_SEND_HISTORY_TABLE
        )

        connection.execute(
            CREATE_AUTO_SEND_MAIL_SCHEDULER_TABLE
        )

        # ----------------------------------------------------
        # Default Mail Template
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT OR IGNORE INTO mail_template (
                id,
                subject,
                heading,
                closing
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                1,
                "KTSP SSD gửi bộ phận KTTB",
                (
                    "KTSP SSD nhờ KTTB "
                    "kiểm tra các slot sau"
                ),
                "",
            ),
        )

        # ----------------------------------------------------
        # Default Auto Send Mail
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT OR IGNORE INTO auto_send_mail_scheduler (
                id,
                enable_auto_send,
                send_time
            )
            VALUES (1, 0, '07:00')
            """
        )

        # ----------------------------------------------------
        # Default Auto Import
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT OR IGNORE INTO auto_import_scheduler (
                id,
                enable_auto_import,
                import_time,
                log_folder,
                last_import_date
            )
            VALUES (
                1,
                0,
                '03:00',
                '',
                NULL
            )
            """
        )

        # ----------------------------------------------------
        # Filter cache
        # ----------------------------------------------------

        connection.execute(
            CREATE_FILTER_EQP_OPTION_TABLE
        )

        connection.execute(
            CREATE_FILTER_CHAMBER_OPTION_TABLE
        )

        connection.execute(
            CREATE_FILTER_SCRAP_CODE_OPTION_TABLE
        )

        connection.execute(
            CREATE_FILTER_MODEL_OPTION_TABLE
        )

        # ----------------------------------------------------
        # MIGRATION PHẢI CHẠY TRƯỚC INDEX
        # ----------------------------------------------------

        _apply_schema_migrations(
            connection
        )

        # ----------------------------------------------------
        # Indexes
        # ----------------------------------------------------

        for sql in CREATE_INDEXES:
            connection.execute(sql)

        # ----------------------------------------------------
        # Mail Unified Alarm Index - V17
        #
        # Được tạo SAU migration.
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_mail_slot_send_history_lookup
            ON mail_slot_send_history (
                alarm_date,
                alarm_type,
                eqp,
                machine,
                slot
            )
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ============================================================
# APPLY MIGRATIONS
# ============================================================

def _apply_schema_migrations(
    connection,
) -> None:
    """
    Áp dụng migration còn thiếu theo đúng phiên bản.

    Đặc biệt V17:
    Nếu schema_version đã là 17 nhưng bảng
    mail_slot_send_history vẫn là schema cũ,
    migration vẫn được chạy.
    """

    row = connection.execute(
        """
        SELECT COALESCE(MAX(version), 0)
        FROM schema_version
        """
    ).fetchone()

    current_version = int(row[0])

    # --------------------------------------------------------
    # V4
    # --------------------------------------------------------

    if current_version < FILTER_CACHE_SCHEMA_VERSION:

        _rebuild_filter_option_cache(
            connection
        )

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                FILTER_CACHE_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                (
                    "Add filter option cache tables "
                    "and rebuild existing options"
                ),
            ),
        )

        current_version = FILTER_CACHE_SCHEMA_VERSION

    # --------------------------------------------------------
    # V5
    # --------------------------------------------------------

    if current_version < IMPORT_STATUS_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                IMPORT_STATUS_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Add data import status metadata table",
            ),
        )

        current_version = IMPORT_STATUS_SCHEMA_VERSION

    # --------------------------------------------------------
    # V6
    # --------------------------------------------------------

    if current_version < AUTO_IMPORT_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                AUTO_IMPORT_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Add auto import scheduler configuration table",
            ),
        )

        current_version = AUTO_IMPORT_SCHEMA_VERSION

    # --------------------------------------------------------
    # V7
    # --------------------------------------------------------

    if current_version < MAIL_PARTY_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                MAIL_PARTY_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Add mail sender and mail recipient tables",
            ),
        )

        current_version = MAIL_PARTY_SCHEMA_VERSION

    # --------------------------------------------------------
    # V8
    # --------------------------------------------------------

    if current_version < MAIL_CREDENTIAL_SCHEMA_VERSION:

        _migrate_mail_configuration_v8(
            connection
        )

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                MAIL_CREDENTIAL_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                (
                    "Add sender password and remove "
                    "recipient department"
                ),
            ),
        )

        current_version = MAIL_CREDENTIAL_SCHEMA_VERSION

    # --------------------------------------------------------
    # V9
    # --------------------------------------------------------

    if current_version < MAIL_TEMPLATE_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                MAIL_TEMPLATE_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Add mail template table",
            ),
        )

        current_version = MAIL_TEMPLATE_SCHEMA_VERSION

    # --------------------------------------------------------
    # V10
    # --------------------------------------------------------

    if current_version < MAIL_SEND_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                MAIL_SEND_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Add mail slot send history table",
            ),
        )

        current_version = MAIL_SEND_SCHEMA_VERSION

    # --------------------------------------------------------
    # V11
    # --------------------------------------------------------

    if current_version < MAIL_HISTORY_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                MAIL_HISTORY_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Add successful mail history table",
            ),
        )

        current_version = MAIL_HISTORY_SCHEMA_VERSION

    # --------------------------------------------------------
    # V12
    # --------------------------------------------------------

    if current_version < AUTO_SEND_MAIL_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                AUTO_SEND_MAIL_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Add auto send mail scheduler table",
            ),
        )

        current_version = AUTO_SEND_MAIL_SCHEMA_VERSION

    # --------------------------------------------------------
    # V13
    # --------------------------------------------------------

    if current_version < ALARM_TRACKING_SCHEMA_VERSION:

        _migrate_alarm_tracking_v13(
            connection
        )

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                ALARM_TRACKING_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                (
                    "Add alarm status, completion "
                    "datetime and engineer"
                ),
            ),
        )

        current_version = ALARM_TRACKING_SCHEMA_VERSION

    # --------------------------------------------------------
    # V14
    # --------------------------------------------------------

    if current_version < ALARM_STATUS_SCHEMA_VERSION:

        _migrate_alarm_status_v14(
            connection
        )

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                ALARM_STATUS_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Rename completed alarm status",
            ),
        )

        current_version = ALARM_STATUS_SCHEMA_VERSION

    # --------------------------------------------------------
    # V15
    # --------------------------------------------------------

    if current_version < MACHINE_SLOT_YIELD_SCHEMA_VERSION:

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                MACHINE_SLOT_YIELD_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                (
                    "Add Machine Slot Yield "
                    "15/30 test target configuration"
                ),
            ),
        )

        current_version = MACHINE_SLOT_YIELD_SCHEMA_VERSION

    # --------------------------------------------------------
    # V16
    # --------------------------------------------------------

    if current_version < MACHINE_SLOT_YIELD_ALARM_SCHEMA_VERSION:

        columns = {
            str(row["name"])
            for row in connection.execute(
                "PRAGMA table_info(machine_slot_yield_alarm)"
            ).fetchall()
        }

        additions = {
            "scrap_codes": "TEXT NOT NULL DEFAULT ''",
            "model": "TEXT NOT NULL DEFAULT ''",
            "quick_check_result": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "cal_check_result": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "engineer_action": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "monitor_day1": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "monitor_day2": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "monitor_day3": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "comment": (
                "TEXT NOT NULL DEFAULT ''"
            ),
        }

        for name, definition in additions.items():

            if name not in columns:

                connection.execute(
                    f"""
                    ALTER TABLE machine_slot_yield_alarm
                    ADD COLUMN {name} {definition}
                    """
                )

        connection.execute(
            """
            INSERT INTO schema_version (
                version,
                applied_at,
                description
            )
            VALUES (?, ?, ?)
            """,
            (
                MACHINE_SLOT_YIELD_ALARM_SCHEMA_VERSION,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                (
                    "Add Machine Slot Yield Alarm "
                    "improvement tracking"
                ),
            ),
        )

        current_version = (
            MACHINE_SLOT_YIELD_ALARM_SCHEMA_VERSION
        )

    # --------------------------------------------------------
    # V17 - UNIFIED MAIL ALARM
    # --------------------------------------------------------

    mail_history_columns = {
        str(row["name"])
        for row in connection.execute(
            """
            PRAGMA table_info(mail_slot_send_history)
            """
        ).fetchall()
    }

    required_mail_history_columns = {
        "alarm_date",
        "alarm_type",
        "eqp",
        "machine",
        "slot",
        "sent_at",
    }

    mail_history_v17_ready = (
        required_mail_history_columns
        .issubset(mail_history_columns)
    )

    # QUAN TRỌNG:
    #
    # Không chỉ kiểm tra version.
    #
    # Nếu lần trước version 17 đã được ghi nhưng
    # migration thực tế chưa hoàn thành thì vẫn phải
    # sửa lại bảng.
    if (
        current_version < MAIL_UNIFIED_ALARM_SCHEMA_VERSION
        or not mail_history_v17_ready
    ):

        _migrate_mail_unified_alarm_v17(
            connection
        )

        # Chỉ ghi version nếu version 17 chưa tồn tại.
        if current_version < MAIL_UNIFIED_ALARM_SCHEMA_VERSION:

            connection.execute(
                """
                INSERT INTO schema_version (
                    version,
                    applied_at,
                    description
                )
                VALUES (?, ?, ?)
                """,
                (
                    MAIL_UNIFIED_ALARM_SCHEMA_VERSION,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    (
                        "Unify Mail send history for "
                        "Slot Fail Alarm and "
                        "Machine Slot Yield Alarm"
                    ),
                ),
            )

        current_version = (
            MAIL_UNIFIED_ALARM_SCHEMA_VERSION
        )


# ============================================================
# MIGRATION V17
# ============================================================

def _migrate_mail_unified_alarm_v17(
    connection,
) -> None:
    """
    Chuyển mail_slot_send_history cũ sang schema v17.

    Cũ:
        alarm_date
        eqp
        slot
        sent_at

    Mới:
        alarm_date
        alarm_type
        eqp
        machine
        slot
        sent_at
    """

    # --------------------------------------------------------
    # Đọc cấu trúc thực tế
    # --------------------------------------------------------

    table_info = connection.execute(
        """
        PRAGMA table_info(mail_slot_send_history)
        """
    ).fetchall()

    # --------------------------------------------------------
    # Nếu bảng chưa tồn tại
    # --------------------------------------------------------

    if not table_info:

        connection.execute(
            CREATE_MAIL_SLOT_SEND_HISTORY_TABLE
        )

        return

    columns = {
        str(row["name"])
        for row in table_info
    }

    required_columns = {
        "alarm_date",
        "alarm_type",
        "eqp",
        "machine",
        "slot",
        "sent_at",
    }

    # --------------------------------------------------------
    # Nếu bảng đã đúng V17
    # --------------------------------------------------------

    if required_columns.issubset(columns):
        return

    # --------------------------------------------------------
    # Backup bảng cũ
    # --------------------------------------------------------

    connection.execute(
        """
        DROP TABLE IF EXISTS
        mail_slot_send_history_v16
        """
    )

    connection.execute(
        """
        ALTER TABLE mail_slot_send_history
        RENAME TO mail_slot_send_history_v16
        """
    )

    # --------------------------------------------------------
    # Tạo bảng V17
    # --------------------------------------------------------

    connection.execute(
        CREATE_MAIL_SLOT_SEND_HISTORY_TABLE
    )

    # --------------------------------------------------------
    # Đọc cấu trúc bảng cũ
    # --------------------------------------------------------

    old_columns = {
        str(row["name"])
        for row in connection.execute(
            """
            PRAGMA table_info(
                mail_slot_send_history_v16
            )
            """
        ).fetchall()
    }

    # --------------------------------------------------------
    # Chuyển dữ liệu cũ
    #
    # Dữ liệu cũ mặc định là SLOT_FAIL.
    # --------------------------------------------------------

    if {
        "alarm_date",
        "eqp",
        "slot",
        "sent_at",
    }.issubset(old_columns):

        connection.execute(
            """
            INSERT OR IGNORE INTO
            mail_slot_send_history (
                alarm_date,
                alarm_type,
                eqp,
                machine,
                slot,
                sent_at
            )
            SELECT
                alarm_date,
                'SLOT_FAIL',
                COALESCE(eqp, ''),
                '',
                slot,
                sent_at
            FROM mail_slot_send_history_v16
            """
        )

    # --------------------------------------------------------
    # Xóa backup
    # --------------------------------------------------------

    connection.execute(
        """
        DROP TABLE mail_slot_send_history_v16
        """
    )


# ============================================================
# MIGRATION V13
# ============================================================

def _migrate_alarm_tracking_v13(
    connection,
) -> None:

    duplicate = connection.execute(
        """
        SELECT
            alarm_date,
            eqp,
            chamber,
            slot,
            COUNT(*) AS qty
        FROM slot_fail_alarm
        GROUP BY
            alarm_date,
            eqp,
            chamber,
            slot
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).fetchone()

    if duplicate is not None:

        raise ValueError(
            "Không thể nâng cấp Alarm: "
            "trùng khóa ngày/EQP/chamber/slot: "
            f"{tuple(duplicate)}. "
            "Dữ liệu được giữ nguyên; "
            "cần kiểm tra khóa trùng."
        )

    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(slot_fail_alarm)"
        )
    }

    additions = {
        "status": (
            "TEXT NOT NULL "
            "DEFAULT 'Chưa tiến hành' "
            "CHECK ("
            "status IN ("
            "'Chưa tiến hành', "
            "'Đang tiến hành', "
            "'Đã hoàn thành'"
            ")"
            ")"
        ),
        "date_complete": (
            "TEXT NOT NULL DEFAULT ''"
        ),
        "engineer": (
            "TEXT NOT NULL DEFAULT ''"
        ),
    }

    for name, definition in additions.items():

        if name not in columns:

            connection.execute(
                f"""
                ALTER TABLE slot_fail_alarm
                ADD COLUMN {name} {definition}
                """
            )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_alarm_day_slot
        ON slot_fail_alarm (
            alarm_date,
            eqp,
            chamber,
            slot
        )
        """
    )


# ============================================================
# MIGRATION V14
# ============================================================

def _migrate_alarm_status_v14(
    connection,
) -> None:
    """
    Đổi status Đã tiến hành thành Đã hoàn thành.
    """

    connection.execute(
        """
        ALTER TABLE slot_fail_alarm
        RENAME TO slot_fail_alarm_v13
        """
    )

    connection.execute(
        """
        CREATE TABLE slot_fail_alarm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            alarm_date TEXT NOT NULL
                CHECK (
                    length(alarm_date) = 8
                    AND alarm_date NOT GLOB '*[^0-9]*'
                ),

            eqp TEXT NOT NULL,

            chamber INTEGER NOT NULL
                CHECK (chamber IN (1, 2)),

            slot INTEGER NOT NULL
                CHECK (slot BETWEEN 1 AND 240),

            start_prime_id INTEGER NOT NULL,

            end_prime_id INTEGER NOT NULL,

            start_datetime TEXT NOT NULL,

            end_datetime TEXT NOT NULL,

            fail_qty INTEGER NOT NULL
                CHECK (fail_qty >= 2),

            scrap_codes TEXT NOT NULL DEFAULT '',

            models TEXT NOT NULL DEFAULT '',

            lotids TEXT NOT NULL DEFAULT '',

            status TEXT NOT NULL
                DEFAULT 'Chưa tiến hành'
                CHECK (
                    status IN (
                        'Chưa tiến hành',
                        'Đang tiến hành',
                        'Đã hoàn thành'
                    )
                ),

            date_complete TEXT NOT NULL DEFAULT '',

            engineer TEXT NOT NULL DEFAULT '',

            UNIQUE (
                eqp,
                chamber,
                slot,
                start_prime_id,
                end_prime_id
            )
        )
        """
    )

    connection.execute(
        """
        INSERT INTO slot_fail_alarm (
            id,
            alarm_date,
            eqp,
            chamber,
            slot,
            start_prime_id,
            end_prime_id,
            start_datetime,
            end_datetime,
            fail_qty,
            scrap_codes,
            models,
            lotids,
            status,
            date_complete,
            engineer
        )
        SELECT
            id,
            alarm_date,
            eqp,
            chamber,
            slot,
            start_prime_id,
            end_prime_id,
            start_datetime,
            end_datetime,
            fail_qty,
            scrap_codes,
            models,
            lotids,
            CASE
                WHEN status = 'Đã tiến hành'
                    THEN 'Đã hoàn thành'
                ELSE status
            END,
            date_complete,
            engineer
        FROM slot_fail_alarm_v13
        """
    )

    connection.execute(
        """
        DROP TABLE slot_fail_alarm_v13
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_slot_fail_alarm_date
        ON slot_fail_alarm (
            alarm_date,
            end_datetime
        )
        """
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_alarm_day_slot
        ON slot_fail_alarm (
            alarm_date,
            eqp,
            chamber,
            slot
        )
        """
    )


# ============================================================
# MIGRATION V8 - MAIL CONFIGURATION
# ============================================================

def _migrate_mail_configuration_v8(
    connection,
) -> None:
    """
    Thêm password cho Sender và loại bỏ
    department khỏi Receiver.
    """

    sender_columns = {
        str(row["name"])
        for row in connection.execute(
            "PRAGMA table_info(mail_sender)"
        ).fetchall()
    }

    if "password" not in sender_columns:

        connection.execute(
            """
            ALTER TABLE mail_sender
            ADD COLUMN password TEXT
                NOT NULL DEFAULT ''
            """
        )

    recipient_columns = {
        str(row["name"])
        for row in connection.execute(
            "PRAGMA table_info(mail_recipient)"
        ).fetchall()
    }

    if "department" not in recipient_columns:
        return

    connection.execute(
        """
        DROP TABLE IF EXISTS mail_recipient_v8
        """
    )

    connection.execute(
        """
        CREATE TABLE mail_recipient_v8 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id TEXT NOT NULL
                COLLATE NOCASE,

            display_name TEXT NOT NULL,

            recipient_type TEXT NOT NULL
                DEFAULT 'NONE'
                CHECK (
                    recipient_type IN (
                        'RECEIVER',
                        'CC',
                        'NONE'
                    )
                ),

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            UNIQUE (user_id)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO mail_recipient_v8 (
            id,
            user_id,
            display_name,
            recipient_type,
            created_at,
            updated_at
        )
        SELECT
            id,
            user_id,
            display_name,
            recipient_type,
            created_at,
            updated_at
        FROM mail_recipient
        """
    )

    connection.execute(
        """
        DROP TABLE mail_recipient
        """
    )

    connection.execute(
        """
        ALTER TABLE mail_recipient_v8
        RENAME TO mail_recipient
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_mail_recipient_type
        ON mail_recipient (
            recipient_type,
            display_name
        )
        """
    )


# ============================================================
# FILTER CACHE
# ============================================================

def _rebuild_filter_option_cache(
    connection,
) -> None:
    """
    Rebuild filter cache.
    """

    connection.execute(
        "DELETE FROM filter_eqp_option"
    )

    connection.execute(
        "DELETE FROM filter_chamber_option"
    )

    connection.execute(
        "DELETE FROM filter_scrap_code_option"
    )

    connection.execute(
        "DELETE FROM filter_model_option"
    )

    # --------------------------------------------------------
    # EQP
    # --------------------------------------------------------

    connection.execute(
        """
        INSERT INTO filter_eqp_option (
            eqp,
            row_count
        )
        SELECT
            EQP,
            COUNT(*)
        FROM prime_data
        GROUP BY EQP
        """
    )

    # --------------------------------------------------------
    # Chamber
    # --------------------------------------------------------

    connection.execute(
        """
        INSERT INTO filter_chamber_option (
            chamber,
            row_count
        )
        SELECT
            Chamber,
            COUNT(*)
        FROM prime_data
        GROUP BY Chamber
        """
    )

    # --------------------------------------------------------
    # Scrap Code - PRIME
    # --------------------------------------------------------

    connection.execute(
        """
        INSERT INTO filter_scrap_code_option (
            scrap_code,
            prime_row_count,
            cum_row_count
        )
        SELECT
            SCRAPCODE,
            COUNT(*),
            0
        FROM prime_data
        WHERE TRIM(
            COALESCE(SCRAPCODE, '')
        ) != ''
        GROUP BY SCRAPCODE
        """
    )

    # --------------------------------------------------------
    # Scrap Code - CUM
    # --------------------------------------------------------

    connection.execute(
        """
        INSERT INTO filter_scrap_code_option (
            scrap_code,
            prime_row_count,
            cum_row_count
        )
        SELECT
            detail.scrap_code,
            0,
            COUNT(*)
        FROM cum_scrap_detail AS detail
        GROUP BY detail.scrap_code

        ON CONFLICT(scrap_code)
        DO UPDATE SET
            cum_row_count =
                excluded.cum_row_count
        """
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    connection.execute(
        """
        INSERT INTO filter_model_option (
            model,
            row_count
        )
        SELECT
            MODEL,
            COUNT(*)
        FROM prime_data
        GROUP BY MODEL
        """
    )

