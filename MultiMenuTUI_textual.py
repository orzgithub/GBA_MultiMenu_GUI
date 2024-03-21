from textual_ui import MenuBuilderTUI
from resources_src import Config, I18n

if __name__ == "__main__":
    config = Config.Config()
    lang = eval(f"I18n.{config.lang}")
    ui = MenuBuilder.MenuBuilderTUI(lang)
    ui.run()
