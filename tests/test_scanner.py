import os

from check_init.scanner import scan_file

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def _var_names(result) -> set:
    return {f.var_name for f in result.findings}


class TestGoodFile:
    """All declarations in good.cpp are properly initialized — expect 0 findings."""

    def test_no_findings(self):
        source = _read_fixture("good.cpp")
        result = scan_file(source, "good.cpp")
        assert (
            result.findings == []
        ), f"Expected 0 findings, got {len(result.findings)}: " + ", ".join(
            str(f) for f in result.findings
        )

    def test_no_findings_with_members(self):
        source = _read_fixture("good.cpp")
        result = scan_file(source, "good.cpp", check_members=True)
        assert (
            result.findings == []
        ), f"Expected 0 findings with --members, got {len(result.findings)}: " + ", ".join(
            str(f) for f in result.findings
        )


class TestBadLocals:
    """Each variable in bad_locals.cpp should be flagged."""

    EXPECTED_VARS = {
        "a",
        "b",
        "c",
        "p",
        "byte",
        "d",
        "ch",
        "cp",
        "ul",
        "ll",
        "val",
        "sz",
        "sensor",
        "counter",
        "vi",
        "sf",
        "sc",
        "ui",
        "diff",
    }

    def test_all_flagged(self):
        source = _read_fixture("bad_locals.cpp")
        result = scan_file(source, "bad_locals.cpp")
        found = _var_names(result)
        missing = self.EXPECTED_VARS - found
        assert not missing, f"Not flagged: {missing}"

    def test_no_extra_findings(self):
        source = _read_fixture("bad_locals.cpp")
        result = scan_file(source, "bad_locals.cpp")
        found = _var_names(result)
        extra = found - self.EXPECTED_VARS
        assert not extra, f"Unexpected findings: {extra}"

    def test_kinds(self):
        source = _read_fixture("bad_locals.cpp")
        result = scan_file(source, "bad_locals.cpp")
        kinds = {f.var_name: f.kind for f in result.findings}
        assert kinds.get("p") == "pointer"
        assert kinds.get("cp") == "pointer"
        assert kinds.get("a") == "local"


class TestBadMembers:
    """Members should only be flagged when check_members=True."""

    def test_not_flagged_by_default(self):
        source = _read_fixture("bad_members.cpp")
        result = scan_file(source, "bad_members.cpp", check_members=False)
        assert result.findings == []

    def test_flagged_with_members(self):
        source = _read_fixture("bad_members.cpp")
        result = scan_file(source, "bad_members.cpp", check_members=True)
        found = _var_names(result)
        # Struct members
        assert "x" in found
        assert "ptr" in found
        assert "active" in found
        assert "arr" in found
        assert "value" in found
        assert "id" in found
        assert "name" in found
        # Class members
        assert "count" in found
        assert "data" in found
        assert "ready" in found
        assert "length" in found
        # Class types too
        assert "items" in found
        assert "label" in found

    def test_methods_not_flagged(self):
        source = _read_fixture("bad_members.cpp")
        result = scan_file(source, "bad_members.cpp", check_members=True)
        found = _var_names(result)
        assert "method" not in found


class TestBadArrays:
    """All arrays in bad_arrays.cpp should be flagged."""

    EXPECTED = {"arr", "matrix", "buf", "coords", "values", "pixels"}

    def test_all_flagged(self):
        source = _read_fixture("bad_arrays.cpp")
        result = scan_file(source, "bad_arrays.cpp")
        found = _var_names(result)
        missing = self.EXPECTED - found
        assert not missing, f"Not flagged: {missing}"

    def test_all_array_kind(self):
        source = _read_fixture("bad_arrays.cpp")
        result = scan_file(source, "bad_arrays.cpp")
        for f in result.findings:
            assert f.kind == "array", f"{f.var_name} has kind {f.kind}, expected 'array'"


