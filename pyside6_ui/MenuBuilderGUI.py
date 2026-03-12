# coding=utf-8
import datetime
import json
import os.path
import subprocess
import typing
import base64
import platform
from PIL import Image
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QMenuBar,
    QMenu,
    QDialog,
    QGridLayout,
    QGroupBox,
    QStyleFactory,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QMimeData
from PySide6.QtGui import QPixmap, QIcon, QAction, QFont, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QAbstractItemView

from utils import MenuBuilder
from resources_src import Resource, I18n, Config
from rom_builder.cartridge_config import cartridge_types

# These code are still really poor quality, a little better than the tkinter version.
# Seems it won't be rebuilt.


class BuildThread(QThread):

    build_finished = Signal(list, list)

    def __init__(self, options, argoptions, game_list):
        super().__init__()
        self.options = options
        self.argoptions = argoptions
        self.game_list = game_list

    def run(self):
        msg, err = [], []
        for result in MenuBuilder.build_start(
            self.options, self.argoptions, self.game_list
        ):
            if result.success:
                msg.append(result)
            else:
                err.append(result)
        self.build_finished.emit(msg, err)


class GbaStruct(typing.TypedDict):
    path: str
    name: str
    save_slot: int | None


class EditRomDialog(QDialog):
    def __init__(
        self,
        parent=None,
        title="",
        rom_config: GbaStruct | None = None,
        is_new_rom=False,
    ):
        super().__init__(parent)

        if parent and hasattr(parent, "config"):
            self.config = parent.config
            self.app_lang = parent.app_lang
        else:
            global config
            self.config = config
            self.app_lang = eval(f"I18n.{config.lang}")

        self.is_new_rom = is_new_rom
        self.rom_config = rom_config

        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 200)

        layout = QVBoxLayout(self)

        # GBA Path
        path_layout = QHBoxLayout()
        self.label_gba_path = QLabel(self.app_lang.text_gba_path)
        self.entry_gba_path = QLineEdit()
        self.button_gba_path = QPushButton(self.app_lang.button_add_rom)
        self.button_gba_path.clicked.connect(self.select_rom_file)

        path_layout.addWidget(self.label_gba_path)
        path_layout.addWidget(self.entry_gba_path)
        path_layout.addWidget(self.button_gba_path)
        layout.addLayout(path_layout)

        # GBA Name
        name_layout = QHBoxLayout()
        self.label_gba_name = QLabel(self.app_lang.text_gba_name)
        self.entry_gba_name = QLineEdit()

        name_layout.addWidget(self.label_gba_name)
        name_layout.addWidget(self.entry_gba_name)
        layout.addLayout(name_layout)

        # Save Slot
        slot_layout = QHBoxLayout()
        self.label_save_slot = QLabel(self.app_lang.text_save_slot)
        self.combo_save_slot = QComboBox()
        self.combo_save_slot.setEditable(False)
        self.combo_save_slot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.entry_gba_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.entry_gba_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        slot_layout.addWidget(self.label_save_slot)
        slot_layout.addWidget(self.combo_save_slot)
        layout.addLayout(slot_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.button_done = QPushButton(self.app_lang.button_done)
        self.button_cancel = QPushButton(
            self.app_lang.button_cancel
            if hasattr(self.app_lang, "button_cancel")
            else "Cancel"
        )

        self.button_done.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)

        button_layout.addWidget(self.button_done)
        button_layout.addWidget(self.button_cancel)
        layout.addLayout(button_layout)

        if rom_config:
            self.entry_gba_name.setText(rom_config["name"])
            self.entry_gba_path.setText(rom_config["path"])
        self.update_save_slot_options()

    def update_save_slot_options(self):
        global max_slot
        self.combo_save_slot.clear()
        self.combo_save_slot.addItem("None")
        for i in range(1, max_slot + 1):
            self.combo_save_slot.addItem(str(i))

        if self.is_new_rom:
            self.combo_save_slot.setCurrentText(str(max_slot))
        elif self.rom_config and self.rom_config["save_slot"]:
            slot_text = (
                str(self.rom_config["save_slot"])
                if self.rom_config["save_slot"] is not None
                else "None"
            )
            index = self.combo_save_slot.findText(slot_text)
            if index >= 0:
                self.combo_save_slot.setCurrentIndex(index)

    def select_rom_file(self):
        file_filter = (
            f"{self.app_lang.text_filetype_gba} (*.gba);;"
            f"{self.app_lang.text_filetype_gbc} (*.gbc);;"
            f"{self.app_lang.text_filetype_gb} (*.gb);;"
            f"{self.app_lang.text_filetype_nes} (*.nes)"
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self, self.app_lang.button_add_rom, "", file_filter
        )

        if file_path:
            self.entry_gba_path.setText(file_path)
            if not self.entry_gba_name.text() and os.path.splitext(file_path)[
                1
            ].lower() in [".gba", ".gbc", ".gb", ".nes"]:
                name = os.path.splitext(os.path.basename(file_path))[0]
                self.entry_gba_name.setText(name)

    def get_rom_info(self):
        save_slot = None
        if self.combo_save_slot.currentText() != "None":
            save_slot = int(self.combo_save_slot.currentText())

        return GbaStruct(
            path=self.entry_gba_path.text(),
            name=self.entry_gba_name.text(),
            save_slot=save_slot,
        )


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent and hasattr(parent, "config"):
            self.config = parent.config
            self.app_lang = parent.app_lang
        else:
            global config
            self.config = config
            self.app_lang = eval(f"I18n.{config.lang}")

        self.setWindowTitle(self.app_lang.menu_about)
        self.setModal(True)
        self.resize(300, 400)

        layout = QVBoxLayout(self)

        # App Icon
        app_icon_data = base64.b64decode(Resource.icon)
        pixmap = QPixmap()
        pixmap.loadFromData(app_icon_data)
        icon_label = QLabel()
        icon_label.setPixmap(
            pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(self.app_lang.text_about_title)
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Version
        version_label = QLabel(self.app_lang.text_about_version)
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # URL
        url_label = QLabel(
            f'<a href="{self.app_lang.text_about_url}">{self.app_lang.text_about_url}</a>'
        )
        url_label.setOpenExternalLinks(True)
        url_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(url_label)

        # Transgender flag
        transflag_data = base64.b64decode(Resource.transflag)
        transflag_pixmap = QPixmap()
        transflag_pixmap.loadFromData(transflag_data)
        transflag_label = QLabel()
        transflag_label.setPixmap(transflag_pixmap)
        transflag_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(transflag_label)

        # Close button
        close_button = QPushButton(
            self.app_lang.button_close
            if hasattr(self.app_lang, "button_close")
            else "Close"
        )
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


class DragDropTreeWidget(QTreeWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        elif event.mimeData().hasText():
            text = event.mimeData().text()
            if text.startswith("file://"):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        file_paths = []

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path and os.path.exists(file_path):
                    file_paths.append(file_path)

        elif event.mimeData().hasText():
            text = event.mimeData().text()
            if text.startswith("file://"):
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("file://"):
                        file_path = line[7:]
                        file_path = file_path.split("?")[0]
                        file_path = file_path.split("#")[0]
                        try:
                            from urllib.parse import unquote

                            file_path = unquote(file_path)
                        except:
                            pass
                        if file_path and os.path.exists(file_path):
                            file_paths.append(file_path)

        for file_path in file_paths:
            if os.path.splitext(file_path)[1].lower() in [
                ".gba",
                ".gbc",
                ".gb",
                ".nes",
            ]:
                parent = self.parent()
                while parent and not hasattr(parent, "handle_dropped_file"):
                    parent = parent.parent()

                if parent and hasattr(parent, "handle_dropped_file"):
                    parent.handle_dropped_file(file_path)
                    break

        event.acceptProposedAction()


class MenuBuilderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        global config
        config = Config.Config()
        self.config = config
        self.app_lang = eval(f"I18n.{config.lang}")

        global max_slot
        max_slot = 1

        self.bg_path = ""
        self.build_thread = None

        self.init_ui()
        self.apply_theme(config.tk_theme)

    def init_ui(self):
        self.setWindowTitle(self.app_lang.window_title)
        self.setMinimumSize(900, 600)

        app_icon_data = base64.b64decode(Resource.icon)
        pixmap = QPixmap()
        pixmap.loadFromData(app_icon_data)
        self.setWindowIcon(QIcon(pixmap))

        self.create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        self.create_game_management_section(main_layout)

        self.create_rom_generation_section(main_layout)

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)

        # Add Game Menu
        add_game_action = QAction(self.app_lang.menu_add_game, self)
        add_game_action.triggered.connect(self.show_window_add_rom)
        menu_bar.addAction(add_game_action)

        # Language Menu
        lang_menu = QMenu(self.app_lang.menu_lang_set, self)
        for lang in I18n.lang_dict.keys():
            lang_action = QAction(I18n.lang_dict[lang], self)
            lang_action.triggered.connect(
                lambda checked=False, l=lang: self.set_language(l)
            )
            lang_menu.addAction(lang_action)
        menu_bar.addMenu(lang_menu)

        # Theme Menu
        theme_menu = QMenu(self.app_lang.menu_theme, self)

        menu_theme_dict = {}

        for (
            theme_type,
            theme_type_name,
        ) in self.app_lang.menu_qt_theme_type_dict.items():
            menu_theme_dict[f"menu_theme_{theme_type}"] = QMenu(theme_type_name, self)
            theme_menu.addMenu(menu_theme_dict[f"menu_theme_{theme_type}"])

        for (
            theme_elem_type,
            theme_elem_type_name,
        ) in self.app_lang.menu_qt_theme_dict.items():
            theme_type = (
                theme_elem_type.split("::")[0] if "::" in theme_elem_type else "system"
            )
            menu_key = f"menu_theme_{theme_type}"

            if menu_key in menu_theme_dict:
                theme_action = QAction(theme_elem_type_name, self)
                theme_action.triggered.connect(
                    lambda checked=False, t=theme_elem_type: self.apply_theme(t)
                )
                menu_theme_dict[menu_key].addAction(theme_action)

        menu_bar.addMenu(theme_menu)

        # About Menu
        about_action = QAction(self.app_lang.menu_about, self)
        about_action.triggered.connect(self.show_window_about)
        menu_bar.addAction(about_action)

        # Exit Menu
        exit_action = QAction(self.app_lang.menu_exit, self)
        exit_action.triggered.connect(self.close)
        menu_bar.addAction(exit_action)

        self.setMenuBar(menu_bar)

    def create_game_management_section(self, parent_layout):
        frame_game_mgr = QGroupBox(self.app_lang.frame_rom_mgr)
        frame_layout = QVBoxLayout(frame_game_mgr)

        self.table_game_list = DragDropTreeWidget()
        self.table_game_list.setHeaderLabels(
            [
                self.app_lang.table_rom_headings[
                    list(self.app_lang.table_rom_headings.keys())[0]
                ],
                self.app_lang.table_rom_headings[
                    list(self.app_lang.table_rom_headings.keys())[1]
                ],
                self.app_lang.table_rom_headings[
                    list(self.app_lang.table_rom_headings.keys())[2]
                ],
            ]
        )
        self.table_game_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_game_list.itemDoubleClicked.connect(self.table_game_list_edit)

        frame_layout.addWidget(self.table_game_list)

        # Delete button
        self.button_game_delete = QPushButton(self.app_lang.button_delete)
        self.button_game_delete.clicked.connect(self.delete_game)
        frame_layout.addWidget(self.button_game_delete)

        parent_layout.addWidget(frame_game_mgr)

    def create_rom_generation_section(self, parent_layout):
        frame_rom_gen = QGroupBox(self.app_lang.frame_rom_gen)
        frame_layout = QVBoxLayout(frame_rom_gen)

        # Generate Settings
        frame_settings = QWidget()
        settings_layout = QGridLayout(frame_settings)

        # Cartridge Type
        row = 0
        settings_layout.addWidget(QLabel(self.app_lang.text_cart_type), row, 0)
        self.combo_cartridge_type = QComboBox()
        self.combo_cartridge_type.addItems([cart["name"] for cart in cartridge_types])
        settings_layout.addWidget(self.combo_cartridge_type, row, 1)

        # Cartridge Min ROM Size
        row += 1
        settings_layout.addWidget(QLabel(self.app_lang.text_cart_min_size), row, 0)
        self.combo_cartridge_min_rom_size = QComboBox()
        self.combo_cartridge_min_rom_size.addItems(
            list(self.app_lang.text_cart_min_size_list.keys())
        )
        settings_layout.addWidget(self.combo_cartridge_min_rom_size, row, 1)

        # Cartridge Battery Type
        row += 1
        settings_layout.addWidget(QLabel(self.app_lang.text_cart_battery_type), row, 0)
        self.check_cartridge_battery_type = QCheckBox()
        self.check_cartridge_battery_type.setChecked(True)
        self.check_cartridge_battery_type.stateChanged.connect(
            self.toggle_use_rts_visibility
        )
        settings_layout.addWidget(
            self.check_cartridge_battery_type, row, 1, Qt.AlignLeft
        )

        # Use RTS
        row += 1
        self.label_use_rts = QLabel(self.app_lang.text_use_rts)
        self.check_use_rts = QCheckBox()
        self.check_use_rts.setChecked(False)
        settings_layout.addWidget(self.label_use_rts, row, 0)
        settings_layout.addWidget(self.check_use_rts, row, 1, Qt.AlignLeft)

        # Batteryless Autosave
        self.label_batteryless_autosave = QLabel(
            self.app_lang.text_batteryless_autosave
        )
        self.check_batteryless_autosave = QCheckBox()
        self.check_batteryless_autosave.setChecked(True)
        settings_layout.addWidget(self.label_batteryless_autosave, row, 0)
        settings_layout.addWidget(self.check_batteryless_autosave, row, 1, Qt.AlignLeft)

        # Cartridge Split
        row += 1
        settings_layout.addWidget(QLabel(self.app_lang.text_cart_split), row, 0)
        self.check_cartridge_split = QCheckBox()
        self.check_cartridge_split.setChecked(False)
        settings_layout.addWidget(self.check_cartridge_split, row, 1, Qt.AlignLeft)

        # SRAM Bank
        row += 1
        settings_layout.addWidget(QLabel(self.app_lang.text_sram_bank), row, 0)
        self.check_sram_bank = QCheckBox()
        self.check_sram_bank.setChecked(False)
        settings_layout.addWidget(self.check_sram_bank, row, 1, Qt.AlignLeft)

        frame_layout.addWidget(frame_settings)

        # Background Image
        frame_layout.addWidget(QLabel(self.app_lang.text_lk_bg))

        self.label_image_lk_bg = QLabel()
        default_bg_data = base64.b64decode(Resource.default_bg)
        pixmap = QPixmap()
        pixmap.loadFromData(default_bg_data)
        self.label_image_lk_bg.setPixmap(
            pixmap.scaled(240, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.label_image_lk_bg.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(self.label_image_lk_bg)

        # Background selection button
        self.button_lk_set_bg = QPushButton(self.app_lang.button_lk_set_bg)
        self.button_lk_set_bg.clicked.connect(self.select_menu_bg)
        frame_layout.addWidget(self.button_lk_set_bg)

        # Build button
        self.button_lk_build = QPushButton(self.app_lang.button_lk_build)
        self.button_lk_build.clicked.connect(self.start_build)
        frame_layout.addWidget(self.button_lk_build)

        # Initialize visibility
        QTimer.singleShot(100, self.toggle_use_rts_visibility)

        parent_layout.addWidget(frame_rom_gen)

    def handle_dropped_file(self, file_path):

        if not os.path.exists(file_path):
            return

        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in [".gba", ".gbc", ".gb", ".nes"]:
            return

        dialog = EditRomDialog(
            self, self.app_lang.window_title_add_rom, is_new_rom=True
        )
        dialog.entry_gba_path.setText(file_path)
        dialog.entry_gba_name.setText(os.path.splitext(os.path.basename(file_path))[0])

        if dialog.exec() == QDialog.Accepted:
            self.add_game(dialog.get_rom_info())

    def show_window_add_rom(self):
        dialog = EditRomDialog(
            self, self.app_lang.window_title_add_rom, is_new_rom=True
        )
        if dialog.exec() == QDialog.Accepted:
            self.add_game(dialog.get_rom_info())

    def table_game_list_edit(self, item, column):
        save_slot_text = item.text(2)
        save_slot = None if save_slot_text == "None" else int(save_slot_text)

        dialog = EditRomDialog(
            self,
            self.app_lang.window_title_edit_rom,
            GbaStruct(name=item.text(0), path=item.text(1), save_slot=save_slot),
            is_new_rom=False,
        )
        if dialog.exec() == QDialog.Accepted:
            self.edit_game(dialog.get_rom_info(), item)

    def delete_game(self):
        global max_slot
        selected_items = self.table_game_list.selectedItems()
        if selected_items:
            for item in selected_items:
                index = self.table_game_list.indexOfTopLevelItem(item)
                self.table_game_list.takeTopLevelItem(index)

            max_save_slot = 0
            for i in range(self.table_game_list.topLevelItemCount()):
                item = self.table_game_list.topLevelItem(i)
                save_slot_text = item.text(2)
                if save_slot_text != "None":
                    max_save_slot = max(max_save_slot, int(save_slot_text))

            max_slot = max_save_slot + 1

    def add_game(self, game_info: GbaStruct):
        global max_slot
        if game_info["save_slot"] == max_slot:
            max_slot += 1

        item = QTreeWidgetItem(
            [
                game_info["name"],
                game_info["path"],
                (
                    str(game_info["save_slot"])
                    if game_info["save_slot"] is not None
                    else "None"
                ),
            ]
        )
        self.table_game_list.addTopLevelItem(item)

    def edit_game(self, game_info: GbaStruct, item: QTreeWidgetItem):
        global max_slot
        item.setText(0, game_info["name"])
        item.setText(1, game_info["path"])
        item.setText(
            2,
            (
                str(game_info["save_slot"])
                if game_info["save_slot"] is not None
                else "None"
            ),
        )

        max_save_slot = 0
        for i in range(self.table_game_list.topLevelItemCount()):
            current_item = self.table_game_list.topLevelItem(i)
            save_slot_text = current_item.text(2)
            if save_slot_text != "None":
                max_save_slot = max(max_save_slot, int(save_slot_text))

        max_slot = max_save_slot + 1

    def toggle_use_rts_visibility(self):
        if self.check_cartridge_battery_type.isChecked():
            self.label_batteryless_autosave.hide()
            self.check_batteryless_autosave.hide()
            self.label_use_rts.show()
            self.check_use_rts.show()
        else:
            self.label_use_rts.hide()
            self.check_use_rts.hide()
            self.label_batteryless_autosave.show()
            self.check_batteryless_autosave.show()

    def select_menu_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.app_lang.button_lk_set_bg,
            "",
            f"{self.app_lang.text_filetype_png} (*.png)",
        )

        if file_path:
            image = Image.open(file_path)
            if image.size == (240, 160):
                self.bg_path = file_path
                pixmap = QPixmap(file_path)
                self.label_image_lk_bg.setPixmap(
                    pixmap.scaled(240, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                QMessageBox.critical(
                    self, "Error", self.app_lang.error_image_size_not_allowed
                )

    def start_build(self):
        if self.table_game_list.topLevelItemCount() == 0:
            QMessageBox.warning(
                self, "Warning", self.app_lang.error_add_rom_before_generate
            )
            return

        game_list = []
        for i in range(self.table_game_list.topLevelItemCount()):
            item = self.table_game_list.topLevelItem(i)
            save_slot_text = item.text(2)
            game_list_elem = GbaStruct(
                name=item.text(0),
                path=item.text(1),
                save_slot=None if save_slot_text == "None" else int(save_slot_text),
            )
            game_list.append(game_list_elem)

        options = {
            "type": self.combo_cartridge_type.currentIndex() + 1,
            "battery_present": self.check_cartridge_battery_type.isChecked(),
            "min_rom_size": self.app_lang.text_cart_min_size_list[
                list(self.app_lang.text_cart_min_size_list.keys())[
                    self.combo_cartridge_min_rom_size.currentIndex()
                ]
            ],
        }

        argoptions = {}
        argoptions["split"] = self.check_cartridge_split.isChecked()
        argoptions["sram_bank_type"] = 1 if self.check_sram_bank.isChecked() else 0
        argoptions["use_rts"] = self.check_use_rts.isChecked()
        argoptions["batteryless_autosave"] = self.check_batteryless_autosave.isChecked()

        if self.bg_path:
            argoptions["bg"] = self.bg_path

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.app_lang.button_lk_build,
            "",
            f"{self.app_lang.text_filetype_gba} (*.gba)",
        )

        if file_path:
            if not file_path.endswith(".gba"):
                file_path += ".gba"
            argoptions["output"] = file_path

            self.button_lk_build.setEnabled(False)

            self.progress_dialog = QMessageBox(self)
            self.progress_dialog.setWindowTitle(self.app_lang.window_title_building)
            self.progress_dialog.setText(self.app_lang.info_building)
            self.progress_dialog.setStandardButtons(QMessageBox.NoButton)
            self.progress_dialog.show()

            self.build_thread = BuildThread(options, argoptions, game_list)
            self.build_thread.build_finished.connect(self.on_build_finished)
            self.build_thread.start()

    def on_build_finished(self, msg, err):
        self.progress_dialog.hide()

        self.button_lk_build.setEnabled(True)
        self.button_lk_build.setText(self.app_lang.button_lk_build)

        if len(err) == 0:
            QMessageBox.information(self, "Info", self.app_lang.info_build_done)
        else:
            error_list = []
            for error in err:
                print(error)
                error_list.append(
                    {"game": error.path, "type": error.type, "msg": error.msg}
                )

            error_log = {
                "options": self.build_thread.options,
                "argoptions": self.build_thread.argoptions,
                "error": error_list,
            }

            log_file_name = (
                f"error-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            )
            with open(log_file_name, "w", encoding="utf-8") as log:
                json.dump(error_log, log, indent=2, ensure_ascii=False)

            reply = QMessageBox.question(
                self,
                "Info",
                self.app_lang.info_build_done_with_error.replace(
                    "%file_name", log_file_name
                ),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                if platform.system() == "Windows":
                    os.startfile(log_file_name)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", log_file_name])
                else:
                    subprocess.call(["xdg-open", log_file_name])

        self.build_thread = None

    def set_language(self, lang: str):
        self.config.set_lang(lang)
        lang_obj = eval(f"I18n.{lang}")
        QMessageBox.information(self, "Info", lang_obj.info_change_lang)

    def show_window_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def apply_theme(self, theme: str):
        self.config.set_qt_theme(theme)

        if "::" not in theme:
            QApplication.setStyle(QStyleFactory.create(theme))


def run():
    app = QApplication([])

    # Set application attributes for high DPI support
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = MenuBuilderGUI()
    window.show()

    app.exec()
