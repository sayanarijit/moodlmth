from unittest.mock import patch

import pytest

raw_html = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8" />
        <title>test</title>
        <script>{}</script>
    </head>
    <body>
        <!-- A comment -->
        <div id="main">
            <form action="/" method="POST">
                <textarea required></textarea>
                <input name="test" required type="text" />
                <button type="submit">submit</button>
            </form>
        </div>
        <clipboard-copy value="x">Copy Me</clipboard-copy>
        <countdown value="10" />
        <footer> space test </footer>
        <script>var x = {a: 1};</script>
    </body>
    <script>{}</script>
</html>
"""

expected_result = """\
from htmldoom import base as b
from htmldoom import elements as e
from htmldoom import render as _render
from htmldoom import renders

doctype = b.doctype("html")


@renders(e.title()("test"))
def title(data):
    return {}


@renders(e.head()(e.meta(charset="utf-8"), "{title}", e.script()(b"{{}}")))
def head(data):
    return {"title": title(data)}


@renders(
    e.body()(
        e.body()(
            b.comment(" A comment "),
            e.div(id_="main")(
                e.form(action="/", method="POST")(
                    e.textarea("required"),
                    e.input_("required", name="test", type_="text"),
                    e.button(type_="submit")("submit"),
                )
            ),
            b.composite_tag("clipboard-copy")(value="x")("Copy Me"),
            b.leaf_tag("countdown")(value="10"),
            e.footer()(" space test "),
            e.script()(b"var x = {{a: 1}};"),
        )
    )
)
def body(data):
    return {}


@renders(e.html()("{head}", "{body}", e.script()(b"{{}}")))
def html(data):
    return {"head": head(data=data), "body": body(data=data)}


@renders("{doctype}{html}")
def document(data):
    return {"doctype": doctype, "html": html(data=data)}


def render(data):
    return _render(document(data=data))


if __name__ == "__main__":
    print(render({}))
"""


@patch("moodlmth.py_converter.warnings.warn")
def test_convert(mocked_warn):
    from moodlmth.py_converter import Converter

    result = Converter().convert(raw_html)
    print(result)
    assert result.strip() == expected_result.strip()


def test_tagleaf():
    from moodlmth.py_converter import TagLeaf

    TagLeaf("a").render() == "e.a()"
    repr(TagLeaf("a", value=TagLeaf("a"))) == "e.a()(e.a())"


def test_value_err():
    from moodlmth.py_converter import Converter

    with pytest.raises(ValueError):
        Converter().convert("</div>")


@patch("moodlmth.py_converter.warnings.warn")
def test_tag_never_closed(mocked_warn):
    from moodlmth.py_converter import Converter

    Converter().convert("<html><p></html>")
    assert mocked_warn.called
