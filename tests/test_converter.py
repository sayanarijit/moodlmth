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

doctype = _render(b.doctype("html"))

contents = _render(
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
    e.script()(b"var x = {a: 1};"),
)


@renders(e.title()("test"))
def render_title(data):
    return {}


@renders(e.head()(e.meta(charset="utf-8"), "{title}", e.script()(b"{{}}")))
def render_head(data, title_renderer=render_title):
    return {"title": title_renderer(data=data)}


@renders(e.body()("{contents}"))
def render_body(data) -> None:
    return {"contents": contents}


@renders(e.html()("{head}", "{body}", e.script()(b"{{}}")))
def render_html(
    data,
    title_renderer=render_title,
    head_renderer=render_head,
    body_renderer=render_body,
):
    return {
        "head": head_renderer(data=data, title_renderer=render_title),
        "body": body_renderer(data=data),
    }


@renders("{doctype}{html}")
def render_document(
    data,
    title_renderer=render_title,
    head_renderer=render_head,
    body_renderer=render_body,
    html_renderer=render_html,
):
    return {
        "doctype": doctype,
        "html": html_renderer(
            data=data,
            title_renderer=title_renderer,
            head_renderer=head_renderer,
            body_renderer=body_renderer,
        ),
    }


def render(data):
    return render_document(data=data)


if __name__ == "__main__":
    print(render({}))
"""


@patch("moodlmth.converter.warnings.warn")
def test_convert(mocked_warn):
    from moodlmth.converter import Converter

    result = Converter().convert(raw_html)
    print(result)
    assert result == expected_result


def test_tagleaf():
    from moodlmth.converter import TagLeaf

    TagLeaf("a").render() == "e.a()"
    repr(TagLeaf("a", value=TagLeaf("a"))) == "e.a()(e.a())"


def test_value_err():
    from moodlmth.converter import Converter

    with pytest.raises(ValueError):
        Converter().convert("</div>")


@patch("moodlmth.converter.warnings.warn")
def test_tag_never_closed(mocked_warn):
    from moodlmth.converter import Converter

    Converter().convert("<html><p></html>")
    assert mocked_warn.called
