import json
import re

class JSONHandler:
    def __init__(self, file_path):
        self.file_path = file_path

    def _remove_comments(self, json_str):
        # Remove single-line comments
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        # Remove multi-line comments
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        return json_str

    def read_json(self):
        with open(self.file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # Remove comments before parsing
            clean_content = self._remove_comments(content)
            return json.loads(clean_content)

    def write_json(self, data):
        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)