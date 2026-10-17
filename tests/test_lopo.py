"""Synthetic, in-memory tests. No study data and no Julia runtime are required."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import pandas as pd

from digitalrock_sr.descriptors import PARAM_NAMES, SEALED_ROCKS
from digitalrock_sr.evaluation import canonical_expression, evaluate_formula, metrics
from digitalrock_sr.families import family_key, write_summaries
from digitalrock_sr.lopo import (
    aggregate,
    code_digest,
    load_config,
    prepare,
    run_task,
    search_options,
    task_complete,
    task_dir,
)
from digitalrock_sr.preprocessing import (
    complete_cases,
    fit_preprocessor,
    load_input,
    lopo_folds,
    parent_balanced_sample,
    transform_frame,
)

ROOT = Path(__file__).resolve().parents[1]


def synthetic_frame():
    rows = []
    for ri, (rock, count) in enumerate([("A", 3), ("B", 5), ("C", 4)]):
        for i in range(count):
            row = {name: 1.0 + i / 10 + ri / 5 for name in PARAM_NAMES}
            row.update(
                Filename=f"{rock}_{i}.raw",
                rock_name=rock,
                lithology="sandstone",
                permeability=10.0 ** (-14 + i / 5 + ri / 10),
                porosity_extracted=0.1 + i / 100,
                euler_density=(-1) ** i * (i + 1) * 0.01,
            )
            rows.append(row)
    return pd.DataFrame(rows)


class FakeModel:
    """Two Pareto members ensure that no best-only filtering slips in."""

    last = None

    def __init__(self, **options):
        self.options = options
        FakeModel.last = self

    def fit(self, x, y, variable_names):
        self.x = x.copy()
        self.y = y.copy()
        self.variable_names = variable_names
        self.equations_ = pd.DataFrame(
            [
                {"equation": "-13.5", "complexity": 1, "loss": 1.0},
                {"equation": "porosity_extracted - 12", "complexity": 3, "loss": 0.1},
            ]
        )


class InputAndTransformTests(unittest.TestCase):
    def setUp(self):
        self.frame = synthetic_frame()

    def test_twenty_ordered_descriptors(self):
        self.assertEqual(len(PARAM_NAMES), 20)
        self.assertEqual(len(set(PARAM_NAMES)), 20)

    def test_whole_rock_isolation_and_full_test_rows(self):
        counts = self.frame.groupby("rock_name").size()
        for rock, train, test in lopo_folds(self.frame):
            self.assertTrue(set(train.rock_name).isdisjoint(test.rock_name))
            self.assertEqual(len(test), counts[rock])
            self.assertEqual(len(train) + len(test), len(self.frame))

    def test_balanced_sampling_exact_archived_rng(self):
        sampled = parent_balanced_sample(self.frame, 700000)
        rng = np.random.default_rng(700000)
        expected = []
        for rock in sorted(self.frame.rock_name.unique()):
            group = self.frame[self.frame.rock_name == rock]
            expected.extend(group.iloc[rng.choice(len(group), 5, replace=len(group) < 5)].Filename)
        self.assertEqual(sampled.Filename.tolist(), expected)
        self.assertEqual(sampled.groupby("rock_name").size().tolist(), [5, 5, 5])
        self.assertEqual(len(sampled[sampled.rock_name == "B"].Filename.unique()), 5)

    def test_sampling_repeatability(self):
        pd.testing.assert_frame_equal(
            parent_balanced_sample(self.frame, 4), parent_balanced_sample(self.frame, 4)
        )

    def test_duplicate_id_is_fatal(self):
        bad = pd.concat([self.frame, self.frame.iloc[:1]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            complete_cases(bad)

    def test_external_rock_rejected_before_quality_control(self):
        bad = self.frame.copy()
        bad.loc[0, "rock_name"] = sorted(SEALED_ROCKS)[0]
        bad.loc[0, "permeability"] = np.nan
        with self.assertRaisesRegex(ValueError, "hold-out"):
            complete_cases(bad)

    def test_other_lithology_rejected(self):
        bad = self.frame.copy()
        bad.loc[0, "lithology"] = "carbonate"
        with self.assertRaisesRegex(ValueError, "sandstone"):
            complete_cases(bad)

    def test_quality_control_signed_euler_and_numeric_conversion(self):
        bad = self.frame.copy()
        bad.loc[0, "formation_factor"] = 0
        bad.loc[1, "permeability"] = np.inf
        bad["porosity_extracted"] = bad["porosity_extracted"].astype(str)
        clean = complete_cases(bad)
        self.assertEqual(len(clean), len(bad) - 2)
        self.assertTrue((clean.euler_density < 0).any())
        self.assertTrue(pd.api.types.is_numeric_dtype(clean.porosity_extracted))

    def test_entire_rock_removed_is_fatal(self):
        bad = self.frame.copy()
        bad.loc[bad.rock_name == "A", "permeability"] = 0
        with self.assertRaisesRegex(ValueError, "entire rock"):
            complete_cases(bad)

    def test_euler_scale_is_training_only(self):
        train = self.frame[self.frame.rock_name != "C"].copy()
        test = self.frame[self.frame.rock_name == "C"].copy()
        pre = fit_preprocessor(train)
        expected = np.median(np.abs(train.euler_density))
        self.assertEqual(pre.euler_scale, expected)
        test["euler_density"] = 1e12
        x, y = transform_frame(test, pre)
        np.testing.assert_allclose(x.euler_density, np.arcsinh(1e12 / expected))
        np.testing.assert_allclose(y, np.log10(test.permeability))
        self.assertEqual(x.columns.tolist(), PARAM_NAMES)
        self.assertEqual(pre.euler_scale, expected)

    def test_zero_euler_training_scale_fails(self):
        frame = self.frame.copy()
        frame["euler_density"] = 0
        with self.assertRaisesRegex(ValueError, "undefined"):
            fit_preprocessor(frame)

    def test_transform_does_not_drop_invalid_test_rows(self):
        pre = fit_preprocessor(self.frame)
        bad = self.frame.copy()
        bad.loc[0, "formation_factor"] = 0
        with self.assertRaisesRegex(ValueError, "Nonpositive"):
            transform_frame(bad, pre)

    def test_canonicalization_and_prediction(self):
        a = canonical_expression("2*mean_chord_length - formation_factor + 1")[0]
        b = canonical_expression("1 - formation_factor + mean_chord_length*2")[0]
        self.assertEqual(a, b)
        x, _ = transform_frame(self.frame, fit_preprocessor(self.frame))
        np.testing.assert_allclose(evaluate_formula("2", x), 2)
        np.testing.assert_allclose(evaluate_formula("formation_factor", x), x.formation_factor)

    def test_invalid_prediction_is_not_reported_as_good_score(self):
        self.assertTrue(np.isnan(metrics(np.arange(3), np.array([1, np.nan, 3]))["r2"]))

    def test_algebraic_grouping_removes_intercept_not_exponents(self):
        self.assertEqual(
            family_key("2*mean_chord_length-formation_factor+1"),
            family_key("-formation_factor+7+2*mean_chord_length"),
        )
        self.assertNotEqual(
            family_key("2*mean_chord_length-formation_factor+1"),
            family_key("3*mean_chord_length-formation_factor+1"),
        )


class PlanAndRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "input.csv"
        synthetic_frame().to_csv(self.data, index=False)
        self.config = self.root / "config.json"
        self.cfg = json.loads((ROOT / "configs/sandstone_lopo.json").read_text())
        self.cfg.update(
            name="synthetic_test",
            folds=3,
            seeds=[41, 42],
            expected_rocks=["A", "B", "C"],
            iterations=1,
            populations=2,
            population_size=20,
        )
        self.config.write_text(json.dumps(self.cfg), encoding="utf-8")
        self.out = self.root / "results"

    def tearDown(self):
        self.temp.cleanup()

    def plan(self):
        return prepare(self.data, self.config, self.out)

    def test_one_balance_table_per_fold_shared_across_seeds(self):
        meta = self.plan()
        self.assertEqual(meta["task_count"], 6)
        self.assertEqual(len(meta["balance_tables"]), 3)
        for balance in meta["balance_tables"]:
            tasks = [t for t in meta["tasks"] if t["fold"] == balance["fold"]]
            self.assertEqual(len({t["balance_sha256"] for t in tasks}), 1)
            self.assertEqual(balance["balance_seed"], 700000 + balance["fold_index"])
            self.assertNotIn(balance["fold"], balance["training_rocks"])

    def test_resume_preserves_fold_tables(self):
        a = self.plan()
        times = {p: p.stat().st_mtime_ns for p in self.out.glob("fold_balance_tables/*.csv")}
        b = self.plan()
        self.assertEqual(a["run_identity"], b["run_identity"])
        self.assertEqual(times, {p: p.stat().st_mtime_ns for p in times})

    def test_changed_config_refuses_resume(self):
        self.plan()
        self.cfg["iterations"] = 2
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, "Resume refused"):
            self.plan()

    def test_changed_input_refuses_resume(self):
        self.plan()
        self.data.write_text(self.data.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "Resume refused"):
            self.plan()

    def test_tampered_fold_table_refuses_resume(self):
        meta = self.plan()
        path = self.out / meta["balance_tables"][0]["file"]
        path.write_text(path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "modified shared"):
            self.plan()

    def test_nonempty_unknown_output_refused(self):
        self.out.mkdir()
        (self.out / "unrelated.txt").write_text("keep me")
        with self.assertRaisesRegex(ValueError, "not empty"):
            self.plan()
        self.assertEqual((self.out / "unrelated.txt").read_text(), "keep me")

    def test_task_fits_training_only_and_keeps_whole_front(self):
        meta = self.plan()
        task = meta["tasks"][0]
        result = run_task(self.out, task["fold"], task["seed"], FakeModel)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["pareto_rows"], 2)
        sampled = pd.read_csv(self.out / task["balance_file"])
        pre = fit_preprocessor(sampled)
        x, y = transform_frame(sampled, pre)
        np.testing.assert_allclose(FakeModel.last.x, x)
        np.testing.assert_allclose(FakeModel.last.y, y)
        self.assertEqual(FakeModel.last.variable_names, PARAM_NAMES)
        self.assertEqual(FakeModel.last.options["parallelism"], "serial")
        self.assertEqual(FakeModel.last.options["unary_operators"], [])
        self.assertTrue(task_complete(self.out, task, meta["run_identity"]))
        table = pd.read_csv(task_dir(self.out, task["fold"], task["seed"]) / "pareto.csv")
        self.assertEqual(table.complexity.tolist(), [1, 3])
        self.assertIn("test_rmse", table)

    def test_incomplete_aggregation_fails(self):
        meta = self.plan()
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            aggregate(self.out, meta)

    def test_modified_pareto_invalidates_resume_completion(self):
        meta = self.plan()
        task = meta["tasks"][0]
        run_task(self.out, task["fold"], task["seed"], FakeModel)
        path = task_dir(self.out, task["fold"], task["seed"]) / "pareto.csv"
        path.write_text(path.read_text() + "\n")
        self.assertFalse(task_complete(self.out, task, meta["run_identity"]))

    def test_completed_run_aggregates_all_tasks_and_records(self):
        meta = self.plan()
        for task in meta["tasks"]:
            self.assertEqual(
                run_task(self.out, task["fold"], task["seed"], FakeModel)["status"], "completed"
            )
        aggregate(self.out, meta)
        self.assertEqual(len(pd.read_csv(self.out / "pareto_all.csv")), 12)
        self.assertEqual(len(pd.read_csv(self.out / "task_manifest.csv")), 6)
        frequency = pd.read_csv(self.out / "descriptor_frequency.csv")
        self.assertEqual(len(frequency), 20)
        row = frequency[frequency.descriptor == "porosity_extracted"].iloc[0]
        self.assertEqual(row.record_fraction, 0.5)
        self.assertEqual(row.task_fraction, 1.0)

    def test_cli_dry_run_without_julia(self):
        command = [
            sys.executable,
            str(ROOT / "scripts/run_symbolic_regression.py"),
            "--input-csv",
            str(self.data),
            "--config",
            str(self.config),
            "--output-dir",
            str(self.out),
            "--dry-run",
        ]
        done = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(
            json.loads((self.out / "experiment_metadata.json").read_text())["task_count"], 6
        )
        self.assertFalse(list(self.out.glob("p/*/s*/pareto.csv")))

    def test_config_seeds_must_be_unique(self):
        self.cfg["seeds"] = [41, 41]
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, "unique"):
            load_config(self.config)

    def test_config_unknown_discovery_rocks_rejected(self):
        with self.assertRaisesRegex(ValueError, "rock names"):
            load_input(self.data)

    def test_search_complexity_minimum_checked_before_julia(self):
        self.cfg["maxsize"] = 5
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, "at least 7"):
            load_config(self.config)


if __name__ == "__main__":
    unittest.main()
