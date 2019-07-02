raw_html = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8" />
        <title>test</title>
    </head>
    <body>
        <div id="main">
            <form action="/" method="POST">
                <input name="test" required type="text" />
                <button type="submit">submit</button>
            </form>
        </div>
        <footer> space test </footer>
    </body>
</html>
"""

expected_result = """\
from htmldoom import base as b
from htmldoom import elements as e
from htmldoom import render as _render
from htmldoom import renders

doctype = _render(b.doctype("html"))

contents = _render(
    e.div(id_="main")(
        e.form(action="/", method="POST")(
            e.input_("required", name="test", type_="text"),
            e.button(type_="submit")("submit"),
        )
    ),
    e.footer()(" space test "),
)


@renders(e.title()("test"))
def render_title(data):
    return {}


@renders(e.head()(e.meta(charset="utf-8"), "{title}"))
def render_head(data, title_renderer=render_title):
    return {"title": title_renderer(data=data)}


@renders(e.body()("{contents}"))
def render_body(data) -> None:
    return {"contents": contents}


@renders(e.html()("{head}", "{body}"))
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


def test_convert():
    from moodlmth.converter import Converter

    result = Converter().convert(raw_html)
    print(result)
    assert result == expected_result
