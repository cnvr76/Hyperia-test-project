from Parser import Parser
from pprint import pprint
from typing import Dict
from FileWriter import Writer


if __name__ == "__main__":
    parser: Parser = Parser()

    html: str = parser.send_request(1)
    parser.close_connection()

    info: Dict[str, str] = parser.parse_info(html)

    
