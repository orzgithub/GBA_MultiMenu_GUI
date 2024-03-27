# coding=utf-8

from textual.app import *
from textual.widgets import *
from textual.binding import *
from textual.containers import *
from textual.actions import *
from textual.events import *

from resources_src import Resource, I18n, Config
from utils import MenuBuilder


# Binds are forced to load before init so it can only generate in a standalone way.
def LangBINDINGS(screen: str):
    config = Config.Config()
    lang: I18n.lang_base = eval(f"I18n.{config.lang}")
    binding = []
    match screen:
        case "main":
            binding = [
                Binding(
                    key="a",
                    action="push_screen('addrom')",
                    description=lang.menu_add_game,
                ),
                Binding(
                    key="t", action="push_screen('about')", description=lang.menu_about
                ),
                Binding(key="l", action="toggle_dark()", description=lang.menu_theme),
                Binding(key="g", action="build()", description=lang.button_lk_build),
                Binding(key="q", action="quit()", description=lang.menu_exit),
            ]
        case "addrom":
            binding = [
                Binding(key="y", action="add_rom", description=lang.done),
                Binding(key="b", action="push_screen('main')", description=lang.back),
            ]
        case "about":
            binding = [
                Binding(key="b", action="push_screen('main')", description=lang.back),
            ]
    return binding


