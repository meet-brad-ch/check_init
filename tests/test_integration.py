"""Integration tests — scan fixture files end-to-end."""

import os

from check_init.scanner import scan_file

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _scan_fixture(name: str, check_members: bool = False):
    path = os.path.join(FIXTURES_DIR, name)
    with open(path) as f:
        source = f.read()
    return scan_file(source, path, check_members=check_members)


class TestFixtureIntegration:
    def test_good_file_clean(self):
        result = _scan_fixture("good.cpp")
        assert len(result.findings) == 0, "good.cpp should have 0 findings, got: " + "\n".join(
            str(f) for f in result.findings
        )

    def test_bad_locals_count(self):
        result = _scan_fixture("bad_locals.cpp")
        # 19 variables in the fixture
        assert (
            len(result.findings) == 19
        ), f"Expected 19 findings, got {len(result.findings)}: " + "\n".join(
            str(f) for f in result.findings
        )

    def test_bad_arrays_count(self):
        result = _scan_fixture("bad_arrays.cpp")
        assert (
            len(result.findings) == 6
        ), f"Expected 6 findings, got {len(result.findings)}: " + "\n".join(
            str(f) for f in result.findings
        )

    def test_bad_members_without_flag(self):
        result = _scan_fixture("bad_members.cpp", check_members=False)
        assert len(result.findings) == 0

    def test_bad_members_with_flag(self):
        result = _scan_fixture("bad_members.cpp", check_members=True)
        # 7 struct members + 6 class members = 13
        assert (
            len(result.findings) == 13
        ), f"Expected 13 member findings, got {len(result.findings)}: " + "\n".join(
            str(f) for f in result.findings
        )

    def test_edge_cases_expected_findings(self):
        result = _scan_fixture("edge_cases.cpp")
        found = {f.var_name for f in result.findings}
        # Should be flagged
        expected_flagged = {
            "shared_arr",
            "dev_var",  # CUDA
            "v",
            "s",
            "m",  # std types
            "obj",
            "perception",  # custom types
            "func_ptr",  # function pointer
            "sensor_reading",  # multi-line
            "my_ptr",  # multi-line scoped
        }
        missing = expected_flagged - found
        assert not missing, f"Expected to flag but didn't: {missing}"

    def test_edge_cases_no_false_positives(self):
        result = _scan_fixture("edge_cases.cpp")
        found = {f.var_name for f in result.findings}
        # Should NOT be flagged
        should_not_flag = {
            "ok1",
            "ok2",
            "ok3",
            "ok4",
            "ok5",  # initialized
            "ext_var",
            "ext_str",  # extern
            "ForwardClass",
            "ForwardStruct",  # forward decls
            "MyInt",
            "MyFloat",  # typedefs
            "item",
            "i",  # for-loop vars
            "a",
            "b",  # initialized locals in exprs()
            "height",
            "channels",
            "rect_out_height",
            "kNumChannelsRgb",  # multiplication
            "projection_matrix_inv",  # multi-line expression array access
        }
        false_positives = found & should_not_flag
        assert not false_positives, f"False positives: {false_positives}"

    def test_line_numbers_are_positive(self):
        result = _scan_fixture("bad_locals.cpp")
        for f in result.findings:
            assert f.line > 0, f"Finding {f.var_name} has non-positive line number {f.line}"

    def test_file_path_preserved(self):
        result = _scan_fixture("bad_locals.cpp")
        for f in result.findings:
            assert "bad_locals.cpp" in f.file
