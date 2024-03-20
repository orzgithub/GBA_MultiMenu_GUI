from abc import ABC

# In order to add a new language please just add it to lang_dict and then create a new class for it.
# Then the language will appear in the language setting on the menu.
# If the translation is not 100% finished you can inherit your class from other classes.

lang_dict = {"en_US": "English(US)", "zh_CN": "简体中文"}


class lang_base(ABC):
    select: str
    back: str
    cancel: str
    done: str
    window_title: str
    window_title_add_rom: str
    menu_add_game: str
    menu_lang_set: str
    menu_about: str
    menu_theme: str
    menu_theme_type_dict: dict[str, str] = {
        "system": "",
        "sun_valley": "",
    }
    menu_theme_dict: dict[str, str] = {
        "classic": "",
        "auto": "",
        "light": "",
        "dark": "",
    }
    menu_exit: str
    text_lk_bg: str
    text_gba_path: str
    text_gba_name: str
    text_save_slot: str
    text_filetype_png: str
    text_filetype_gba: str
    text_filetype_gbc: str
    text_filetype_gb: str
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
    text_about_title: str
    text_about_url: str = "https://github.com/orzgithub/GBA_MultiMenu_GUI"
    text_about_version: str = "Beta 0.1"
    table_rom_headings: dict[str, str] = {"name": "", "path": "", "save_slot": ""}
    frame_rom_mgr: str
    frame_rom_gen: str
    button_done: str
    button_lk_build: str
    button_lk_set_bg: str
    button_add_rom: str
    button_delete: str
    info_change_lang: str
    info_build_done: str
    error_image_size_not_allowed: str


class zh_CN(lang_base):
    select: str = "选择"
    back: str = "返回"
    cancel: str = "取消"
    done: str = "完成"
    window_title: str = "LK合卡菜单制作GUI"
    window_title_add_rom: str = "添加ROM"
    menu_add_game: str = "添加"
    menu_lang_set: str = "语言"
    menu_about: str = "关于"
    menu_theme: str = "主题"
    menu_theme_type_dict: dict[str, str] = {
        "system": "系统样式",
        "sun_valley": "Windows11样式",
    }
    menu_theme_dict: dict[str, str] = {
        "classic": "经典",
        "auto": "自动",
        "light": "亮色",
        "dark": "暗色",
    }
    menu_exit: str = "退出"
    text_lk_bg: str = "菜单背景"
    text_gba_path: str = "ROM路径"
    text_gba_name: str = "游戏名称"
    text_save_slot: str = "存档槽位"
    text_filetype_png: str = "PNG文件"
    text_filetype_gba: str = "GBA文件"
    text_filetype_gbc: str = "GBC文件"
    text_filetype_gb: str = "GB文件"
    text_cart_type: str = "卡带类型"
    text_cart_battery_type: str = "是否有电池"
    text_cart_split: str = "分割ROM"
    text_cart_min_size: str = "卡带最小ROM大小"
    text_about_title: str = "LK合卡菜单生成"
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
    info_build_done: str = "生成完成"
    error_image_size_not_allowed: str = "图片尺寸不符，无法作为菜单背景。 \n" "请选择一个240*160的png图片。"


class en_US(lang_base):
    select: str = "Select"
    back: str = "Back"
    cancel: str = "Cancel"
    done: str = "Done"
    window_title: str = "LK multirom menu builder GUI"
    window_title_add_rom: str = "Add a ROM"
    menu_add_game: str = "Add"
    menu_lang_set: str = "Language"
    menu_about: str = "About"
    menu_theme: str = "Theme"
    menu_theme_type_dict: dict[str, str] = {
        "system": "System style",
        "sun_valley": "Windows11 style",
    }
    menu_theme_dict: dict[str, str] = {
        "classic": "Classic",
        "auto": "Auto",
        "light": "Light",
        "dark": "Dark",
    }
    menu_exit: str = "Exit"
    text_lk_bg: str = "Menu Background"
    text_gba_path: str = "ROM Path"
    text_gba_name: str = "Game Name"
    text_save_slot: str = "Save Slot"
    text_filetype_png: str = "PNG files"
    text_filetype_gba: str = "GBA ROM files"
    text_filetype_gbc: str = "GBC ROM files"
    text_filetype_gb: str = "GB ROM files"
    text_cart_type: str = "Cartridge Type"
    text_cart_battery_type: str = "Have Battery"
    text_cart_split: str = "Split ROM"
    text_cart_min_size: str = "Minimial ROM size"
    text_about_title: str = "LK Muiltmenu builder"
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
    info_build_done: str = "Generate finished"
    error_image_size_not_allowed: str = (
        "Size of the image is wrong. \n" "Please use a 240*160 pixel image."
    )
