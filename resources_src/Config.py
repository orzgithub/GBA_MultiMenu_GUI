import json
import os
import warnings
from .I18n import lang_dict


class Config(object):
    lang: str = "en_US"
    theme: str = "classic"

    def __init__(self) -> None:
        valid_config: dict = {
            "lang": lang_dict.keys(),
            "theme": ["classic", "auto", "light", "dark"],
        }
        if os.path.isfile("config.json"):
            with open("config.json") as config_file:
                try:
                    config_json = json.load(config_file)
                    if (
                        "lang" in config_json
                        and config_json["lang"] in valid_config["lang"]
                    ):
                        self.lang = config_json["lang"]
                    if (
                        "theme" in config_json
                        and config_json["theme"] in valid_config["theme"]
                    ):
                        self.theme = config_json["theme"]
                except json.decoder.JSONDecodeError as e:
                    warnings.warn(
                        "config.json is not a valid json", category=ResourceWarning
                    )
        self.save()

    def save(self) -> None:
        with open("config.json", "w") as config_file:
            config_dict: dict = {"lang": self.lang, "theme": self.theme}
            json.dump(config_dict, config_file)

    def set_lang(self, langset: str) -> None:
        self.lang: str = langset
        self.save()

    def set_theme(self, themeset: str) -> None:
        self.theme: str = themeset
        self.save()
