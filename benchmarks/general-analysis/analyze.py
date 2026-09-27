#!/usr/bin/env python3
"""Aggregate paired general coding benchmark runs.

The runner deliberately keeps this report consumer independent from the Pi
host.  A run is a directory containing ``design.json`` and one directory per
trial.  Each trial directory contains ``result.json`` and may contain
``telemetry.json``, ``judge.jsonl``, ``filter-events.jsonl`` and ``gc.jsonl``.

The report compares every candidate with the baseline having the same task and
repetition.  It reports total, cached and uncached input separately, computes
paired bootstrap intervals, and only attributes savings to a policy when an
event log shows that the policy changed context.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
DEFAULT_MIN_SAVINGS = 0.25
DEFAULT_MAX_SAVINGS = 0.35
DEFAULT_MAX_TASK_DROP = 0.0
DEFAULT_MAX_CASE_DROP = 0.02
DEFAULT_BOOTSTRAP = 20_000


def number(value: Any) -> float | None:
    """Return a finite numeric value, preserving integer-looking values."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def integer(value: Any) -> int | None:
    value = number(value)
    if value is None:
        return None
    return int(value)


def first_number(*values: Any) -> float | None:
    for value in values:
        result = number(value)
        if result is not None:
            return result
    return None


def first_integer(*values: Any) -> int | None:
    for value in values:
        result = integer(value)
        if result is not None:
            return result
    return None


def get_path(value: Any, *path: str) -> Any:
    for name in path:
        if not isinstance(value, dict):
            return None
        value = value.get(name)
    return value


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    if not path.exists():
        return rows, malformed
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return rows, 1
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(item, dict):
            rows.append(item)
        else:
            malformed += 1
    return rows, malformed


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def normalize_fraction(value: Any, default: float) -> float:
    value = number(value)
    if value is None:
        return default
    # Design files often use percentages while the calculations use fractions.
    return value / 100.0 if abs(value) > 1.0 else value


def compact(value: float | int | None) -> int | float | None:
    if value is None:
        return None
    if float(value).is_integer():
        return int(value)
    return round(float(value), 6)


def parse_design(root: Path) -> tuple[dict[str, Any], list[str], int | None, list[str], dict[str, str]]:
    raw = load_json(root / "design.json")
    if not isinstance(raw, dict):
        return {}, [], None, [], {}
    design = raw.get("design") if isinstance(raw.get("design"), dict) else raw
    arms_value = design.get("arms", [])
    arm_names: list[str] = []
    if isinstance(arms_value, list):
        for arm in arms_value:
            if isinstance(arm, str):
                arm_names.append(arm)
            elif isinstance(arm, dict) and isinstance(arm.get("name"), str):
                arm_names.append(arm["name"])
    elif isinstance(arms_value, dict):
        arm_names.extend(str(name) for name in arms_value)
    repeats = first_integer(design.get("repeats"), design.get("repeatCount"))
    tasks: list[str] = []
    task_strata: dict[str, str] = {}
    for task in as_list(design.get("tasks")):
        if isinstance(task, str):
            tasks.append(task)
        elif isinstance(task, dict):
            task_id = task.get("id", task.get("name"))
            if task_id is not None:
                task_id = str(task_id)
                tasks.append(task_id)
                metadata = task.get("metadata") or task.get("meta") or {}
                stratum = task.get("stratum")
                if stratum is None and isinstance(metadata, dict):
                    stratum = metadata.get("stratum")
                # `length` is accepted as a compatibility alias when the
                # fixture design uses short/long task metadata directly.
                if stratum is None and str(task.get("length", "")).lower() in {"short", "long"}:
                    stratum = task.get("length")
                if stratum is not None:
                    task_strata[task_id] = str(stratum)
    return design, arm_names, repeats, tasks, task_strata


def infer_task_repeat(path: Path) -> tuple[str | None, int | None]:
    # The current runner names directories task-rN-arm.  Keep this fallback
    # only for incomplete artifacts; result.json remains the source of truth.
    pieces = path.name.split("-")
    repetition: int | None = None
    for piece in pieces:
        match = re.fullmatch(r"r?(\d+)", piece)
        if match:
            repetition = int(match.group(1))
            break
    task = path.name
    if repetition is not None:
        task = re.sub(r"[-_]r?\d+[-_]?.*$", "", task)
    return task or None, repetition


def normalize_stratum(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def usage_from_telemetry(telemetry: Any) -> dict[str, float | int | None]:
    if isinstance(telemetry, list):
        entries = telemetry
    elif isinstance(telemetry, dict):
        entries = as_list(telemetry.get("usage"))
        if not entries:
            entries = as_list(telemetry.get("requests"))
    else:
        entries = []

    total = cached = uncached = output = 0.0
    have_total = have_cached = have_uncached = have_output = False
    cached_requests = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        cache = first_number(
            entry.get("cached_tokens"),
            entry.get("cacheRead"),
            entry.get("cache_read_tokens"),
            entry.get("input_cached_tokens"),
            get_path(entry, "usage", "prompt_tokens_details", "cached_tokens"),
        )
        raw_uncached = first_number(
            entry.get("inputUncached"),
            entry.get("uncachedInput"),
            entry.get("input"),
            entry.get("input_tokens_uncached"),
            entry.get("uncached_tokens"),
        )
        raw_total = first_number(
            entry.get("inputTotal"),
            entry.get("totalInputTokens"),
            entry.get("input_tokens_total"),
            get_path(entry, "usage", "input_tokens"),
        )
        raw_output = first_number(
            entry.get("outputTokens"), entry.get("output"), entry.get("output_tokens")
        )
        if cache is not None:
            cached += cache
            have_cached = True
            if cache > 0:
                cached_requests += 1
        if raw_uncached is not None:
            uncached += raw_uncached
            have_uncached = True
        if raw_total is not None:
            total += raw_total
            have_total = True
        elif raw_uncached is not None or cache is not None:
            total += (raw_uncached or 0.0) + (cache or 0.0)
            have_total = True
        if raw_output is not None:
            output += raw_output
            have_output = True

    # Some providers expose only total input and cached input.  In that case
    # infer uncached input after summing all requests.
    if have_total and not have_uncached:
        uncached = max(0.0, total - cached)
        have_uncached = True
    if have_total and have_uncached and not have_cached:
        cached = max(0.0, total - uncached)
        have_cached = True
    return {
        "inputTotal": total if have_total else None,
        "inputCached": cached if have_cached else None,
        "inputUncached": uncached if have_uncached else None,
        "outputTokens": output if have_output else None,
        "requests": len(entries) if entries else None,
        "cachedRequests": cached_requests if entries else None,
    }


def extract_usage(result: dict[str, Any], telemetry: Any) -> dict[str, Any]:
    telemetry_usage = usage_from_telemetry(telemetry)
    total = first_number(
        result.get("inputTotal"),
        result.get("totalInputTokens"),
        result.get("input_tokens_total"),
        get_path(result, "input", "total"),
        get_path(result, "usage", "inputTotal"),
        telemetry_usage["inputTotal"],
    )
    cached = first_number(
        result.get("inputCached"),
        result.get("cachedInput"),
        result.get("cacheRead"),
        result.get("cached_tokens"),
        result.get("input_cached_tokens"),
        get_path(result, "input", "cached"),
        get_path(result, "usage", "inputCached"),
        telemetry_usage["inputCached"],
    )
    uncached = first_number(
        result.get("inputUncached"),
        result.get("uncachedInput"),
        result.get("input_tokens_uncached"),
        get_path(result, "input", "uncached"),
        get_path(result, "usage", "inputUncached"),
        telemetry_usage["inputUncached"],
    )
    output = first_number(
        result.get("outputTokens"),
        result.get("output_tokens"),
        get_path(result, "usage", "outputTokens"),
        telemetry_usage["outputTokens"],
    )
    if total is None and uncached is not None:
        total = uncached + (cached or 0.0)
    if total is not None and uncached is None:
        uncached = max(0.0, total - (cached or 0.0))
    if total is not None and cached is None:
        cached = max(0.0, total - (uncached or 0.0))
    requests = first_integer(result.get("requests"), telemetry_usage.get("requests"))
    cached_requests = first_integer(
        result.get("cachedRequests"), telemetry_usage.get("cachedRequests")
    )
    return {
        "inputTotal": compact(total),
        "inputCached": compact(cached),
        "inputUncached": compact(uncached),
        "outputTokens": compact(output),
        "allTokens": compact((total or 0.0) + (output or 0.0))
        if total is not None or output is not None
        else first_number(result.get("allTokens")),
        "requests": requests,
        "cachedRequests": cached_requests,
        "source": "result" if any(
            key in result
            for key in ("inputTotal", "inputCached", "inputUncached", "outputTokens")
        ) else "telemetry",
    }


def evaluation_metrics(result: dict[str, Any]) -> dict[str, Any]:
    evaluation = result.get("evaluation")
    if not isinstance(evaluation, dict):
        evaluation = {}
    passed = first_integer(
        evaluation.get("passed"), result.get("testsPassed"), result.get("passed")
    )
    total = first_integer(
        evaluation.get("total"), result.get("testsTotal"), result.get("total")
    )
    success_value = evaluation.get("success", result.get("taskPass"))
    success = success_value if isinstance(success_value, bool) else None
    if success is None and passed is not None and total is not None:
        success = total > 0 and passed == total
    rate = passed / total if passed is not None and total and total > 0 else None
    initial = result.get("initialEvaluation")
    initial_success = initial.get("success") if isinstance(initial, dict) else None
    return {
        "taskPass": success,
        "testsPassed": passed,
        "testsTotal": total,
        "casePassRate": rate,
        "initialTaskPass": initial_success if isinstance(initial_success, bool) else None,
    }


def event_rows(trial_dir: Path, result: dict[str, Any], field: str, filename: str) -> tuple[list[dict[str, Any]], int]:
    value = result.get(field)
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)], 0
    if isinstance(value, dict):
        return [value], 0
    return load_jsonl(trial_dir / filename)


