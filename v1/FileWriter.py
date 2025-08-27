import json
from typing import Dict, List, Any


class Writer:
    @staticmethod    
    def write_to_json(data: List[Dict[str, Any]], filename: str) -> bool:
        try:        
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
                return True
        except FileNotFoundError as fnfe:
            print(f"'{filename=}' not found...")
            return False

    @staticmethod
    def load_from_json(filename: str) -> Dict[str, Any] | None:
        try:
            with open(filename, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError as fnfe:
            print(f"'{filename=}' not found...")
            return None
        except json.JSONDecodeError as jde:
            print(f"'{filename=}' contains invalid JSON or empty...")
            return None
        
    @staticmethod
    def write_to_file(data: str, filename: str) -> bool:
        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(data)
                return True
        except FileNotFoundError as fnfe:
            print(f"'{filename=}' not found...")
            return False
    
    @staticmethod
    def load_from_file(filename: str) -> str | None:
        try:
            with open(filename, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError as fnfe:
            print(f"'{filename=}' not found...")
            return None