class TestEdgeCases:
    """Edge cases from edge_cases.cpp."""

    def test_cuda_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "shared_arr" not in found  # __shared__ excluded — NVCC forbids initializers
        assert "dev_var" in found

    def test_std_types_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "v" in found, "std::vector<int> v should be flagged"
        assert "s" in found, "std::string s should be flagged"
        assert "m" in found, "std::map<int,float> m should be flagged"

    def test_custom_types_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "obj" in found, "MyCustomType obj should be flagged"
        assert "perception" in found, "helm::Perception should be flagged"

    def test_function_pointer_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "func_ptr" in found

    def test_multiline_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "sensor_reading" in found
        assert "my_ptr" in found

    def test_for_loops_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "item" not in found
        assert "x" not in found
        assert "i" not in found

    def test_structured_bindings_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        # 'x' and 'y' from auto [x, y] should not be flagged
        found = _var_names(result)
        assert "x" not in found or "y" not in found

    def test_extern_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "ext_var" not in found
        assert "ext_str" not in found

    def test_initialized_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "ok1" not in found
        assert "ok2" not in found
        assert "ok3" not in found
        assert "ok4" not in found
        assert "ok5" not in found

    def test_typedef_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "MyInt" not in found
        assert "MyFloat" not in found

    def test_forward_decls_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        assert "ForwardClass" not in found
        assert "ForwardStruct" not in found

    def test_multiplication_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        # width * height * channels is multiplication, not a pointer declaration
        assert "height" not in found
        assert "channels" not in found
        assert "rect_out_height" not in found
        assert "kNumChannelsRgb" not in found

    def test_multiline_expression_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        # Continuation lines from multi-line expressions should not be re-scanned
        assert "projection_matrix_inv" not in found

    def test_bitwise_expressions_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        # a | b, a ^ b, etc. are expressions, not declarations
        assert "b" not in found

    def test_ternary_not_flagged(self):
        source = _read_fixture("edge_cases.cpp")
        result = scan_file(source, "edge_cases.cpp")
        found = _var_names(result)
        # a ? 1 : 0 is an expression
        # Make sure the ternary doesn't produce false positives
        assert "1" not in found