def filter_metrics(trial_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    embedded = None
    for field in ("filterEvents", "contextEvents", "events"):
        if field in result:
            embedded = result.get(field)
            break
    if embedded is not None:
        rows = [row for row in as_list(embedded) if isinstance(row, dict)]
        malformed = 0
        source = "result"
    else:
        rows, malformed = load_jsonl(trial_dir / "context-events.jsonl")
        source = "context-events.jsonl"
        if not rows:
            rows, malformed_filter = load_jsonl(trial_dir / "filter-events.jsonl")
            malformed += malformed_filter
            source = "filter-events.jsonl"
    actions: Counter[str] = Counter()
    judge_actions: Counter[str] = Counter()
    changed = 0
    removed = 0.0
    for row in rows:
        event_action = row.get("action")
        if isinstance(event_action, str):
            actions[event_action] += 1
        for decision in as_list(row.get("decisions")):
            if isinstance(decision, dict) and isinstance(decision.get("action"), str):
                # Nested decisions are judge votes.  They are not an applied
                # action unless the runner also emits the chosen action at the
                # event level.
                judge_actions[decision["action"]] += 1
        explicit_changed = row.get("changed")
        removed_value = first_number(
            row.get("removedCharacters"),
            row.get("removedToolCharacters"),
            row.get("removedContextCharacters"),
        )
        if removed_value is None:
            original = first_number(row.get("originalCharacters"), row.get("beforeCharacters"))
            retained = first_number(row.get("retainedCharacters"), row.get("afterCharacters"))
            if original is not None and retained is not None:
                removed_value = max(0.0, original - retained)
        if removed_value is not None:
            removed += removed_value
        is_changed = explicit_changed if isinstance(explicit_changed, bool) else None
        if is_changed is None:
            is_changed = removed_value is not None and removed_value > 0
        if is_changed:
            changed += 1
    explicit_applied = first_integer(
        result.get("filteredResults"),
        result.get("filterEventsApplied"),
        result.get("actualFilterEvents"),
        # The general runner calls an applied tool-result change a
        # ``prunedResults`` event.  Keep the older filteredResults spelling as
        # an alias for the existing benchmark artifacts.
        result.get("prunedResults"),
    )
    if explicit_applied is not None:
        changed = explicit_applied
    explicit_removed = first_number(
        result.get("removedToolCharacters"), result.get("removedContextCharacters")
    )
    if explicit_removed is not None:
        removed = explicit_removed
    return {
        "judged": len(rows),
        "applied": changed,
        "removedCharacters": compact(removed),
        "actions": dict(sorted(actions.items())),
        "judgeActions": dict(sorted(judge_actions.items())),
        "malformed": malformed,
        "source": source,
    }


def gc_metrics(trial_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    rows, malformed = event_rows(trial_dir, result, "gcEvents", "gc.jsonl")
    actions: Counter[str] = Counter()
    changed = 0
    pruned_messages = 0.0
    pruned_characters = 0.0
    changing_actions = {"DROP", "PRUNE", "REWIND", "NAVIGATE", "COLLECT", "DISCARD"}
    for row in rows:
        action = row.get("action")
        if isinstance(action, str):
            actions[action] += 1
        before = first_number(row.get("beforeMessages"), row.get("before_message_count"))
        after = first_number(row.get("afterMessages"), row.get("after_message_count"))
        if before is not None and after is not None and before > after:
            pruned_messages += before - after
        chars = first_number(
            row.get("removedCharacters"),
            row.get("prunedCharacters"),
            row.get("removedContextCharacters"),
        )
        if chars is not None:
            pruned_characters += max(0.0, chars)
        explicit_changed = row.get("contextChanged", row.get("pruned"))
        if isinstance(explicit_changed, bool):
            changed += int(explicit_changed)
        elif (before is not None and after is not None and before > after) or action in changing_actions:
            # An action named DROP/REWIND is counted only when no explicit
            # false marker is present.  This supports old gc.jsonl artifacts.
            changed += 1
    explicit_applied = first_integer(
        result.get("rewinds"),
        result.get("pruneEvents"),
        result.get("pruneEventsApplied"),
        result.get("actualPrunes"),
    )
    if explicit_applied is not None:
        changed = explicit_applied
    explicit_messages = first_number(result.get("prunedMessages"), result.get("removedMessages"))
    if explicit_messages is not None:
        pruned_messages = explicit_messages
    explicit_chars = first_number(result.get("prunedCharacters"), result.get("removedContextCharacters"))
    if explicit_chars is not None:
        pruned_characters = explicit_chars
    return {
        "judged": len(rows),
        "applied": changed,
        "prunedMessages": compact(pruned_messages),
        "prunedCharacters": compact(pruned_characters),
        "actions": dict(sorted(actions.items())),
        "malformed": malformed,
    }


def judge_metrics(trial_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    rows, malformed = event_rows(trial_dir, result, "judgeEvents", "judge.jsonl")
    latency = 0.0
    for row in rows:
        item = row.get("result") if isinstance(row.get("result"), dict) else row
        latency += first_number(item.get("latencyMs"), row.get("latencyMs")) or 0.0
    calls = first_integer(result.get("judgeCalls"))
    if calls is None:
        calls = len(rows)
    explicit_latency = first_number(result.get("judgeLatencyMs"))
    return {
        "calls": calls,
        "latencyMs": compact(explicit_latency if explicit_latency is not None else latency),
        "malformed": malformed,
    }


def make_trial(path: Path) -> dict[str, Any]:
    result = load_json(path / "result.json")
    if not isinstance(result, dict):
        return {
            "path": str(path),
            "id": path.name,
            "arm": None,
            "task": None,
            "repetition": None,
            "stratum": None,
            "pairKey": None,
            "valid": False,
            "error": "result.json is missing or invalid",
        }
    fallback_task, fallback_repeat = infer_task_repeat(path)
    task = result.get("task", result.get("taskId", fallback_task))
    repetition = first_integer(result.get("repetition"), result.get("repeat"), fallback_repeat)
    metadata = result.get("metadata") or result.get("meta") or {}
    stratum = result.get("stratum")
    if stratum is None and isinstance(metadata, dict):
        stratum = metadata.get("stratum")
    if stratum is None:
        stratum = get_path(result, "config", "stratum")
    arm = result.get("arm")
    if not isinstance(arm, str):
        config = result.get("config")
        arm = config.get("name") if isinstance(config, dict) else None
    if not isinstance(arm, str):
        arm = path.name.rsplit("-", 1)[-1]
    pair_key = result.get("pairKey")
    if pair_key is None and task is not None and repetition is not None:
        pair_key = f"{task}::r{repetition}"
    telemetry = load_json(path / "telemetry.json")
    usage = extract_usage(result, telemetry)
    evaluation = evaluation_metrics(result)
    filters = filter_metrics(path, result)
    gc = gc_metrics(path, result)
    judges = judge_metrics(path, result)
    status = result.get("status")
    error = result.get("error")
    if status in {"error", "failed", "incomplete"} and not error:
        error = f"status={status}"
    missing = []
    for name, value in (("task", task), ("repetition", repetition), ("arm", arm), ("inputTotal", usage["inputTotal"]), ("evaluation", evaluation["taskPass"])):
        if value is None:
            missing.append(name)
    if error:
        valid = False
    else:
        valid = not missing
    return {
        "id": result.get("id", path.name),
        "path": str(path),
        "task": str(task) if task is not None else None,
        "repetition": repetition,
        "stratum": normalize_stratum(stratum),
        "arm": arm,
        "pairKey": str(pair_key) if pair_key is not None else None,
        "valid": valid,
        "error": str(error) if error else None,
        "missing": missing,
        "status": status or ("complete" if valid else "invalid"),
        "model": result.get("model") or get_path(result, "config", "model"),
        "usage": usage,
        "evaluation": evaluation,
        "filter": filters,
        "gc": gc,
        "judge": judges,
        "wallMs": result.get("wallMs"),
        "initialEvaluation": result.get("initialEvaluation"),
        "finalSourceHash": result.get("finalSourceHash"),
    }


def discover_trials(root: Path) -> list[dict[str, Any]]:
    paths = sorted(path for path in root.rglob("result.json") if path.parent != root)
    return [make_trial(path.parent) for path in paths]


def summarize_arm(rows: list[dict[str, Any]], expected: int | None) -> dict[str, Any]:
    valid = [row for row in rows if row["valid"]]
    errors = [row for row in rows if not row["valid"]]

    def sum_metric(section: str, key: str) -> float:
        return sum(number(row[section].get(key)) or 0.0 for row in valid)

    total = sum_metric("usage", "inputTotal")
    cached = sum_metric("usage", "inputCached")
    uncached = sum_metric("usage", "inputUncached")
    output = sum_metric("usage", "outputTokens")
    wall_values = [number(row.get("wallMs")) for row in valid]
    wall_values = [value for value in wall_values if value is not None]
    tests_passed = sum_metric("evaluation", "testsPassed")
    tests_total = sum_metric("evaluation", "testsTotal")
    task_passes = sum(bool(row["evaluation"].get("taskPass")) for row in valid)
    requests = sum_metric("usage", "requests")
    cached_requests = sum_metric("usage", "cachedRequests")
    filter_actions: Counter[str] = Counter()
    prune_actions: Counter[str] = Counter()
    for row in valid:
        filter_actions.update(row["filter"].get("actions") or {})
        prune_actions.update(row["gc"].get("actions") or {})
    return {
        "trials": len(rows),
        "validTrials": len(valid),
        "expectedTrials": expected,
        "completionRate": len(valid) / expected if expected else None,
        "errors": len(errors),
        "errorIds": [row["id"] for row in errors],
        "taskPasses": task_passes,
        "taskPassRate": task_passes / len(valid) if valid else None,
        "testsPassed": compact(tests_passed),
        "testsTotal": compact(tests_total),
        "casePassRate": tests_passed / tests_total if tests_total else None,
        "inputTotal": compact(total),
        "inputCached": compact(cached),
        "inputUncached": compact(uncached),
        "cacheShare": cached / total if total else None,
        "cachedRequests": compact(cached_requests),
        "requests": compact(requests),
        "outputTokens": compact(output),
        "allTokens": compact(total + output),
        "meanWallMs": compact(statistics.mean(wall_values)) if wall_values else None,
        "judgeCalls": sum(integer(row["judge"].get("calls")) or 0 for row in valid),
        "judgeLatencyMs": compact(sum(number(row["judge"].get("latencyMs")) or 0.0 for row in valid)),
        "filterEventsJudged": sum(integer(row["filter"].get("judged")) or 0 for row in valid),
        "filterEventsApplied": sum(integer(row["filter"].get("applied")) or 0 for row in valid),
        "interventionEventsApplied": sum(
            (integer(row["filter"].get("applied")) or 0) + (integer(row["gc"].get("applied")) or 0)
            for row in valid
        ),
        "filterActions": dict(sorted(filter_actions.items())),
        "filterRemovedCharacters": compact(sum(number(row["filter"].get("removedCharacters")) or 0.0 for row in valid)),
        "pruneEventsJudged": sum(integer(row["gc"].get("judged")) or 0 for row in valid),
        "pruneEventsApplied": sum(integer(row["gc"].get("applied")) or 0 for row in valid),
        "pruneActions": dict(sorted(prune_actions.items())),
        "prunedMessages": compact(sum(number(row["gc"].get("prunedMessages")) or 0.0 for row in valid)),
        "prunedCharacters": compact(sum(number(row["gc"].get("prunedCharacters")) or 0.0 for row in valid)),
        "models": sorted({str(row["model"]) for row in valid if row.get("model")}),
    }


def summarize_arm_strata(
    rows: list[dict[str, Any]], expected_by_stratum: dict[str, int | None]
) -> dict[str, dict[str, Any]]:
    """Summarize an arm in each fixture stratum, including unclassified rows."""

    labels = set(expected_by_stratum)
    labels.update(row.get("stratum") or "(unclassified)" for row in rows)
    return {
        label: summarize_arm(
            [row for row in rows if (row.get("stratum") or "(unclassified)") == label],
            expected_by_stratum.get(label),
        )
        for label in sorted(labels)
    }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def bootstrap_interval(values: list[float], seed: int, repetitions: int) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1 or repetitions <= 1:
        return values[0], values[0]
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(repetitions):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    return compact(percentile(means, 0.025)), compact(percentile(means, 0.975))


def mcnemar_p_value(wins: int, losses: int) -> float | None:
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, i) for i in range(min(wins, losses) + 1)) / (2**discordant)
    return min(1.0, 2.0 * tail)


def pair_rows(base_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, Any]]:
    base_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    candidate_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in base_rows:
        if row["valid"] and row.get("pairKey") is not None:
            base_index[row["pairKey"]].append(row)
    for row in candidate_rows:
        if row["valid"] and row.get("pairKey") is not None:
            candidate_index[row["pairKey"]].append(row)
    keys = sorted(set(base_index) & set(candidate_index))
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    duplicate_keys = []
    for key in keys:
        if len(base_index[key]) != 1 or len(candidate_index[key]) != 1:
            duplicate_keys.append(key)
            continue
        pairs.append((base_index[key][0], candidate_index[key][0]))
    return pairs, {
        "paired": len(pairs),
        "baselineOnly": len(set(base_index) - set(candidate_index)),
        "candidateOnly": len(set(candidate_index) - set(base_index)),
        "duplicateKeys": duplicate_keys,
    }


