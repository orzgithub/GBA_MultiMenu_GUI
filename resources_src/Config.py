import json
import os
import warnings
from .I18n import lang_dict, lang_base

dummy_lang = lang_base()


class Config(object):
    lang: str = "en_US"
    tk_theme: str = "classic"
    qt_theme: str = "Fusion"

    def __init__(self) -> None:
        valid_config: dict = {
            "lang": lang_dict.keys(),
            "tk_theme": dummy_lang.menu_tk_theme_dict.keys(),
            "qt_theme": dummy_lang.menu_qt_theme_dict.keys(),
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
                        "tk_theme" in config_json
                        and config_json["tk_theme"] in valid_config["tk_theme"]
                    ):
                        self.tk_theme = config_json["tk_theme"]
                    if (
                        "qt_theme" in config_json
                        and config_json["qt_theme"] in valid_config["qt_theme"]
                    ):
                        self.qt_theme = config_json["qt_theme"]
                except json.decoder.JSONDecodeError as e:
                    warnings.warn(
                        "config.json is not a valid json", category=ResourceWarning
                    )
        self.save()

    def save(self) -> None:
        with open("config.json", "w") as config_file:
            config_dict: dict = {
                "lang": self.lang,
                "tk_theme": self.tk_theme,
                "qt_theme": self.qt_theme,
            }
            json.dump(config_dict, config_file)

    def set_lang(self, langset: str) -> None:
        self.lang: str = langset
        self.save()

    def set_tk_theme(self, themeset: str) -> None:
        self.tk_theme: str = themeset
        self.save()

    def set_qt_theme(self, themeset: str) -> None:
        self.qt_theme: str = themeset
        self.save()