class TestInlineSnippets:
    """Test individual code snippets for specific behaviors."""

    def test_reference_not_flagged(self):
        # References must be initialized — compiler enforces
        result = scan_file("int& ref = x;", "test.cpp")
        assert result.findings == []

    def test_const_reference_not_flagged(self):
        result = scan_file("const int& ref = x;", "test.cpp")
        assert result.findings == []

    def test_simple_uninit(self):
        result = scan_file("int x;", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].var_name == "x"

    def test_initialized_equals(self):
        result = scan_file("int x = 0;", "test.cpp")
        assert result.findings == []

    def test_initialized_braces(self):
        result = scan_file("int x{};", "test.cpp")
        assert result.findings == []

    def test_initialized_parens(self):
        result = scan_file("int x(0);", "test.cpp")
        assert result.findings == []

    def test_pointer_uninit(self):
        result = scan_file("int* p;", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].kind == "pointer"

    def test_array_uninit(self):
        result = scan_file("int arr[10];", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].kind == "array"

    def test_array_initialized(self):
        result = scan_file("int arr[10]{};", "test.cpp")
        assert result.findings == []

    def test_array_value_initialized(self):
        result = scan_file("int arr[10] = {0};", "test.cpp")
        assert result.findings == []

    def test_unsigned_long_long(self):
        result = scan_file("unsigned long long x;", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].var_name == "x"

    def test_std_vector(self):
        result = scan_file("std::vector<int> v;", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].var_name == "v"

    def test_std_vector_initialized(self):
        result = scan_file("std::vector<int> v{};", "test.cpp")
        assert result.findings == []

    def test_scoped_type(self):
        result = scan_file("helm::Perception p;", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].var_name == "p"

    def test_template_pointer(self):
        result = scan_file("std::shared_ptr<Foo> p;", "test.cpp")
        assert len(result.findings) == 1

    def test_extern_not_flagged(self):
        result = scan_file("extern int x;", "test.cpp")
        assert result.findings == []

    def test_typedef_not_flagged(self):
        result = scan_file("typedef int MyInt;", "test.cpp")
        assert result.findings == []

    def test_using_not_flagged(self):
        result = scan_file("using MyInt = int;", "test.cpp")
        assert result.findings == []

    def test_return_not_flagged(self):
        result = scan_file("return value;", "test.cpp")
        assert result.findings == []

    def test_class_forward_decl_not_flagged(self):
        result = scan_file("class Foo;", "test.cpp")
        assert result.findings == []

    def test_struct_forward_decl_not_flagged(self):
        result = scan_file("struct Bar;", "test.cpp")
        assert result.findings == []

    def test_multiline_declaration(self):
        result = scan_file("const\n    int\n    x;", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].var_name == "x"

    def test_inline_not_flagged(self):
        result = scan_file("inline int helper() { return 0; }", "test.cpp")
        assert result.findings == []

    def test_new_expression_not_flagged(self):
        result = scan_file("auto* p = new int(5);", "test.cpp")
        assert result.findings == []

    def test_delete_not_flagged(self):
        result = scan_file("delete p;", "test.cpp")
        assert result.findings == []

    def test_constexpr_not_flagged(self):
        result = scan_file("constexpr int x = 5;", "test.cpp")
        assert result.findings == []

    def test_enum_definition_not_flagged(self):
        result = scan_file("enum Color { RED, GREEN };", "test.cpp")
        assert result.findings == []

    def test_static_assert_not_flagged(self):
        result = scan_file('static_assert(sizeof(int) == 4, "int must be 4 bytes");', "test.cpp")
        assert result.findings == []

    def test_preprocessor_not_flagged(self):
        result = scan_file("#define FOO int x", "test.cpp")
        assert result.findings == []

    def test_cuda_shared_skipped(self):
        """__shared__ variables are skipped — NVCC forbids initializers on shared memory."""
        result = scan_file("__shared__ int arr[64];", "test.cpp")
        assert len(result.findings) == 0

    def test_cuda_device_uninit(self):
        result = scan_file("__device__ float x;", "test.cpp")
        assert len(result.findings) == 1

    def test_catch_not_flagged(self):
        source = "try {} catch (std::exception e) {}"
        result = scan_file(source, "test.cpp")
        found = _var_names(result)
        assert "e" not in found

    def test_multiplication_not_flagged(self):
        result = scan_file("width * height * channels;", "test.cpp")
        assert result.findings == []

    def test_two_operand_star_is_ambiguous(self):
        # "a * b;" is ambiguous — could be multiplication or pointer declaration.
        # The scanner treats it as a pointer declaration, which is correct
        # since "type* name;" is the pattern we want to catch.
        result = scan_file("a * b;", "test.cpp")
        assert len(result.findings) == 1
        assert result.findings[0].kind == "pointer"

    def test_division_not_flagged(self):
        result = scan_file("total / count;", "test.cpp")
        assert result.findings == []

    def test_modulo_not_flagged(self):
        result = scan_file("value % alignment;", "test.cpp")
        assert result.findings == []

    def test_addition_not_flagged(self):
        result = scan_file("base + offset;", "test.cpp")
        assert result.findings == []

    def test_subtraction_not_flagged(self):
        result = scan_file("end - start;", "test.cpp")
        assert result.findings == []

    def test_bitwise_or_not_flagged(self):
        result = scan_file("flags | mask;", "test.cpp")
        assert result.findings == []

    def test_bitwise_xor_not_flagged(self):
        result = scan_file("a ^ b;", "test.cpp")
        assert result.findings == []

    def test_shift_left_not_flagged(self):
        result = scan_file("value << 2;", "test.cpp")
        assert result.findings == []

    def test_shift_right_not_flagged(self):
        result = scan_file("value >> 1;", "test.cpp")
        assert result.findings == []

    def test_multiline_expression_continuation(self):
        # Continuation lines should not be re-scanned as separate declarations
        source = (
            "const float x1 = x0 * matrix[0][0] +\n"
            "                 y0 * matrix[0][1] +\n"
            "                 z0 * matrix[0][2];\n"
        )
        result = scan_file(source, "test.cpp")
        assert result.findings == []

    def test_multiline_assigned_expression(self):
        # Multi-line expression with = on first line
        source = "size_t rgb_size =\n" "    rect_out_width * rect_out_height * kNumChannelsRgb;\n"
        result = scan_file(source, "test.cpp")
        assert result.findings == []

    def test_ternary_not_flagged(self):
        result = scan_file("int x = a ? 1 : 0;", "test.cpp")
        assert result.findings == []

    def test_typedef_struct_members_not_flagged(self):
        # Members inside typedef struct { ... } Name; should not be flagged
        # without --members, same as named struct/class members.
        source = "typedef struct {\n" "    int x;\n" "    float y;\n" "} Point2D;\n"
        result = scan_file(source, "test.cpp")
        assert (
            result.findings == []
        ), f"Expected 0 findings, got {len(result.findings)}: " + ", ".join(
            str(f) for f in result.findings
        )

    def test_typedef_struct_members_flagged_with_members(self):
        source = "typedef struct {\n" "    int x;\n" "    float y;\n" "} Point2D;\n"
        result = scan_file(source, "test.cpp", check_members=True)
        found = _var_names(result)
        assert "x" in found
        assert "y" in found

    def test_define_does_not_swallow_next_line(self):
        # A single-line #define must NOT cause the following lines to be
        # treated as macro continuation.  Regression: rect_kernel.h false
        # positive where 'int width' inside a function parameter list was
        # flagged because the preceding #define set in_macro_def=True.
        source = "#define CHAN_NUM 4\n" "\n" "void Foo(int a,\n" "         int b);\n"
        result = scan_file(source, "test.cpp")
        assert (
            result.findings == []
        ), f"Expected 0 findings, got {len(result.findings)}: " + ", ".join(
            str(f) for f in result.findings
        )

    def test_define_breaks_class_scope_tracking(self):
        # Regression: helm_swiftnav_duro.hpp — #define in a header caused
        # the class scope to not be tracked, so class members were flagged
        # as top-level locals without --members.
        source = (
            "#pragma once\n"
            "#define MY_CONST 42\n"
            "\n"
            "class Foo {\n"
            "public:\n"
            "    int x;\n"
            "    float y;\n"
            "};\n"
        )
        result = scan_file(source, "test.hpp")
        assert result.findings == [], (
            f"Expected 0 findings (class members without --members), got "
            f"{len(result.findings)}: " + ", ".join(str(f) for f in result.findings)
        )

    def test_ifndef_guard_does_not_swallow(self):
        # #ifndef/#define header guards must not leak macro state.
        source = (
            "#ifndef MY_HEADER_H\n"
            "#define MY_HEADER_H\n"
            "\n"
            "int global_uninit;\n"
            "\n"
            "#endif\n"
        )
        result = scan_file(source, "test.h")
        assert len(result.findings) == 1
        assert result.findings[0].var_name == "global_uninit"

    def test_multiline_function_decl_not_flagged(self):
        # Multi-line function declarations should not flag parameters.
        source = (
            "void CUDARGBA2RGB(unsigned char *input,\n"
            "                  unsigned char *output,\n"
            "                  int height,\n"
            "                  int width,\n"
            "                  cudaStream_t stream);\n"
        )
        result = scan_file(source, "test.h")
        assert result.findings == [], (
            f"Expected 0 findings for function decl params, got "
            f"{len(result.findings)}: " + ", ".join(str(f) for f in result.findings)
        )

    def test_multiline_function_decl_with_attributes(self):
        # Regression: common.h — function declaration with __attribute__
        source = (
            "void SysEvent(const char *file,\n"
            "              const int32_t line,\n"
            "              const char *format, ...)\n"
            "    __attribute__((format(printf, 3, 4)));\n"
        )
        result = scan_file(source, "test.h")
        assert result.findings == [], (
            f"Expected 0 findings for function decl with attribute, got "
            f"{len(result.findings)}: " + ", ".join(str(f) for f in result.findings)
        )


