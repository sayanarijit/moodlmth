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
        <footer>test</footer>
    </body>
</html>
"""

expected_result = '''\
from htmldoom import elements as e
from htmldoom.layouts import BaseLayout


class Layout(BaseLayout):
    """Layout class."""

    @property
    def doctype(self) -> e.DocType:
        """Document type."""

        return e.DocType("html")

    @property
    def title(self) -> e.Title:
        """Document title."""

        return e.Title()(e._Text("test"))

    @property
    def head(self) -> e.Head:
        """Document head."""

        return e.Head()(e.Meta(charset=repr(v)), e.Title()(e._Text("test")))

    @property
    def body(self) -> e.Body:
        """Document body."""

        return e.Body()(
            e.Div(**{"id": "main"})(
                e.Form(action=repr(v), method=repr(v))(
                    e.Input("required", **{"name": "test", "type": "text"}),
                    e.Button(**{"type": "submit"})(e._Text("submit")),
                )
            ),
            e.Footer()(e._Text("test")),
        )
'''


def test_convert():
    from moodlmth.converter import Converter

    result = Converter().convert(raw_html)
    assert result == expected_result