def filter_expected_rows(rows: list[dict[str, Any]], expected_keys: list[str]) -> list[dict[str, Any]]:
    """Keep only design-declared pairs when a design supplies expected keys."""

    if not expected_keys:
        return rows
    expected = set(expected_keys)
    return [row for row in rows if row.get("pairKey") in expected]


def pair_completeness(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    expected_keys: list[str],
) -> dict[str, Any]:
    """Describe missing, failed, or ambiguous expected sides of each pair."""

    if not expected_keys:
        return {"expected": None, "complete": True, "incomplete": []}
    baseline_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    candidate_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in baseline_rows:
        if row.get("pairKey") in expected_keys:
            baseline_by_key[row["pairKey"]].append(row)
    for row in candidate_rows:
        if row.get("pairKey") in expected_keys:
            candidate_by_key[row["pairKey"]].append(row)
    incomplete: list[dict[str, Any]] = []
    for key in expected_keys:
        baseline = baseline_by_key.get(key, [])
        candidate = candidate_by_key.get(key, [])
        reasons: list[str] = []
        valid_baseline = sum(bool(row.get("valid")) for row in baseline)
        valid_candidate = sum(bool(row.get("valid")) for row in candidate)
        if valid_baseline != 1:
            reasons.append("baseline_missing" if not baseline else "baseline_invalid")
            if valid_baseline > 1:
                reasons.append("baseline_duplicate_valid")
        if valid_candidate != 1:
            reasons.append("candidate_missing" if not candidate else "candidate_invalid")
            if valid_candidate > 1:
                reasons.append("candidate_duplicate_valid")
        if reasons:
            incomplete.append({
                "pairKey": key,
                "reasons": reasons,
                "baselineArtifacts": len(baseline),
                "baselineValid": valid_baseline,
                "candidateArtifacts": len(candidate),
                "candidateValid": valid_candidate,
            })
    return {
        "expected": len(expected_keys),
        "complete": not incomplete,
        "incomplete": incomplete,
    }