class TestClassScope:
    """A class's scope ends at its closing brace; method bodies inside it are not class scope."""

    def test_local_after_class_flagged(self):
        # Regression: the class scope never closed, so every local after the first multi-line class was dropped
        source = (
            "struct Header\n"
            "{\n"
            "    int Version;\n"
            "};\n"
            "\n"
            "void Load()\n"
            "{\n"
            "    int count;\n"
            "}\n"
        )
        result = scan_file(source, "test.cpp")
        assert [(f.var_name, f.kind) for f in result.findings] == [("count", "local")]

    def test_local_after_class_not_a_member(self):
        source = "class A\n{\n    int a;\n};\nvoid f()\n{\n    int b;\n}\n"
        result = scan_file(source, "test.cpp", check_members=True)
        assert {(f.var_name, f.kind) for f in result.findings} == {("a", "member"), ("b", "local")}

    def test_member_after_nested_class(self):
        source = (
            "class Outer\n"
            "{\n"
            "    struct Inner\n"
            "    {\n"
            "        int inner;\n"
            "    };\n"
            "    int outer;\n"
            "};\n"
            "int global_uninit;\n"
        )
        result = scan_file(source, "test.h", check_members=True)
        assert {(f.var_name, f.kind) for f in result.findings} == {
            ("inner", "member"), ("outer", "member"), ("global_uninit", "local")}

    def test_local_in_inline_method_body(self):
        # Locals inside an inline method body are locals, and members after the body are still members
        source = (
            "class A\n"
            "{\n"
            "    void f()\n"
            "    {\n"
            "        int local;\n"
            "    }\n"
            "    int member;\n"
            "};\n"
        )
        result = scan_file(source, "test.h", check_members=True)
        assert {(f.var_name, f.kind) for f in result.findings} == {("local", "local"), ("member", "member")}
        result = scan_file(source, "test.h")
        assert [f.var_name for f in result.findings] == ["local"]


