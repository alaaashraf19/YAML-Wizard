from .BaseJUnitXMLParser import BaseJUnitXMLParser


class PytestXMLParser(BaseJUnitXMLParser):

    framework_name = "pytest"

    @property
    def supported_formats(self):
        return ["pytest_xml"]

    @property
    def priority(self):
        return 10

    def can_parse(self, content: str, filename: str = "") -> bool:

        return ("pytest" in filename.lower()
            and "<testcase" in content
            and ("pytest" in content.lower() or "::test_" in content)
            )