from check_init.preprocessor import join_continuations, preprocess, strip_comments


class TestStripComments:
    def test_line_comment(self):
        assert strip_comments("int x; // comment").strip() == "int x;"

    def test_block_comment(self):
        result = strip_comments("int /* comment */ x;")
        assert "int" in result and "x;" in result
        assert "comment" not in result

    def test_block_comment_multiline(self):
        result = strip_comments("int x; /* start\nmiddle\nend */ int y;")
        lines = result.split("\n")
        assert lines[0].strip() == "int x;"
        assert "int y;" in lines[-1]

    def test_preserves_string_literals(self):
        result = strip_comments('const char* s = "hello // world";')
        assert '"hello // world"' in result

    def test_preserves_string_with_block_comment_syntax(self):
        result = strip_comments('const char* s = "/* not a comment */";')
        assert '"/* not a comment */"' in result

    def test_preserves_char_literal(self):
        result = strip_comments("char c = '/';")
        assert "'/'" in result

    def test_nested_string_escape(self):
        result = strip_comments(r'const char* s = "escaped \"quote\"";')
        assert "escaped" in result

    def test_empty_input(self):
        assert strip_comments("") == ""

    def test_no_comments(self):
        src = "int x = 0;"
        assert strip_comments(src) == src


class TestJoinContinuations:
    def test_simple_continuation(self):
        result = join_continuations("int \\\nx;")
        assert result == "int x;"

    def test_no_continuation(self):
        result = join_continuations("int x;\nint y;")
        assert result == "int x;\nint y;"

    def test_multiple_continuations(self):
        result = join_continuations("a\\\nb\\\nc")
        assert result == "abc"


class TestPreprocess:
    def test_preserves_line_numbers(self):
        source = "int a;\n// comment\nint b;"
        lines = preprocess(source)
        texts = {ln.number: ln.text.strip() for ln in lines if ln.text.strip()}
        assert texts[1] == "int a;"
        assert texts[3] == "int b;"

    def test_comment_removal_with_line_numbers(self):
        source = "int a; // init\nint b; /* block */\nint c;"
        lines = preprocess(source)
        assert any(ln.number == 1 and "int a;" in ln.text for ln in lines)
        assert any(ln.number == 3 and "int c;" in ln.text for ln in lines)

    def test_continuation_joining(self):
        source = "int \\\n  x;"
        lines = preprocess(source)
        joined = [ln for ln in lines if "x" in ln.text]
        assert len(joined) == 1
        assert joined[0].number == 1  # Reports the starting line

    def test_empty_source(self):
        assert preprocess("") == [] or all(ln.text == "" for ln in preprocess(""))
