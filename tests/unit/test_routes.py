# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import pytest
from symdex.core.storage import get_connection


def test_routes_table_exists(tmp_path):
    db = str(tmp_path / "test.db")
    conn = get_connection(db)
    # If table doesn't exist this raises OperationalError
    conn.execute("SELECT * FROM routes LIMIT 0")
    conn.close()
