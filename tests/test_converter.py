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
from htmldoom import render
from htmldoom import base as b
from htmldoom import elements as e


doctype = b.doctype("html")

title = e.title()("test")

head = e.head()(e.meta(charset="utf-8"), title)

body = e.body()(
    e.div(id_="main")(
        e.form(action="/", method="POST")(
            e.input_("required", name="test", type_="text"),
            e.button(type_="submit")("submit"),
        )
    ),
    e.footer()(" space test "),
)

html = e.html()(head, body)

document = render(doctype, html)


def render():
    return document


if __name__ == "__main__":
    print(render())
"""


def test_convert():
    from moodlmth.converter import Converter

    result = Converter().convert(raw_html)
    print(result)
    assert result == expected_result