def arm_completeness(rows: list[dict[str, Any]], expected_keys: list[str]) -> list[dict[str, Any]]:
    """Return expected keys without exactly one valid artifact for an arm."""

    if not expected_keys:
        return []
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("pairKey") in expected_keys:
            by_key[row["pairKey"]].append(row)
    incomplete: list[dict[str, Any]] = []
    for key in expected_keys:
        artifacts = by_key.get(key, [])
        valid = sum(bool(row.get("valid")) for row in artifacts)
        if valid != 1:
            reasons = ["missing" if not artifacts else "invalid"]
            if valid > 1:
                reasons.append("duplicate_valid")
            incomplete.append({
                "arm": None,
                "pairKey": key,
                "reasons": reasons,
                "artifacts": len(artifacts),
                "valid": valid,
            })
    return incomplete


def metric_comparison(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    metric: str,
    seed: int,
    bootstrap: int,
) -> dict[str, Any]:
    baseline_values: list[float] = []
    candidate_values: list[float] = []
    savings: list[float] = []
    for base, candidate in pairs:
        b = number(base["usage"].get(metric))
        c = number(candidate["usage"].get(metric))
        if b is None or c is None:
            continue
        baseline_values.append(b)
        candidate_values.append(c)
        if b > 0:
            savings.append((b - c) / b)
    ci_low, ci_high = bootstrap_interval(savings, seed, bootstrap)
    base_sum = sum(baseline_values)
    candidate_sum = sum(candidate_values)
    pooled = (base_sum - candidate_sum) / base_sum if base_sum else None
    return {
        "pairsWithMetric": len(savings),
        "baselineTotal": compact(base_sum),
        "candidateTotal": compact(candidate_sum),
        "deltaTokens": compact(candidate_sum - base_sum) if baseline_values else None,
        "pooledSavings": compact(pooled),
        "pooledSavingsPercent": compact(pooled * 100) if pooled is not None else None,
        "pairedMeanSavings": compact(statistics.mean(savings)) if savings else None,
        "pairedMedianSavings": compact(statistics.median(savings)) if savings else None,
        "pairedSavingsPercent": compact(statistics.mean(savings) * 100) if savings else None,
        "pairedSavingsCI95": {
            "low": compact(ci_low * 100) if ci_low is not None else None,
            "high": compact(ci_high * 100) if ci_high is not None else None,
            "method": "percentile bootstrap over task/repetition savings",
            "samples": bootstrap if len(savings) > 1 else 0,
        },
    }


