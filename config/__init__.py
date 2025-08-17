import json
import os
import sys
from pathlib import Path
from typing import Any


class Settings:
    settings, locked = None, False

    def __getattr__(cls, key: str):
        if cls.locked and key in cls.settings:
            return cls.settings[key]
        raise AttributeError(
            f"'{key}' is not present in settings file (config/default.json)"
        )

    def __delattr__(self, key: str) -> None:
        if self.locked:
            raise AttributeError(f"Can not modify settings")
        super().__delattr__(key)

    def __setattr__(self, key: str, value: Any) -> None:
        if self.locked and key != "locked":
            raise AttributeError(f"Can not modify settings")
        super().__setattr__(key, value)

    def __getitem__(self, key: str) -> Any:
        if self.locked and key in self.settings:
            return self.settings[key]
        raise KeyError(f"'{key}' is not present in settings file (config/default.json)")

    def load(self, data: dict) -> None:
        """load from file, handle nested attributes, needs to be objects, not dicts"""
        if not hasattr(self, "settings") or self.settings is None:
            self.settings = {}
        for key, value in data.items():
            if isinstance(value, dict):
                self.settings[key] = Settings()
                self.settings[key].load(value)
            else:
                self.settings[key] = value
        self.locked = True

    def override(self, file: str) -> None:
        """Override settings with a new file, file can be relative or absolute path."""
        self.locked = False
        if not os.path.exists(file):
            raise FileNotFoundError(f"Config file {file} does not exist")
        with open(file, "r") as f:
            self.load(json.load(f))


settings = None
if not settings:
    settings = Settings()
    project_root = str(Path(__file__).resolve().parent.parent)
    try:
        with open(os.path.join(project_root, "config", "default.json"), "r") as file:
            settings.load(json.load(file))
    except FileNotFoundError:
        print("Please create a default.json file in config/default.json")
        sys.exit()
    except json.decoder.JSONDecodeError:
        print("default.json file not in a readable json format")
        sys.exit()