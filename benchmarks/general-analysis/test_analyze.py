#!/usr/bin/env python3
"""Focused regression tests for the paired stratum analysis helpers."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("analyze.py")
SPEC = importlib.util.spec_from_file_location("general_analysis", MODULE_PATH)
assert SPEC and SPEC.loader
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)


def trial(identifier, task, repetition, stratum, total, passed=True, changed=1):
    return {
        "id": identifier,
        "task": task,
        "repetition": repetition,
        "stratum": stratum,
        "pairKey": f"{task}::r{repetition}",
        "valid": True,
        "usage": {
            "inputTotal": total,
            "inputUncached": total,
            "inputCached": 0,
            "outputTokens": 0,
            "requests": 1,
            "cachedRequests": 0,
        },
        "evaluation": {
            "taskPass": passed,
            "testsPassed": 10 if passed else 9,
            "testsTotal": 10,
            "casePassRate": 1.0 if passed else 0.9,
        },
        "filter": {"applied": changed, "actions": {"KEEP_RESULT": changed}},
        "gc": {"applied": 0, "actions": {}},
        "judge": {"calls": changed, "latencyMs": 1},
        "wallMs": 1,
        "model": "test",
    }


class StratumAnalysisTests(unittest.TestCase):
    def test_arm_summary_keeps_short_and_long_rows_separate(self):
        rows = [
            trial("short-base", "short-task", 0, "short", 100),
            trial("long-base", "long-task", 0, "long", 1000),
        ]
        summary = ANALYSIS.summarize_arm_strata(rows, {"short": 1, "long": 1})
        self.assertEqual(summary["short"]["inputTotal"], 100)
        self.assertEqual(summary["long"]["inputTotal"], 1000)
        self.assertEqual(summary["short"]["taskPasses"], 1)
        self.assertEqual(summary["long"]["taskPasses"], 1)

    def test_paired_savings_are_reported_per_stratum(self):
        baseline = [
            trial("short-base", "short-task", 0, "short", 100),
            trial("long-base", "long-task", 0, "long", 1000),
        ]
        candidate = [
            trial("short-laya", "short-task", 0, "short", 110),
            trial("long-laya", "long-task", 0, "long", 700),
        ]
        target = {"minSavings": 0.25, "maxSavings": 0.35, "maxTaskDrop": 0, "maxCaseDrop": 0.02}
        for label, expected in (("short", -10.0), ("long", 30.0)):
            pairs, pairing = ANALYSIS.pair_rows(
                [row for row in baseline if row["stratum"] == label],
                [row for row in candidate if row["stratum"] == label],
            )
            report = ANALYSIS.compare_pair_group(pairs, pairing, "baseline", "laya", target, 7, 10)
            self.assertAlmostEqual(report["total"]["pooledSavingsPercent"], expected)
        all_pairs, pairing = ANALYSIS.pair_rows(baseline, candidate)
        report = ANALYSIS.compare_pair_group(all_pairs, pairing, "baseline", "laya", target, 7, 10)
        self.assertIn("short", {row["stratum"] for row in ANALYSIS.pair_records(all_pairs)})
        self.assertAlmostEqual(report["total"]["pooledSavingsPercent"], 26.363636, places=4)

    def test_stratum_quality_guard_fails_on_task_regression(self):
        baseline = [trial("base", "task", 0, "short", 100, passed=True)]
        candidate = [trial("candidate", "task", 0, "short", 70, passed=False)]
        pairs, pairing = ANALYSIS.pair_rows(baseline, candidate)
        target = {"minSavings": 0.25, "maxSavings": 0.35, "maxTaskDrop": 0, "maxCaseDrop": 0.02}
        report = ANALYSIS.compare_pair_group(pairs, pairing, "baseline", "laya", target, 9, 10)
        self.assertFalse(report["quality"]["pass"])
        self.assertEqual(report["target"]["gate"], "FAIL_QUALITY")

    def test_invalid_expected_pair_cannot_pass_from_surviving_pairs(self):
        """A failed canonical-url row must make every affected comparison incomplete."""

        def artifact(identifier, task, arm, error=None):
            return {
                "id": identifier,
                "task": task,
                "stratum": "short",
                "repetition": 0,
                "arm": arm,
                "inputTotal": 100,
                "inputUncached": 100,
                "inputCached": 0,
                "outputTokens": 0,
                "requests": 1,
                "evaluation": {"passed": 10, "total": 10, "success": True},
                "error": error,
                "prunedResults": 1 if arm != "baseline" else 0,
                "removedToolCharacters": 100 if arm != "baseline" else 0,
                "judgeCalls": 1 if arm != "baseline" else 0,
                "judgeLatencyMs": 1,
                "wallMs": 1,
            }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "design.json").write_text(json.dumps({
                "design": {
                    "repeats": 1,
                    "arms": ["baseline", "laya", "von"],
                    "tasks": [
                        {"id": "kept", "stratum": "short"},
                        {"id": "canonical-url", "stratum": "short"},
                    ],
                }
            }))
            rows = [
                artifact("kept-r0-baseline", "kept", "baseline"),
                artifact("canonical-url-r0-baseline", "canonical-url", "baseline", "fetch failed"),
                artifact("kept-r0-laya", "kept", "laya"),
                artifact("canonical-url-r0-laya", "canonical-url", "laya"),
                artifact("kept-r0-von", "kept", "von"),
                artifact("canonical-url-r0-von", "canonical-url", "von", "fetch failed"),
            ]
            for row in rows:
                directory = root / row["id"]
                directory.mkdir()
                (directory / "result.json").write_text(json.dumps(row))
            args = type("Args", (), {
                "baseline": "baseline",
                "treatments": ["laya", "von"],
                "min_savings": None,
                "max_savings": None,
                "max_task_drop": None,
                "max_case_drop": None,
                "bootstrap": 20,
            })()
            analysis = ANALYSIS.build_analysis(root, args)
            self.assertEqual(analysis["validity"]["incompleteExpectedCount"], 2)
            for name in ("laya", "von"):
                comparison = analysis["comparisons"][name]
                self.assertFalse(comparison["pairing"]["complete"])
                self.assertEqual(comparison["target"]["gate"], "INCOMPLETE")
                self.assertFalse(comparison["quality"]["complete"])
                self.assertFalse(comparison["quality"]["pass"])


if __name__ == "__main__":
    unittest.main()