def quality_comparison(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    max_task_drop: float,
    max_case_drop: float,
    seed: int,
    bootstrap: int,
) -> dict[str, Any]:
    task_deltas: list[float] = []
    case_deltas: list[float] = []
    wins = losses = 0
    for base, candidate in pairs:
        base_pass = base["evaluation"].get("taskPass")
        candidate_pass = candidate["evaluation"].get("taskPass")
        if isinstance(base_pass, bool) and isinstance(candidate_pass, bool):
            task_deltas.append(float(candidate_pass) - float(base_pass))
            if candidate_pass and not base_pass:
                wins += 1
            elif base_pass and not candidate_pass:
                losses += 1
        base_rate = number(base["evaluation"].get("casePassRate"))
        candidate_rate = number(candidate["evaluation"].get("casePassRate"))
        if base_rate is not None and candidate_rate is not None:
            case_deltas.append(candidate_rate - base_rate)
    task_ci = bootstrap_interval(task_deltas, seed ^ 0xA53C, bootstrap)
    case_ci = bootstrap_interval(case_deltas, seed ^ 0xB17D, bootstrap)
    baseline_task = sum(1 for value in task_deltas if value == 0 or value == 1)
    candidate_task = sum(1 for value in task_deltas if value == 1 or value == 0)
    # The explicit counts below avoid treating missing evaluation values as
    # failures.  The compact rates are computed from observed paired values.
    base_passes = sum(
        bool(base["evaluation"].get("taskPass"))
        for base, candidate in pairs
        if isinstance(base["evaluation"].get("taskPass"), bool)
        and isinstance(candidate["evaluation"].get("taskPass"), bool)
    )
    candidate_passes = sum(
        bool(candidate["evaluation"].get("taskPass"))
        for base, candidate in pairs
        if isinstance(base["evaluation"].get("taskPass"), bool)
        and isinstance(candidate["evaluation"].get("taskPass"), bool)
    )
    task_count = len(task_deltas)
    base_rate = base_passes / task_count if task_count else None
    candidate_rate = candidate_passes / task_count if task_count else None
    task_delta = candidate_rate - base_rate if base_rate is not None and candidate_rate is not None else None
    case_base = []
    case_candidate = []
    for base, candidate in pairs:
        b = number(base["evaluation"].get("casePassRate"))
        c = number(candidate["evaluation"].get("casePassRate"))
        if b is not None and c is not None:
            case_base.append(b)
            case_candidate.append(c)
    case_base_rate = statistics.mean(case_base) if case_base else None
    case_candidate_rate = statistics.mean(case_candidate) if case_candidate else None
    case_delta = case_candidate_rate - case_base_rate if case_base_rate is not None and case_candidate_rate is not None else None
    task_guard = task_delta is not None and task_delta >= -max_task_drop
    case_guard = case_delta is not None and case_delta >= -max_case_drop
    return {
        "paired": len(pairs),
        "taskPairs": task_count,
        "baselineTaskPasses": base_passes,
        "candidateTaskPasses": candidate_passes,
        "baselineTaskPassRate": compact(base_rate),
        "candidateTaskPassRate": compact(candidate_rate),
        "taskPassDelta": compact(task_delta),
        "taskPassDeltaPercent": compact(task_delta * 100) if task_delta is not None else None,
        "taskPassDeltaCI95": {
            "low": compact(task_ci[0] * 100) if task_ci[0] is not None else None,
            "high": compact(task_ci[1] * 100) if task_ci[1] is not None else None,
            "method": "percentile bootstrap over paired task pass indicators",
        },
        "baselineCasePassRate": compact(case_base_rate),
        "candidateCasePassRate": compact(case_candidate_rate),
        "casePassDelta": compact(case_delta),
        "casePassDeltaPercent": compact(case_delta * 100) if case_delta is not None else None,
        "casePassDeltaCI95": {
            "low": compact(case_ci[0] * 100) if case_ci[0] is not None else None,
            "high": compact(case_ci[1] * 100) if case_ci[1] is not None else None,
            "method": "percentile bootstrap over paired per-trial case rates",
        },
        "candidateWins": wins,
        "candidateLosses": losses,
        "mcnemarPValue": compact(mcnemar_p_value(wins, losses)),
        "maxTaskPassDrop": compact(max_task_drop * 100),
        "maxCasePassDrop": compact(max_case_drop * 100),
        "taskGuardPass": task_guard,
        "caseGuardPass": case_guard,
        "pass": task_guard and case_guard,
    }


def compare_pair_group(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    pairing: dict[str, Any],
    baseline_name: str,
    treatment: str,
    target: dict[str, float],
    seed: int,
    bootstrap: int,
) -> dict[str, Any]:
    """Build one overall or stratum-specific candidate comparison."""

    total = metric_comparison(pairs, "inputTotal", seed, bootstrap)
    uncached = metric_comparison(pairs, "inputUncached", seed ^ 0x12A3, bootstrap)
    cached = metric_comparison(pairs, "inputCached", seed ^ 0x29B7, bootstrap)
    quality = quality_comparison(
        pairs,
        target["maxTaskDrop"],
        target["maxCaseDrop"],
        seed,
        bootstrap,
    )
    quality["complete"] = pairing.get("complete", True)
    if not quality["complete"]:
        # The raw deltas over surviving pairs are still useful diagnostics,
        # but they cannot qualify as a quality win when an expected side is
        # missing or errored.
        quality["pass"] = False
    filter_applied = sum(integer(candidate["filter"].get("applied")) or 0 for _, candidate in pairs)
    gc_applied = sum(integer(candidate["gc"].get("applied")) or 0 for _, candidate in pairs)
    filter_actions: Counter[str] = Counter()
    prune_actions: Counter[str] = Counter()
    for _, candidate in pairs:
        filter_actions.update(candidate["filter"].get("actions") or {})
        prune_actions.update(candidate["gc"].get("actions") or {})
    actual_changes = filter_applied + gc_applied
    pooled_total = total.get("pooledSavings")
    observed_band = pooled_total is not None and target["minSavings"] <= pooled_total <= target["maxSavings"]
    lower_bound = total["pairedSavingsCI95"].get("low")
    lower_bound_fraction = lower_bound / 100 if lower_bound is not None else None
    conservative_min = lower_bound_fraction is not None and lower_bound_fraction >= target["minSavings"]
    if pairing.get("complete") is False:
        gate = "INCOMPLETE"
    elif not pairs:
        gate = "INCOMPLETE"
    elif not quality["pass"]:
        gate = "FAIL_QUALITY"
    elif actual_changes == 0:
        gate = "FAIL_NO_CONTEXT_CHANGES"
    elif pooled_total is None or pooled_total < target["minSavings"]:
        gate = "BELOW_TARGET"
    elif pooled_total > target["maxSavings"]:
        gate = "ABOVE_TARGET_BAND"
    else:
        gate = "PASS"
    base_total = sum(number(base["usage"].get("inputTotal")) or 0 for base, _ in pairs)
    candidate_total = sum(number(candidate["usage"].get("inputTotal")) or 0 for _, candidate in pairs)
    base_cached = sum(number(base["usage"].get("inputCached")) or 0 for base, _ in pairs)
    candidate_cached = sum(number(candidate["usage"].get("inputCached")) or 0 for _, candidate in pairs)
    return {
        "baseline": baseline_name,
        "treatment": treatment,
        "pairing": pairing,
        "total": total,
        "uncached": uncached,
        "cached": cached,
        "cacheEffects": {
            "baselineCacheShare": compact(base_cached / base_total) if base_total else None,
            "candidateCacheShare": compact(candidate_cached / candidate_total) if candidate_total else None,
            "cacheShareDelta": compact(candidate_cached / candidate_total - base_cached / base_total)
            if base_total and candidate_total
            else None,
            "cachedInputDelta": compact(candidate_cached - base_cached),
            "uncachedInputDelta": uncached.get("deltaTokens"),
            "interpretation": "Cached input is included in total input; cache reuse is reported separately, not treated as removed work.",
        },
        "quality": quality,
        "actualChanges": {
            "filterEventsApplied": filter_applied,
            "pruneEventsApplied": gc_applied,
            "contextChangeEvents": actual_changes,
            "trialsWithContextChanges": sum(
                bool((candidate["filter"].get("applied") or 0) + (candidate["gc"].get("applied") or 0))
                for _, candidate in pairs
            ),
            "attributionEvidence": actual_changes > 0,
            "filterActionCounts": dict(sorted(filter_actions.items())),
            "pruneActionCounts": dict(sorted(prune_actions.items())),
        },
        "target": {
            "minSavingsPercent": compact(target["minSavings"] * 100),
            "maxSavingsPercent": compact(target["maxSavings"] * 100),
            "pooledSavingsPercent": total.get("pooledSavingsPercent"),
            "pairedSavingsCI95": total.get("pairedSavingsCI95"),
            "observedWithinBand": observed_band,
            "conservativeLowerBoundAtLeastMinimum": conservative_min,
            "gate": gate,
            "qualityGuardPass": quality["pass"],
            "mechanismEvidence": actual_changes > 0,
        },
    }


