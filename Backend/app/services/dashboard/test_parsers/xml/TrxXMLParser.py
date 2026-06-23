from .BaseTrxXMLParser import BaseTrxXMLParser 

class TrxXMLParser(BaseTrxXMLParser):
    """Parse Visual Studio TRX (xUnit, MSTest) format"""
    
    framework_name = "xunit"
    
    @property
    def supported_formats(self):
        return ["trx_xml"]
    
    @property
    def priority(self):
        return 10  #higher priority: specific to .NET
    
    def can_parse(self, content: str, filename: str = "") -> bool:
        """Detect TRX format by distinctive markers"""
        return (
            "<TestRun" in content
            or ".trx" in filename.lower()
            or "microsoft.com/schemas/VisualStudio" in content
        )