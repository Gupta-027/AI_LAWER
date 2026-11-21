"""Behavior tests reuse the same entry point and synthetic inputs as evaluation."""
from __future__ import annotations

import os
import unittest

os.environ["NYAYA_PROVIDER"] = "demo"

from evaluation.runner import assess, load_cases, run_case


class BehaviorTests(unittest.TestCase):
    def test_original_synthetic_conversations(self):
        results = {}
        for spec in load_cases():
            with self.subTest(case=spec["id"]):
                raw = run_case(spec)
                results[spec["id"]] = raw
                for check in assess(spec, raw):
                    with self.subTest(check=check["check"]):
                        self.assertTrue(check["passed"], check["note"])
        # Paired input should materially change the actual correspondence.
        first = results["rental_written_deductions"]["final_state"]["draft"]
        second = results["rental_no_explanation"]["final_state"]["draft"]
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