class TestDeclaratorForms:
    """Declarations the line parser missed: a global-scope type, typename, several declarators, macro class heads."""

    @staticmethod
    def _found(source, members=False):
        return [(f.var_name, f.kind) for f in scan_file(source, "test.cpp", check_members=members).findings]

    def test_global_scope_type(self):
        assert self._found("void f()\n{\n    ::Actor* actor;\n}\n") == [("actor", "pointer")]

    def test_global_scope_assignment_not_flagged(self):
        assert self._found("void f()\n{\n    ::counter = 5;\n}\n") == []

    def test_typename_prefix(self):
        assert self._found("void f()\n{\n    typename Base::Result pos;\n}\n") == [("pos", "local")]

    def test_second_declarator_after_initialised_one(self):
        assert self._found("int32 i = 0, todo;") == [("todo", "local")]

    def test_every_declarator_flagged(self):
        assert self._found("float pos, prevPos;") == [("pos", "local"), ("prevPos", "local")]

    def test_declarator_kinds(self):
        assert self._found("int* p, q, r[4];") == [("p", "pointer"), ("q", "local"), ("r", "array")]

    def test_initialised_declarators_not_flagged(self):
        assert self._found("int a(5), b{}, c = 1;") == []
        assert self._found("Foo f{1, 2}, g;") == [("g", "local")]

    def test_function_declaration_not_flagged(self):
        assert self._found("int compute(int a, int b);") == []

    def test_macro_class_head(self):
        source = (
            "API_CLASS(Sealed) class FLAXENGINE_API Effect : public Actor\n"
            "{\n"
            "    int32 _index;\n"
            "};\n"
            "void f()\n"
            "{\n"
            "    int x;\n"
            "}\n"
        )
        assert set(self._found(source, members=True)) == {("_index", "member"), ("x", "local")}
        assert self._found(source) == [("x", "local")]

    def test_brackets_in_string_literals_ignored(self):
        # Regression: an unbalanced ( inside a string literal left the parenthesis depth open for the rest of the file
        source = (
            "void f()\n"
            "{\n"
            "    sb.Append(\"SRV(t\");\n"
            "    sb.Append('(');\n"
            "    sb.Append(\"{\");\n"
            "    int count;\n"
            "}\n"
            "int after;\n"
        )
        assert self._found(source) == [("count", "local"), ("after", "local")]