def pair_records(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        {
            "pairKey": base["pairKey"],
            "task": base["task"],
            "repetition": base["repetition"],
            "stratum": base.get("stratum"),
            "baselineId": base["id"],
            "candidateId": candidate["id"],
            "baselineInputTotal": base["usage"].get("inputTotal"),
            "candidateInputTotal": candidate["usage"].get("inputTotal"),
            "totalSavingsPercent": compact(
                (1 - candidate["usage"]["inputTotal"] / base["usage"]["inputTotal"]) * 100
            )
            if number(base["usage"].get("inputTotal")) is not None
            and number(candidate["usage"].get("inputTotal")) is not None
            and number(base["usage"].get("inputTotal")) > 0
            else None,
            "baselineTaskPass": base["evaluation"].get("taskPass"),
            "candidateTaskPass": candidate["evaluation"].get("taskPass"),
            "candidateFilterEventsApplied": candidate["filter"].get("applied"),
            "candidatePruneEventsApplied": candidate["gc"].get("applied"),
        }
        for base, candidate in pairs
    ]


def design_target(design: dict[str, Any], args: argparse.Namespace) -> dict[str, float]:
    target = design.get("targetSavings") or design.get("tokenSavingsTarget") or {}
    if not isinstance(target, dict):
        target = {}
    minimum = normalize_fraction(
        args.min_savings if args.min_savings is not None else target.get("min", target.get("minimum", target.get("minPercent"))),
        DEFAULT_MIN_SAVINGS,
    )
    maximum = normalize_fraction(
        args.max_savings if args.max_savings is not None else target.get("max", target.get("maximum", target.get("maxPercent"))),
        DEFAULT_MAX_SAVINGS,
    )
    quality = design.get("qualityGuard") or {}
    if not isinstance(quality, dict):
        quality = {}
    max_task = normalize_fraction(
        args.max_task_drop if args.max_task_drop is not None else quality.get("maxTaskPassDrop"),
        DEFAULT_MAX_TASK_DROP,
    )
    max_case = normalize_fraction(
        args.max_case_drop if args.max_case_drop is not None else quality.get("maxCasePassDrop"),
        DEFAULT_MAX_CASE_DROP,
    )
    return {
        "minSavings": minimum,
        "maxSavings": maximum,
        "maxTaskDrop": max_task,
        "maxCaseDrop": max_case,
    }


def compact_trial(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "task": row.get("task"),
        "repetition": row.get("repetition"),
        "stratum": row.get("stratum"),
        "arm": row.get("arm"),
        "pairKey": row.get("pairKey"),
        "valid": row.get("valid"),
        "error": row.get("error"),
        "missing": row.get("missing", []),
        "usage": row.get("usage"),
        "evaluation": row.get("evaluation"),
        "filter": row.get("filter"),
        "gc": row.get("gc"),
        "judge": row.get("judge"),
        "wallMs": row.get("wallMs"),
        "path": row.get("path"),
    }


