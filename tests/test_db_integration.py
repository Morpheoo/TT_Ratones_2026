import sys
import os
import unittest
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.connection import get_db_engine

class TestDBIntegration(unittest.TestCase):

    def setUp(self):
        self.engine = get_db_engine()
        if not self.engine:
            self.skipTest("Database engine could not be created. Skipping integration test.")
        self.test_email = "test_integration_user@ipn.mx"
        self.test_rat_id = "TEST-RAT-01"

    def tearDown(self):
        """Clean up test data to avoid pollution."""
        with self.engine.connect() as conn:
            # Delete in order of dependencies (Child first, then Parent)
            conn.execute(text("DELETE FROM experiments WHERE rat_id = :rid"), {"rid": self.test_rat_id})
            conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": self.test_email})
            conn.commit()

    def test_experiment_lifecycle(self):
        """
        Test creating a User -> Creating an Experiment -> Verifying it exists.
        """
        with self.engine.connect() as conn:
            # 1. Create Test User
            # We use ON CONFLICT behavior or simple check to ensure we know the ID
            conn.execute(text("DELETE FROM users WHERE username = :u"), {"u": self.test_email}) # Pre-clean
            conn.commit()

            insert_user = text("""
                INSERT INTO users (username, password_hash, role, is_verified, is_active)
                VALUES (:u, 'hashed_secret', 'investigador', TRUE, TRUE)
                RETURNING id
            """)
            result_user = conn.execute(insert_user, {"u": self.test_email}).fetchone()
            user_id = result_user[0]
            self.assertIsNotNone(user_id)

            # 2. Create Test Experiment linked to User
            insert_exp = text("""
                INSERT INTO experiments (rat_id, treatment, video_path, created_by, duration_seconds)
                VALUES (:rid, 'Placebo', 'C:/tmp/video_test.mp4', :uid, 300)
                RETURNING id
            """)
            result_exp = conn.execute(insert_exp, {"rid": self.test_rat_id, "uid": user_id}).fetchone()
            exp_id = result_exp[0]
            self.assertIsNotNone(exp_id)
            conn.commit()

            # 3. Verify Reading Back
            query = text("SELECT treatment, duration_seconds FROM experiments WHERE id = :eid")
            row = conn.execute(query, {"eid": exp_id}).fetchone()
            
            self.assertEqual(row[0], 'Placebo')
            self.assertEqual(row[1], 300)
            
            print(f"\n[OK] Integration Test Passed: User {user_id} created Experiment {exp_id}")

if __name__ == '__main__':
    unittest.main()
