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

        return e.Title()("test")

    @property
    def html(self) -> e.HTML:
        """Document HTML."""
        return e.HTML()(self.head, self.body)

    @property
    def head(self) -> e.Head:
        """Document head."""

        return e.Head()(e.Meta(charset="utf-8"), self.title)

    @property
    def body(self) -> e.Body:
        """Document body."""

        return e.Body()(
            e.Div(**{"id": "main"})(
                e.Form(action="/", method="POST")(
                    e.Input("required", **{"name": "test", "type": "text"}),
                    e.Button(**{"type": "submit"})("submit"),
                )
            ),
            e.Footer()(" space test "),
        )


if __name__ == "__main__":
    print(Layout())
'''


def test_convert():
    from moodlmth.converter import Converter

    result = Converter().convert(raw_html)
    print(result)
    assert result == expected_result