def build_analysis(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    design, design_arms, repeats, tasks, task_strata = parse_design(root)
    trials = discover_trials(root)
    for row in trials:
        if row.get("stratum") is None:
            row["stratum"] = task_strata.get(row.get("task"))
    discovered_arms = sorted({row["arm"] for row in trials if row.get("arm")})
    arm_names = list(dict.fromkeys(design_arms + discovered_arms))
    baseline_name = args.baseline
    if baseline_name not in arm_names and arm_names:
        baseline_name = arm_names[0]
    if args.treatments:
        treatment_names = list(dict.fromkeys(args.treatments))
    else:
        treatment_names = [name for name in arm_names if name != baseline_name]
    arm_names = list(dict.fromkeys(arm_names + treatment_names + [baseline_name]))
    expected = repeats * len(tasks) if repeats is not None and tasks else None
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trials:
        by_arm[row["arm"]].append(row)
    target = design_target(design, args)
    has_strata = bool(task_strata or any(row.get("stratum") for row in trials))
    expected_by_stratum: dict[str, int | None] = {}
    if has_strata and repeats is not None and tasks:
        stratum_task_counts = Counter(task_strata.get(task, "(unclassified)") for task in tasks)
        expected_by_stratum = {
            label: repeats * count for label, count in stratum_task_counts.items()
        }
    observed_strata = {
        row.get("stratum") or "(unclassified)" for row in trials
    } if has_strata else set()
    stratum_labels = sorted(set(expected_by_stratum) | observed_strata)
    arm_summary = {}
    for name in arm_names:
        summary = summarize_arm(by_arm.get(name, []), expected)
        summary["strata"] = summarize_arm_strata(by_arm.get(name, []), expected_by_stratum)
        arm_summary[name] = summary
    baseline_rows = by_arm.get(baseline_name, [])
    expected_pairs = []
    if repeats is not None and tasks:
        expected_pairs = [f"{task}::r{repetition}" for task in tasks for repetition in range(repeats)]
    expected_pairs_by_stratum: dict[str, list[str]] = defaultdict(list)
    if expected_pairs and has_strata:
        for task in tasks:
            label = task_strata.get(task, "(unclassified)")
            expected_pairs_by_stratum[label].extend(
                f"{task}::r{repetition}" for repetition in range(repeats or 0)
            )
    comparisons: dict[str, Any] = {}
    all_pairs: dict[str, Any] = {}
    stratum_pairs: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for treatment in treatment_names:
        candidate_rows = by_arm.get(treatment, [])
        comparison_baseline_rows = filter_expected_rows(baseline_rows, expected_pairs)
        comparison_candidate_rows = filter_expected_rows(candidate_rows, expected_pairs)
        pairs, pairing = pair_rows(comparison_baseline_rows, comparison_candidate_rows)
        pairing.update(pair_completeness(baseline_rows, candidate_rows, expected_pairs))
        seed = sum(ord(char) for char in treatment) + len(pairs) * 1009
        comparisons[treatment] = compare_pair_group(
            pairs, pairing, baseline_name, treatment, target, seed, args.bootstrap
        )
        comparisons[treatment]["strata"] = {}
        stratum_pairs[treatment] = {}
        for label in stratum_labels:
            baseline_stratum = [
                row for row in baseline_rows
                if (row.get("stratum") or "(unclassified)") == label
            ]
            candidate_stratum = [
                row for row in candidate_rows
                if (row.get("stratum") or "(unclassified)") == label
            ]
            stratum_expected = expected_pairs_by_stratum.get(label, [])
            baseline_stratum_for_pairing = filter_expected_rows(baseline_stratum, stratum_expected)
            candidate_stratum_for_pairing = filter_expected_rows(candidate_stratum, stratum_expected)
            stratum_pair_rows, stratum_pairing = pair_rows(
                baseline_stratum_for_pairing, candidate_stratum_for_pairing
            )
            stratum_pairing.update(
                pair_completeness(baseline_stratum, candidate_stratum, stratum_expected)
            )
            stratum_seed = seed ^ sum((index + 1) * ord(char) for index, char in enumerate(label))
            comparisons[treatment]["strata"][label] = compare_pair_group(
                stratum_pair_rows,
                stratum_pairing,
                baseline_name,
                treatment,
                target,
                stratum_seed,
                args.bootstrap,
            )
            stratum_pairs[treatment][label] = pair_records(stratum_pair_rows)
        stratum_quality_failures = [
            label
            for label, stratum_comparison in comparisons[treatment]["strata"].items()
            if stratum_comparison["pairing"].get("complete", True)
            and stratum_comparison["quality"].get("paired", 0)
            and not stratum_comparison["quality"].get("pass")
        ]
        stratum_incomplete = [
            label
            for label, stratum_comparison in comparisons[treatment]["strata"].items()
            if stratum_comparison["pairing"].get("complete") is False
        ]
        comparisons[treatment]["quality"]["stratumGuardPass"] = not stratum_quality_failures
        comparisons[treatment]["quality"]["stratumQualityFailures"] = stratum_quality_failures
        comparisons[treatment]["quality"]["stratumGuardComplete"] = not stratum_incomplete
        comparisons[treatment]["quality"]["stratumQualityIncomplete"] = stratum_incomplete
        if stratum_quality_failures:
            comparisons[treatment]["quality"]["pass"] = False
            comparisons[treatment]["target"]["qualityGuardPass"] = False
            comparisons[treatment]["target"]["gate"] = "FAIL_QUALITY_STRATUM"
        all_pairs[treatment] = pair_records(pairs)
    expected_arms = arm_names
    observed_pairs_by_arm: dict[str, set[str]] = defaultdict(set)
    for row in trials:
        if row.get("pairKey") is not None and row.get("arm") is not None:
            observed_pairs_by_arm[row["arm"]].add(row["pairKey"])
        if row.get("task") is not None and row.get("repetition") is not None and row.get("arm") is not None:
            observed_pairs_by_arm[row["arm"]].add(f"{row['task']}::r{row['repetition']}")
    missing_expected = [
        {"arm": arm, "pairKey": pair_key}
        for arm in expected_arms
        for pair_key in expected_pairs
        if pair_key not in observed_pairs_by_arm.get(arm, set())
    ]
    incomplete_expected: list[dict[str, Any]] = []
    for arm in expected_arms:
        for item in arm_completeness(by_arm.get(arm, []), expected_pairs):
            item["arm"] = arm
            incomplete_expected.append(item)
    validity = {
        "designPresent": bool(design),
        "expectedArms": expected_arms,
        "discoveredArms": discovered_arms,
        "expectedRepeats": repeats,
        "expectedTasks": tasks,
        "expectedTrialsPerArm": expected,
        "totalArtifacts": len(trials),
        "validArtifacts": sum(row["valid"] for row in trials),
        "invalidArtifacts": sum(not row["valid"] for row in trials),
        "invalidIds": [row["id"] for row in trials if not row["valid"]],
        "missingExpected": missing_expected,
        "missingExpectedCount": len(missing_expected),
        "incompleteExpected": incomplete_expected,
        "incompleteExpectedCount": len(incomplete_expected),
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": str(root),
        "baseline": baseline_name,
        "treatments": treatment_names,
        "strata": stratum_labels,
        "taskStrata": task_strata,
        "targetConfig": {
            "minSavingsPercent": compact(target["minSavings"] * 100),
            "maxSavingsPercent": compact(target["maxSavings"] * 100),
            "maxTaskPassDropPercent": compact(target["maxTaskDrop"] * 100),
            "maxCasePassDropPercent": compact(target["maxCaseDrop"] * 100),
            "bootstrapSamples": args.bootstrap,
        },
        "validity": validity,
        "arms": arm_summary,
        "comparisons": comparisons,
        "pairedTrials": all_pairs,
        "pairedTrialsByStratum": stratum_pairs,
        "trials": [compact_trial(row) for row in trials],
    }


def fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return f"{value:,.{digits}f}" if isinstance(value, float) and not value.is_integer() else f"{int(value):,}"
    return str(value)


def pct(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{float(value):+,.{digits}f}%"


def generate_report(analysis: dict[str, Any]) -> str:
    validity = analysis["validity"]
    arms = analysis["arms"]
    comparisons = analysis["comparisons"]
    target = analysis["targetConfig"]
    lines = [
        "# General coding Pi benchmark analysis",
        "",
        "This report compares each candidate with the baseline task and repetition pair. Input tokens include cached and uncached tokens across every model request.",
        "",
        f"Artifacts: {validity['totalArtifacts']} discovered, {validity['validArtifacts']} valid, {validity['invalidArtifacts']} incomplete or failed, {validity.get('missingExpectedCount', 0)} expected pair artifacts missing, {validity.get('incompleteExpectedCount', 0)} expected arm/pair entries invalid or incomplete.",
        f"Target band: {fmt(target['minSavingsPercent'], 1)}% to {fmt(target['maxSavingsPercent'], 1)}% total input savings; quality guard allows at most {fmt(target['maxTaskPassDropPercent'], 1)} percentage points of task pass loss and {fmt(target['maxCasePassDropPercent'], 1)} points of case pass loss.",
        "",
        "## Arm totals",
        "",
        "| Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input | Applied filters | Applied prunes | Cache share |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, summary in arms.items():
        task_rate = summary.get("taskPassRate")
        case_rate = summary.get("casePassRate")
        lines.append(
            f"| {name} | {summary['validTrials']}/{summary.get('expectedTrials') or '—'} | "
            f"{summary['taskPasses']}/{summary['validTrials']} ({fmt(task_rate * 100 if task_rate is not None else None, 1)}%) | "
            f"{fmt(summary['testsPassed'])}/{fmt(summary['testsTotal'])} ({fmt(case_rate * 100 if case_rate is not None else None, 1)}%) | "
            f"{fmt(summary['inputTotal'])} | {fmt(summary['inputUncached'])} | {fmt(summary['inputCached'])} | "
            f"{fmt(summary['filterEventsApplied'])} | {fmt(summary['pruneEventsApplied'])} | "
            f"{fmt(summary['cacheShare'] * 100 if summary.get('cacheShare') is not None else None, 1)}% |"
        )
    strata = analysis.get("strata") or []
    if strata:
        lines.extend(
            [
                "",
                "## Arm totals by stratum",
                "",
                "Strata come from `result.stratum`; when a result omits it, the analyzer uses the task metadata in `design.json`.",
                "",
                "| Stratum | Arm | Valid trials | Task passes | Case checks | Total input | Uncached input | Cached input |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for label in strata:
            for name, summary in arms.items():
                stratum_summary = (summary.get("strata") or {}).get(label, {})
                task_rate = stratum_summary.get("taskPassRate")
                case_rate = stratum_summary.get("casePassRate")
                lines.append(
                    f"| {label} | {name} | {stratum_summary.get('validTrials', 0)}/{stratum_summary.get('expectedTrials') or '—'} | "
                    f"{stratum_summary.get('taskPasses', 0)}/{stratum_summary.get('validTrials', 0)} ({fmt(task_rate * 100 if task_rate is not None else None, 1)}%) | "
                    f"{fmt(stratum_summary.get('testsPassed'))}/{fmt(stratum_summary.get('testsTotal'))} ({fmt(case_rate * 100 if case_rate is not None else None, 1)}%) | "
                    f"{fmt(stratum_summary.get('inputTotal'))} | {fmt(stratum_summary.get('inputUncached'))} | {fmt(stratum_summary.get('inputCached'))} |"
                )
    lines.extend(
        [
            "",
            "## Intervention actions",
            "",
            "These counts come from applied context events. Judge calls that left context unchanged are reported as overhead and do not appear here.",
            "",
            "| Arm | Applied intervention events | Filter action counts | Prune action counts |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for name, summary in arms.items():
        lines.append(
            f"| {name} | {fmt(summary.get('interventionEventsApplied'))} | "
            f"`{json.dumps(summary.get('filterActions') or {}, sort_keys=True)}` | "
            f"`{json.dumps(summary.get('pruneActions') or {}, sort_keys=True)}` |"
        )
    lines.extend(
        [
            "",
            "## Paired comparisons",
            "",
            "Savings are `(baseline − candidate) / baseline`; positive values mean fewer tokens. The interval is a percentile bootstrap over task/repetition pairs. Cached and uncached input are shown independently.",
            "",
            "| Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Applied filter/prune events | Gate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for name, comparison in comparisons.items():
        total = comparison["total"]
        uncached = comparison["uncached"]
        cached = comparison["cached"]
        quality = comparison["quality"]
        actions = comparison["actualChanges"]
        ci = total["pairedSavingsCI95"]
        ci_text = f"{pct(total.get('pooledSavingsPercent'))} [{pct(ci.get('low'))}, {pct(ci.get('high'))}]"
        lines.append(
            f"| {name} | {comparison['pairing']['paired']} | {ci_text} | {pct(uncached.get('pooledSavingsPercent'))} | {pct(cached.get('pooledSavingsPercent'))} | "
            f"{pct(quality.get('taskPassDeltaPercent'))} | {pct(quality.get('casePassDeltaPercent'))} | "
            f"{actions['filterEventsApplied']}/{actions['pruneEventsApplied']} | **{comparison['target']['gate']}** |"
        )
    if not comparisons:
        lines.extend(["| — | 0 | — | — | — | — | — | — | INCOMPLETE |"])
    if strata:
        lines.extend(
            [
                "",
                "## Paired comparisons by stratum",
                "",
                "This breakdown keeps task/repetition pairing within each stratum. It exposes whether a short-task or long-task result drives the overall estimate.",
                "",
                "| Stratum | Candidate | Pairs | Total savings | Uncached savings | Cached savings | Task pass delta | Case pass delta | Gate |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for label in strata:
            for name, comparison in comparisons.items():
                stratum_comparison = (comparison.get("strata") or {}).get(label)
                if not stratum_comparison:
                    continue
                quality = stratum_comparison["quality"]
                lines.append(
                    f"| {label} | {name} | {stratum_comparison['pairing']['paired']} | "
                    f"{pct(stratum_comparison['total'].get('pooledSavingsPercent'))} | "
                    f"{pct(stratum_comparison['uncached'].get('pooledSavingsPercent'))} | "
                    f"{pct(stratum_comparison['cached'].get('pooledSavingsPercent'))} | "
                    f"{pct(quality.get('taskPassDeltaPercent'))} | {pct(quality.get('casePassDeltaPercent'))} | "
                    f"**{stratum_comparison['target']['gate']}** |"
                )
    lines.extend(
        [
            "",
            "## Quality guard and cache effects",
            "",
        ]
    )
    for name, comparison in comparisons.items():
        quality = comparison["quality"]
        cache = comparison["cacheEffects"]
        target_data = comparison["target"]
        quality_status = "INCOMPLETE" if quality.get("complete") is False else ("PASS" if quality.get("pass") else "FAIL")
        stratum_quality_status = "INCOMPLETE" if quality.get("stratumGuardComplete") is False else ("PASS" if quality.get("stratumGuardPass") else "FAIL")
        lines.extend(
            [
                f"### {name}",
                "",
                f"Task pass rate: {fmt(quality.get('baselineTaskPassRate') * 100 if quality.get('baselineTaskPassRate') is not None else None, 1)}% baseline versus {fmt(quality.get('candidateTaskPassRate') * 100 if quality.get('candidateTaskPassRate') is not None else None, 1)}% candidate ({pct(quality.get('taskPassDeltaPercent'))}). McNemar discordance: {quality.get('candidateWins', 0)} candidate wins, {quality.get('candidateLosses', 0)} losses, p={fmt(quality.get('mcnemarPValue'), 3)}.",
                f"Case pass rate delta: {pct(quality.get('casePassDeltaPercent'))}; overall quality guard: {quality_status}; stratum quality guard: {stratum_quality_status}.",
                f"Cache share: {fmt(cache.get('baselineCacheShare') * 100 if cache.get('baselineCacheShare') is not None else None, 1)}% baseline versus {fmt(cache.get('candidateCacheShare') * 100 if cache.get('candidateCacheShare') is not None else None, 1)}% candidate; cached input delta {fmt(cache.get('cachedInputDelta'))} tokens and uncached input delta {fmt(cache.get('uncachedInputDelta'))} tokens.",
                f"Target gate: **{target_data.get('gate')}**. Observed band={target_data.get('observedWithinBand')}, conservative lower bound at least minimum={target_data.get('conservativeLowerBoundAtLeastMinimum')}, mechanism evidence={target_data.get('mechanismEvidence')}.",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "A lower cached count does not by itself establish savings: cached input is still included in total input. Attribute a candidate's reduction to the harness only when its filter or prune event count is positive. Independent model generations can change output length and tool usage, so the paired interval and event counts belong in the same conclusion.",
            "",
            "The quality guard is an observed guard over paired executions, not a proof of equal production accuracy. Small task sets can make the uncertainty interval wide. Provider errors and missing evaluation artifacts remain in the validity section and are excluded from completed-trial totals.",
            "",
        ]
    )
    if validity["invalidArtifacts"]:
        lines.extend(["Incomplete artifacts:", ""])
        for trial in analysis["trials"]:
            if not trial.get("valid"):
                lines.append(f"- `{trial['id']}`: {trial.get('error') or ', '.join(trial.get('missing', []))}")
        lines.append("")
    if validity.get("missingExpectedCount"):
        lines.extend(["Missing expected pair artifacts:", ""])
        for item in validity["missingExpected"]:
            lines.append(f"- `{item['arm']}` / `{item['pairKey']}`")
        lines.append("")
    if validity.get("incompleteExpectedCount"):
        lines.extend(["Invalid or incomplete expected arm/pair entries:", ""])
        for item in validity["incompleteExpected"]:
            reason = ", ".join(item.get("reasons", []))
            lines.append(f"- `{item['arm']}` / `{item['pairKey']}`: {reason}")
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="completed benchmark output directory")
    parser.add_argument("--baseline", default="baseline")
    parser.add_argument("--treatments", nargs="*", help="candidate arms; defaults to every discovered non-baseline arm")
    parser.add_argument("--min-savings", type=float, help="target minimum savings, as percent or fraction")
    parser.add_argument("--max-savings", type=float, help="target maximum savings, as percent or fraction")
    parser.add_argument("--max-task-drop", type=float, help="allowed task pass loss, as percentage points or fraction")
    parser.add_argument("--max-case-drop", type=float, help="allowed hidden-case pass loss, as percentage points or fraction")
    parser.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--check-gate", action="store_true", help="exit nonzero when a selected candidate is incomplete or fails its gate")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = args.directory.resolve()
    if not root.is_dir():
        print(f"benchmark directory does not exist: {root}", file=sys.stderr)
        return 2
    if args.bootstrap < 0:
        print("--bootstrap must be nonnegative", file=sys.stderr)
        return 2
    analysis = build_analysis(root, args)
    json_path = (args.json_out or (root / "general-analysis.json")).resolve()
    report_path = (args.report_out or (root / "GENERAL_REPORT.md")).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(analysis, indent=2) + "\n")
    report_path.write_text(generate_report(analysis))
    print(json.dumps({
        "directory": str(root),
        "json": str(json_path),
        "report": str(report_path),
        "arms": analysis["arms"],
        "gates": {name: item["target"]["gate"] for name, item in analysis["comparisons"].items()},
    }, indent=2))
    if args.check_gate:
        if (
            analysis["validity"]["invalidArtifacts"]
            or analysis["validity"].get("missingExpectedCount")
            or analysis["validity"].get("incompleteExpectedCount")
        ):
            return 1
        if any(item["target"]["gate"] not in {"PASS", "ABOVE_TARGET_BAND"} for item in analysis["comparisons"].values()):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