class MenuBuilderTUI(App):
    class MainScreen(Screen):
        class Container_Games(Container):
            def __init__(
                self,
                lang: I18n.lang_base,
                name: str | None = None,
                id: str | None = None,
                classes: str | None = None,
                disabled: bool = False,
            ):
                self.lang = lang
                self.table_game_list = DataTable(
                    cursor_type="row",
                    classes="content-center-middle",
                    id="table-game-list",
                )
                self.button_del_game = Button(
                    lang.button_delete,
                    classes="content-center-middle",
                    id="button-del-game",
                )
                super().__init__(name=name, id=id, classes=classes, disabled=disabled)

            def on_button_pressed(self, event: Button.Pressed):
                button_id = event.button.id
                match button_id:
                    case "button-del-game":
                        cur_game, _ = self.table_game_list.coordinate_to_cell_key(
                            self.table_game_list.cursor_coordinate
                        )
                        if self.table_game_list.is_valid_coordinate(cur_game):
                            self.table_game_list.remove_row(cur_game)

            def _on_mount(self, event: Mount):
                self.border_title = self.lang.frame_rom_mgr
                self.table_game_list.add_columns(
                    self.lang.table_rom_headings["name"],
                    self.lang.table_rom_headings["path"],
                    self.lang.table_rom_headings["save_slot"],
                )
                super()._on_mount(event)

            def compose(self):
                yield self.table_game_list
                yield self.button_del_game

        class Container_Menu(Grid):
            def __init__(
                self,
                lang: I18n.lang_base,
                name: str | None = None,
                id: str | None = None,
                classes: str | None = None,
                disabled: bool = False,
            ):
                self.lang = lang
                self.label_cart_type = Label(
                    lang.text_cart_type,
                    classes="content-center-middle center-middle",
                )
                self.select_cart_type = Select(
                    (
                        (key, lang.text_cart_type_list.index(key) + 1)
                        for key in lang.text_cart_type_list
                    ),
                    classes="content-center-middle center-middle",
                )
                self.label_min_size = Label(
                    lang.text_cart_min_size,
                    classes="content-center-middle center-middle",
                )
                self.select_min_size = Select(
                    (
                        (key, lang.text_cart_min_size_list[key])
                        for key in lang.text_cart_min_size_list.keys()
                    ),
                    classes="content-center-middle center-middle",
                )
                self.label_have_battery = Label(
                    lang.text_cart_battery_type,
                    classes="content-center-middle center-middle",
                )
                self.switch_have_battery = Switch(
                    classes="content-center-middle center-middle"
                )
                self.label_split = Label(
                    lang.text_cart_split, classes="content-center-middle center-middle"
                )
                self.switch_split = Switch(
                    classes="content-center-middle center-middle"
                )
                self.label_bg_path = Label(
                    lang.text_lk_bg, classes="content-center-middle center-middle"
                )
                self.input_bg_path = Input(
                    classes="content-center-middle center-middle"
                )
                super().__init__(name=name, id=id, classes=classes, disabled=disabled)

            def _on_mount(self, event: Mount):
                self.border_title = self.lang.frame_rom_gen
                super()._on_mount(event)

            def compose(self):
                yield self.label_cart_type
                yield self.select_cart_type
                yield self.label_min_size
                yield self.select_min_size
                yield self.label_have_battery
                yield self.switch_have_battery
                yield self.label_split
                yield self.switch_split
                yield self.label_bg_path
                yield self.input_bg_path

        BINDINGS = LangBINDINGS("main")

        def __init__(
            self,
            lang: I18n.lang_base,
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,
        ):
            self.lang = lang
            self.footer = Footer()
            self.container_games = self.Container_Games(
                lang,
                classes="center-top content-center-middle border-titled",
                id="container-games",
            )
            self.container_menu = self.Container_Menu(
                lang,
                classes="center-top content-center-middle border-titled",
                id="container-menu",
            )
            super().__init__(name, id, classes)

        def compose(self):
            yield self.container_games
            yield self.container_menu
            yield self.footer

    class AboutScreen(Screen):
        BINDINGS = LangBINDINGS("about")

        def __init__(
            self,
            lang: I18n.lang_base,
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,
        ):
            self.lang = lang
            self.footer = Footer()
            super().__init__(name, id, classes)

        def compose(self):
            yield Container(
                Static(classes="pink"),
                Static(classes="powderblue"),
                Static(classes="white"),
                Static(classes="powderblue"),
                Static(classes="pink"),
                classes="content-center-top",
            )
            yield Container(
                Label(
                    self.lang.text_about_title,
                    classes="bold-text content-center-middle",
                ),
                Label(self.lang.text_about_version, classes="content-center-middle"),
                Label(self.lang.text_about_url, classes="content-center-middle"),
                classes="center-middle",
            )
            yield self.footer

    class AddRomScreen(Screen):
        footer = Footer()

        def __init__(
            self,
            lang: I18n.lang_base,
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,
        ):
            self.lang = lang
            self.label_gba_path = Label(
                lang.text_gba_path, classes="content-center-middle center-middle"
            )
            self.input_gba_path = Input(classes="content-center-middle center-middle")
            self.label_gba_title = Label(
                lang.text_gba_name, classes="content-center-middle center-middle"
            )
            self.input_gba_title = Input(classes="content-center-middle center-middle")
            self.label_save_slot = Label(
                lang.text_save_slot, classes="content-center-middle center-middle"
            )
            self.select_save_slot = Select(
                ((str(((None,) + tuple(range(1, 21)))[i]), i) for i in range(0, 21)),
                classes="content-center-middle center-middle",
            )
            super().__init__(name, id, classes)

        def compose(self):
            yield self.label_gba_path
            yield self.input_gba_path
            yield self.label_gba_title
            yield self.input_gba_title
            yield self.label_save_slot
            yield self.select_save_slot
            yield self.footer

        BINDINGS = LangBINDINGS("addrom")

    def __init__(self, lang: I18n.lang_base):
        self.lang = lang
        self.main_screen = self.MainScreen(lang, id="main-screen")
        self.add_rom_screen = self.AddRomScreen(lang, id="game-add-screen")
        self.SCREENS = {
            "main": self.main_screen,
            "addrom": self.add_rom_screen,
            "about": self.AboutScreen(lang, id="about-screen"),
        }
        super().__init__()

    def _on_mount(self, event: Mount):
        self.push_screen("main")

    def action_add_rom(self):
        if (
            self.add_rom_screen.input_gba_path.value != ""
            and self.add_rom_screen.input_gba_title.value != ""
            and self.add_rom_screen.select_save_slot.value != Select.BLANK
        ):
            self.main_screen.container_games.table_game_list.add_row(
                self.add_rom_screen.input_gba_path.value,
                self.add_rom_screen.input_gba_title.value,
                str(
                    ((None,) + tuple(range(1, 21)))[
                        self.add_rom_screen.select_save_slot.value
                    ]
                ),
            )
            self.add_rom_screen.input_gba_path.value = ""
            self.add_rom_screen.input_gba_title.value = ""
            self.add_rom_screen.select_save_slot.value = Select.BLANK
            self.push_screen("main")

    def action_build(self):
        game_list = list()
        for row in self.main_screen.container_games.table_game_list.rows.keys():
            row_info = self.main_screen.container_games.table_game_list.get_row(row)
            game_list_elem = dict()
            game_list_elem["name"] = row_info[0]
            game_list_elem["path"] = row_info[1]
            game_list_elem["save_slot"] = (
                None if row_info[2] == "None" else int(row_info[2])
            )
            game_list.append(game_list_elem)
        options = {
            "type": self.main_screen.container_menu.select_cart_type.value
            if self.main_screen.container_menu.select_cart_type.value != Select.BLANK
            else 2,
            "battery_present": self.main_screen.container_menu.switch_have_battery.value,
            "min_rom_size": self.main_screen.container_menu.select_min_size.value
            if self.main_screen.container_menu.select_min_size.value != Select.BLANK
            else 4194304,
        }
        argoptions = {}
        argoptions["split"] = self.main_screen.container_menu.switch_split.value
        if self.main_screen.container_menu.input_bg_path.value != "":
            argoptions["bg"] = self.main_screen.container_menu.input_bg_path.value
        MenuBuilder.build_start(options, argoptions, game_list)

    CSS_PATH = "MenuBuilder.css"
