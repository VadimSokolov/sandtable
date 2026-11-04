"""Isolated job process: one real run or a declared seeded experiment."""

from pathlib import Path
import copy, json, math, os, statistics, sys, time, traceback
from .api import compile_config, comparison_design, digest
from .simulation import run, Cancelled
from .serialization import clean
from .provenance import provenance
from scipy.stats import t as student_t
from .studies import verify_definition
from .analytics import diagnostics, summarize, statistics_report
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import multiprocessing


def write(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(clean(value), allow_nan=False))
    os.replace(temp, path)


def study_run(folder, arm, seed, index, prov):
    """Isolated process: process-local patches must never share a thread."""
    folder = Path(folder)
    compiled = copy.deepcopy(arm["compiled"])
    compiled["config"]["mission"]["seed"] = seed
    compiled["config_hash"] = digest(compiled["config"])

    def progress(fraction, tick):
        write(
            folder / f"active-{index:03d}.json",
            dict(arm=arm["name"], seed=seed, fraction=fraction, tick=tick),
        )

    a = run(compiled, seed, progress=progress, cancel=lambda: (folder / "cancel").exists())
    a["provenance"] = prov
    a["arm"] = arm["name"]
    a["outcome"].update(diagnostics(a))
    filename = f"run-{index:03d}.json"
    write(folder / filename, a)
    return dict(
        index=index,
        file=filename,
        arm=arm["name"],
        seed=seed,
        outcome=a["outcome"],
        configuration_hash=a["config_hash"],
        summary=a["summary"],
        end_reason=a["end_reason"],
    )


def execute_study(folder, req, status, prov):
    study = req["study"]
    arms = verify_definition(study)
    seeds = study["seeds"]
    total = len(arms) * len(seeds)
    status.update(
        total=total,
        execution_workers=4,
        message="Running 12 saved scenarios in four isolated processes",
    )
    write(folder / "design.json", study)
    write(folder / "status.json", status)
    rows = []
    with ProcessPoolExecutor(
        max_workers=4, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        pending = {}
        index = 0
        for arm in arms:
            for seed in seeds:
                pending[pool.submit(study_run, str(folder), arm, seed, index, prov)] = index
                index += 1
        try:
            while pending:
                if (folder / "cancel").exists():
                    raise Cancelled()
                done, _ = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                for future in done:
                    pending.pop(future)
                    rows.append(future.result())
                    rows.sort(key=lambda r: r["index"])
                if done:
                    write(
                        folder / "partial.json",
                        dict(
                            kind="study",
                            study_id=study["id"],
                            design_hash=study["design_hash"],
                            runs=rows,
                            provenance=prov,
                            complete=False,
                        ),
                    )
                status.update(
                    completed=len(rows),
                    fraction=len(rows) / total,
                    message=f"{len(rows)}/{total} saved; four isolated Python workers",
                )
                write(folder / "status.json", status)
        except BaseException:
            (folder / "cancel").touch()
            for future in pending:
                future.cancel()
            raise
    result = dict(
        kind="study",
        study_id=study["id"],
        design_hash=study["design_hash"],
        complete=True,
        runs=rows,
        provenance=prov,
        study_summary=summarize(rows, study),
    )
    write(folder / "result.json", result)
    status.update(
        state="complete",
        fraction=1,
        completed=total,
        message="All 240 missions complete",
        finished=time.time(),
    )
    write(folder / "status.json", status)


def main(folder):
    folder = Path(folder)
    req = json.loads((folder / "request.json").read_text())
    status = dict(
        id=folder.name,
        kind=req["kind"],
        state="running",
        fraction=0,
        completed=0,
        total=1,
        message="Loading Sandtable",
        started=time.time(),
    )
    write(folder / "status.json", status)
    try:
        prov = provenance()
        write(folder / "provenance.json", prov)
        if req["kind"] == "study":
            execute_study(folder, req, status, prov)
            return
        if req["kind"] == "run":
            compiled = compile_config(req["config"])
            arms = [dict(name="mission", compiled=compiled)]
            seeds = [compiled["config"]["mission"]["seed"]]
            design = None
        else:
            design = comparison_design(req["config"], req["design"])
            arms = design["arms"]
            seeds = design["seeds"]
            write(
                folder / "design.json",
                dict(
                    parameter=design["parameter"],
                    basis=design["basis"],
                    seeds=seeds,
                    arms=[
                        dict(
                            name=a["name"],
                            configuration=a["compiled"]["config"],
                            resolved_summary=a["compiled"]["summary"],
                            configuration_hash=a["compiled"]["config_hash"],
                        )
                        for a in arms
                    ],
                    warnings=design["warnings"],
                ),
            )
        total = len(arms) * len(seeds)
        status["total"] = total
        rows = []
        i = 0
        for arm in arms:
            for seed in seeds:
                if (folder / "cancel").exists():
                    raise Cancelled()
                status.update(
                    message=f"{arm['name']} · seed {seed}", active_arm=arm["name"], active_seed=seed
                )

                def progress(fraction, tick):
                    status.update(fraction=(i + fraction) / total, completed=i, tick=tick)
                    write(folder / "status.json", status)

                compiled = copy.deepcopy(arm["compiled"])
                compiled["config"]["mission"]["seed"] = seed
                compiled["config_hash"] = digest(compiled["config"])
                artifact = run(
                    compiled, seed, progress=progress, cancel=lambda: (folder / "cancel").exists()
                )
                artifact["provenance"] = prov
                artifact["arm"] = arm["name"]
                filename = f"run-{i:03d}.json"
                write(folder / filename, artifact)
                rows.append(
                    dict(
                        index=i,
                        file=filename,
                        arm=arm["name"],
                        seed=seed,
                        outcome=artifact["outcome"],
                        configuration_hash=artifact["config_hash"],
                        summary=artifact["summary"],
                        end_reason=artifact["end_reason"],
                    )
                )
                i += 1
                status.update(
                    completed=i, fraction=i / total, tick=artifact["outcome"]["mission_time"]
                )
                write(folder / "status.json", status)
        result = dict(kind=req["kind"], runs=rows, provenance=prov)
        if design:
            result.update(
                statistics=statistics_report(rows, design),
                basis=design["basis"],
                parameter=design["parameter"],
                seeds=seeds,
                warnings=design["warnings"],
            )
        write(folder / "result.json", result)
        status.update(
            state="complete", fraction=1, completed=total, message="Complete", finished=time.time()
        )
        write(folder / "status.json", status)
    except Cancelled:
        status.update(
            state="cancelled",
            message="Cancelled. Completed artifacts, if any, are retained; no complete comparison is claimed.",
            finished=time.time(),
        )
        write(folder / "status.json", status)
    except Exception as e:
        (folder / "error.log").write_text(traceback.format_exc())
        status.update(state="failed", message=str(e), finished=time.time())
        write(folder / "status.json", status)


if __name__ == "__main__":
    main(sys.argv[1])
