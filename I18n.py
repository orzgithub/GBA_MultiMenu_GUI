from abc import ABC

# In order to add a new language please just add it to lang_dict and then create a new class for it.
# Then the language will appear in the language setting on the menu.
# If the translation is not 100% finished you can inherit your class from other classes.

lang_dict = {"en_US": "English(US)", "zh_CN": "简体中文"}


class lang_base(ABC):
    window_title: str
    window_title_add_rom: str
    menu_add_game: str
    menu_lang_set: str
    menu_exit: str
    text_lk_bg: str
    text_gba_path: str
    text_gba_name: str
    text_save_slot: str
    text_filetype_png: str
    text_filetype_gba: str
    text_cart_type: str
    text_cart_battery_type: str
    text_cart_split: str
    text_cart_min_size: str
    text_cart_type_list: list[str] = [
        "MSP55LV100S",
        "6600M0U0BE",
        "MSP55LV100",
        "F0095H0",
    ]
    text_cart_min_size_list: dict[str, int] = {"4 MB": 4194304, "512 KB": 524288}
    table_rom_headings: dict[str, str] = {"name": "", "path": "", "save_slot": ""}
    frame_rom_mgr: str
    frame_rom_gen: str
    button_done: str
    button_lk_build: str
    button_lk_set_bg: str
    button_add_rom: str
    button_delete: str
    info_change_lang: str
    error_image_size_not_allowed: str


class zh_CN(lang_base):
    window_title: str = "LK合卡菜单制作GUI"
    window_title_add_rom: str = "添加ROM"
    menu_add_game: str = "添加"
    menu_lang_set: str = "语言"
    menu_exit: str = "退出"
    text_lk_bg: str = "菜单背景"
    text_gba_path: str = "ROM路径"
    text_gba_name: str = "游戏名称"
    text_save_slot: str = "存档槽位"
    text_filetype_png: str = "PNG文件"
    text_filetype_gba: str = "GBA文件"
    text_cart_type: str = "卡带类型"
    text_cart_battery_type: str = "是否有电池"
    text_cart_split: str = "分割ROM"
    text_cart_min_size: str = "卡带最小ROM大小"
    table_rom_headings: dict[str, str] = {
        "name": "名称",
        "path": "路径",
        "save_slot": "存档槽位",
    }
    frame_rom_mgr: str = "GBA ROM管理"
    frame_rom_gen: str = "菜单参数"
    button_done: str = "完成"
    button_lk_build: str = "生成"
    button_lk_set_bg: str = "选择背景"
    button_add_rom: str = "选择ROM"
    button_delete: str = "删除"
    info_change_lang: str = "语言已改变，重启应用生效。"
    error_image_size_not_allowed: str = "图片尺寸不符，无法作为菜单背景。 \n" "请选择一个240*160的png图片。"


class en_US(lang_base):
    window_title: str = "LK multirom menu builder GUI"
    window_title_add_rom: str = "Add a ROM"
    menu_add_game: str = "Add"
    menu_lang_set: str = "Language"
    menu_exit: str = "Exit"
    text_lk_bg: str = "Menu Background"
    text_gba_path: str = "ROM Path"
    text_gba_name: str = "Game Name"
    text_save_slot: str = "Save Slot"
    text_filetype_png: str = "PNG files"
    text_filetype_gba: str = "GBA files"
    text_cart_type: str = "Cartridge Type"
    text_cart_battery_type: str = "Have Battery"
    text_cart_split: str = "Split ROM"
    text_cart_min_size: str = "Minimial ROM size"
    table_rom_headings: dict[str, str] = {
        "name": "Name",
        "path": "Path",
        "save_slot": "Save slot",
    }
    frame_rom_mgr: str = "GBA ROM Manager"
    frame_rom_gen: str = "Menu Settings"
    button_done: str = "Done"
    button_lk_build: str = "Build"
    button_lk_set_bg: str = "Select the background"
    button_add_rom: str = "Select the ROM"
    button_delete: str = "Delete"
    info_change_lang: str = (
        "Language is changed. Restart the application to take effect."
    )
    error_image_size_not_allowed: str = (
        "Size of the image is wrong. \n" "Please use a 240*160 pixel image."
    )