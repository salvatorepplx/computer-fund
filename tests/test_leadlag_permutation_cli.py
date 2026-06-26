import contextlib
import io
import json
import sys
import unittest
from unittest import mock

from evals import leadlag_permutation


class LeadLagPermutationCliTest(unittest.TestCase):
    def test_cli_passes_custom_min_n_and_seed(self):
        result = {"entity": "TICKER:RDDT", "min_n": 11, "seed_seen": 123}

        with mock.patch.object(sys, "argv", [
            "leadlag_permutation.py",
            "TICKER:RDDT",
            "--k",
            "17",
            "--max-lag",
            "3",
            "--min-n",
            "11",
            "--seed",
            "123",
        ]), mock.patch.object(
            leadlag_permutation, "permutation_test", return_value=result
        ) as permutation_test, contextlib.redirect_stdout(io.StringIO()) as stdout:
            exit_code = leadlag_permutation.main()

        self.assertEqual(exit_code, 0)
        permutation_test.assert_called_once_with("TICKER:RDDT", 17, 3, 11, 123)
        self.assertEqual(json.loads(stdout.getvalue()), result)

    def test_cli_preserves_existing_defaults(self):
        result = {"entity": "TICKER:NVDA", "min_n": 24, "seed_seen": 7}

        with mock.patch.object(sys, "argv", [
            "leadlag_permutation.py",
        ]), mock.patch.object(
            leadlag_permutation, "permutation_test", return_value=result
        ) as permutation_test, contextlib.redirect_stdout(io.StringIO()) as stdout:
            exit_code = leadlag_permutation.main()

        self.assertEqual(exit_code, 0)
        permutation_test.assert_called_once_with("TICKER:NVDA", 2000, 5, 24, 7)
        self.assertEqual(json.loads(stdout.getvalue()), result)


if __name__ == "__main__":
    unittest.main()
