import json
import os
import warnings
from I18n import lang_dict


class Config(object):
    lang: str = "en_US"

    def __init__(self) -> None:
        valid_config: dict = {"lang": lang_dict.keys()}
        if os.path.isfile("config.json"):
            with open("config.json") as config_file:
                try:
                    config_json = json.load(config_file)
                    if (
                        "lang" in config_json
                        and config_json["lang"] in valid_config["lang"]
                    ):
                        self.lang = config_json["lang"]
                except json.decoder.JSONDecodeError as e:
                    warnings.warn(
                        "config.json is not a valid json", category=ResourceWarning
                    )
        self.save()

    def save(self) -> None:
        with open("config.json", "w") as config_file:
            config_dict: dict = {"lang": self.lang}
            json.dump(config_dict, config_file)

    def set_lang(self, langset: str) -> None:
        self.lang: str = langset
        self.save()
