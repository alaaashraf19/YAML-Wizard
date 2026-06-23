from .BaseNUnitXMLParser import BaseNUnitXMLParser


class NUnitXMLParser(BaseNUnitXMLParser):

    @property
    def supported_formats(self):
        return ["nunit_xml"]

    @property
    def priority(self):
        return 10

    def can_parse(self, content: str, filename: str = "") -> bool:

        #definitive NUnit marker
        if "<test-run" in content:
            return True
        
        has_nunit_tags = "<test-case" in content or "<test-suite" in content
        has_junit_tags = "<testcase" in content  # JUnit is camelCase
        
        # If it has NUnit tags but NOT JUnit tags, it's probably NUnit
        if has_nunit_tags and not has_junit_tags:
            return True
        
        # .NET/Visual Studio hints
        if (".trx" in filename.lower() or ".dll" in content.lower()):
            return has_nunit_tags
        
        return False