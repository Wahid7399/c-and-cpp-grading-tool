import os, re, shutil, subprocess, shlex
import json

def run_individual_tests(docker, image, input_path, per_test_timeout=15):
    workdir = f"cd doctest; "
    exe = "./doctest_executable.out"

    logs = []
    failed = []
    passed = []

    # 1) Get test list
    try:
        result = docker.run(
            image, input_path, f'{workdir}{exe} --list-test-cases --no-colors', 60
        )
        list_output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        combined = "Listing test cases timed out"
        _cleanup(input_path)
        return False, combined, combined
    except Exception as e:
        combined = f"Failed to list test cases: {type(e).__name__}: {e}"
        _cleanup(input_path)
        return False, combined, combined

    # Extract case names (doctest prints one name per line)
    case_names = [line.strip() for line in list_output.splitlines() if line.strip()]
    # doctest also prints a header sometimes; keep only lines that look like case names
    # (heuristic: ignore lines that contain ':' or spaces around 'cases:' etc.)
    # case_names = [c for c in case_names if not re.search(r'cases?:|assertions?:|skipped|pass|fail|doctest version', c, re.I)]
    # case names start with '#'
    case_names = [c for c in case_names if re.match(r'#\d+', c)]

    if not case_names:
        combined = "No test cases found.\n" + list_output
        _cleanup(input_path)
        return False, combined, combined

    # 2) Run each case in isolation
    for case in case_names:
        run_single_case(
            case, docker, image, logs, passed, failed,
            input_path, workdir, exe, per_test_timeout
        )
    # with ThreadPoolExecutor(max_workers=4) as executor:
    #     futures = {executor.submit(
    #         run_single_case,
    #         case, docker, image, logs, passed, failed,
    #         input_path, workdir, exe, per_test_timeout
    #     ): case for case in case_names}
    #     for future in as_completed(futures):
    #         try:
    #             future.result()
    #         except Exception as e:
    #             logs.append(f"Error running test case {futures[future]}: {e}")
    #             failed.append({
    #                 "number": 0,
    #                 "name": futures[future],
    #                 "score": 0,
    #                 "failed_check": "Runtime error",
    #                 "failed_value": "Runtime error"
    #             })

    # 3) Summarize and write combined log
    summary = []
    summary.append("=== SUMMARY ===")
    summary.append(f"Total cases: {len(case_names)}")
    summary.append(f"Passed: {len(passed)}")
    summary.append(f"Failed: {len(failed)}")
    if failed:   summary.append("Failed cases:\n  - " + json.dumps(failed, indent=2))
    summary_text = "\n".join(summary)

    combined_log = summary_text + "\n\n" + "\n".join(logs)

    # Return True if we executed successfully (even with failing tests);
    # False only if we couldn't run the suite at all.
    _cleanup(input_path)

    summary = {
        "total_cases": len(case_names),
        "passed": len(passed),
        "failed": len(failed),
        "total_score": sum(f["score"] for f in failed) + sum(f["score"] for f in passed),
        "obtained_score": sum(f["score"] for f in passed),
        "failures": sorted(failed, key=lambda x: x["number"])
    }

    scores = {}
    for case in case_names:
        m = re.match(r'#(\d+)', case)
        num = int(m.group(1)) if m else 0
        scores[f"test_case_{num}"] = 0
    for p in passed:
        scores[f"test_case_{p['number']}"] = p['score']

    return True, {
        "summary": summary,
        "scores": scores,
    }, combined_log

def _cleanup(input_path):
    shutil.rmtree(os.path.join(input_path, "doctest"), ignore_errors=True)

def run_single_case(case, docker, image, logs, passed, failed, input_path, workdir, exe, per_test_timeout):
    # Use "#N *" wildcard so the comma in "Score: N" isn't treated as a
    # doctest filter separator (commas separate multiple filter patterns).
    number = int(re.match(r'#(\d+)', case).group(1) if re.match(r'#(\d+)', case) else "0")
    score = int(re.search(r'Score:\s+(\d+)', case).group(1) if re.search(r'Score:\s+(\d+)', case) else "0")
    case_filter = shlex.quote(f"#{number} *")
    cmd = (f'{workdir}{exe} '
            f'--test-case={case_filter} --no-breaks --abort-after=0 --no-colors')
    case_dict = { "number": number, "name": case, "score": score }
    try:
        res = docker.run(image, input_path, cmd, per_test_timeout)
        out = (res.stdout or "") + "\n" + (res.stderr or "")
        logs.append(out)
        # Detect process crashes (SIGSEGV, SIGABRT, etc.): doctest exits 0 on
        # full pass, 1 on test failures; anything else means the process crashed.
        if res.returncode not in (0, 1):
            snippet = out.strip()[-500:] if out.strip() else f"Exit code {res.returncode}"
            case_dict['failed_check'] = "Runtime error"
            case_dict['failed_value'] = snippet
            failed.append(case_dict)
            return
        # Parse doctest footer: "test cases: T | P passed | F failed | S skipped"
        footer = re.search(
            r'test cases:\s*(\d+)\s*\|\s*(\d+)\s*passed\s*\|\s*(\d+)\s*failed\s*\|\s*(\d+)\s*skipped',
            out
        )
        if footer and int(footer.group(2)) == 0 and int(footer.group(3)) == 0 and int(footer.group(4)) > 0:
            # Filter didn't match any test case — treat as failure
            case_dict['failed_check'] = "Test case not found (skipped)"
            case_dict['failed_value'] = "Filter did not match any test case"
            failed.append(case_dict)
        elif re.search(r'\bStatus:\s*SUCCESS\b', out):
            passed.append(case_dict)
        elif re.search(r'\bStatus:\s*FAILURE\b', out) or re.search(r'\bfailed\b', out, re.I):
            fail_pattern = re.compile(
                r"TEST CASE:\s+#(\d+)\s+(.*?)\. Score:\s+(\d+).*?"
                r"ERROR: CHECK\(\s*(.*?)\s*\) is NOT correct!.*?"
                r"values:\s+CHECK\(\s*(.*?)\s*\)",
                re.S
            )
            for match in fail_pattern.finditer(out):
                if not case_dict.get('failed_check'):
                    case_dict["failed_check"] = str(match.group(4).strip())
                    case_dict["failed_value"] = str(match.group(5).strip())
                case_dict['failed_check'] += f"; {match.group(4).strip()}"
                case_dict['failed_value'] += f"; {match.group(5).strip()}"
            if not case_dict.get('failed_check'):
                pattern = r'doctest_main\.cpp:\d+:\s*(.*)'
                matches = re.findall(pattern, out)
                if len(matches) >= 2:
                    case_dict['failed_check'] = matches[1].strip()
                    case_dict['failed_value'] = "Unknown"
            failed.append(case_dict)
        else:
            passed.append(case_dict)
    except subprocess.TimeoutExpired:
        case_dict['failed_check'] = "Timed out"
        case_dict['failed_value'] = "Timed out"
        failed.append(case_dict)
        logs.append(f'{case}\nTIMED OUT\n')
    except Exception as e:
        case_dict['failed_check'] = "Runtime error"
        case_dict['failed_value'] = f"{type(e).__name__}: {e}"
        failed.append(case_dict)
        logs.append(f'{case}\nEXCEPTION: {type(e).__name__}: {e}\n')
