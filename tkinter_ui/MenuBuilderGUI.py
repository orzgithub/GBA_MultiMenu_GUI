# coding=utf-8

import datetime
import json
import os.path
import subprocess
import tkinter
import tkinter.messagebox
import tkinter.filedialog
import tkinter.ttk
import tkinter.font
import webbrowser

from PIL import ImageTk, Image
import ctypes
import base64
import platform
from utils import HeaderReader, MenuBuilder
from resources_src import Resource, I18n, Config

import sv_ttk

# These code are really poor quality.
# Maybe it would be rebuilt one day.
# Or maybe never.


class MenuBuilderGUI(tkinter.Tk):
    def __init__(self):
        super().__init__()
        global config
        config = Config.Config()

        app_lang: I18n.lang_base = eval(f"I18n.{config.lang}")

        default_theme = tkinter.ttk.Style(master=self).theme_use()

        def set_theme(theme: str):
            config.set_theme(theme)
            match theme:
                case "auto":
                    dark_mode = False
                    match platform.system():
                        case "darwin":
                            try:
                                from subprocess import check_output

                                dark_mode = check_output(
                                    "defaults read -g AppleInterfaceStyle", shell=True
                                )
                            except:
                                dark_mode = False
                        case "Windows":
                            try:
                                import winreg

                                registry_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                                key = winreg.OpenKey(
                                    winreg.HKEY_CURRENT_USER, registry_path
                                )
                                value, reg_type = winreg.QueryValueEx(
                                    key, "AppsUseLightTheme"
                                )
                                winreg.CloseKey(key)
                                dark_mode = value == 0
                            except:
                                dark_mode = False
                    if dark_mode:
                        sv_ttk.set_theme("dark", self)
                    else:
                        sv_ttk.set_theme("light", self)
                case "light":
                    sv_ttk.set_theme("light", self)
                case "dark":
                    sv_ttk.set_theme("dark", self)
                case "classic":
                    tkinter.ttk.Style(master=self).theme_use(default_theme)

        set_theme(config.theme)

        app_icon_data = base64.b64decode(Resource.icon)
        app_icon = ImageTk.PhotoImage(data=app_icon_data)
        self.iconphoto(False, app_icon)

        if platform.system() == "Windows":  # Using hidpi on Windows
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except:
                ctypes.windll.user32.SetProcessDPIAware()
            scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
            self.tk.call("tk", "scaling", scale_factor / 75)

        self.title(app_lang.window_title)
        self.resizable(False, False)

        gba_struct: dict = {"path": "", "name": "", "save_slot": 0}

        global max_slot
        max_slot = 1

        def show_window_add_rom():
            # Rom Add Window
            window_add_rom = tkinter.Toplevel(self)
            window_add_rom.title(app_lang.window_title_add_rom)
            window_add_rom.resizable(False, False)
            frame_add_rom = tkinter.ttk.Frame(window_add_rom)
            frame_add_rom.pack(padx=10, pady=10)
            label_gba_path = tkinter.ttk.Label(
                frame_add_rom, text=app_lang.text_gba_path
            )
            label_gba_path.grid(row=0, column=0, padx=5, pady=5)
            entry_gba_path = tkinter.ttk.Entry(frame_add_rom)
            entry_gba_path.grid(row=0, column=1, padx=5, pady=5, sticky=tkinter.W)

            def select_menu_bg():
                selected_file_path = tkinter.filedialog.askopenfilename(
                    parent=window_add_rom,
                    filetypes=[
                        (app_lang.text_filetype_gba, ".gba"),
                        (app_lang.text_filetype_gbc, ".gbc"),
                        (app_lang.text_filetype_gb, ".gb"),
                        (app_lang.text_filetype_nes, ".nes"),
                    ],
                )
                if selected_file_path:
                    entry_gba_path.delete(0, tkinter.END)
                    entry_gba_path.insert(0, selected_file_path)
                    if (
                        not entry_gba_name.get()
                        and os.path.splitext(selected_file_path)[1] == ".gba"
                    ):
                        """entry_gba_name.insert(
                            0, HeaderReader.get_name(selected_file_path)
                        )"""
                        entry_gba_name.insert(
                            0, os.path.splitext(os.path.basename(selected_file_path))[0]
                        )

            button_gba_path = tkinter.ttk.Button(
                frame_add_rom, text=app_lang.button_add_rom, command=select_menu_bg
            )
            button_gba_path.grid(row=0, column=2, padx=5, pady=5)

            label_gba_name = tkinter.ttk.Label(
                frame_add_rom, text=app_lang.text_gba_name
            )
            label_gba_name.grid(row=1, column=0, padx=5, pady=5)
            entry_gba_name = tkinter.ttk.Entry(frame_add_rom)
            entry_gba_name.grid(row=1, column=1, padx=5, pady=5, sticky=tkinter.W)

            lable_save_slot = tkinter.ttk.Label(
                frame_add_rom, text=app_lang.text_save_slot
            )
            lable_save_slot.grid(row=2, column=0, padx=5, pady=5)
            entry_save_slot = tkinter.ttk.Spinbox(
                frame_add_rom,
                values=((None,) + tuple(range(1, max_slot + 1))),
                increment=1,
            )
            entry_save_slot.insert(0, "None")
            entry_save_slot.grid(row=2, column=1, padx=5, pady=5, sticky=tkinter.W)

            def finish_add_rom():
                gba_ret = gba_struct.copy()
                gba_ret["path"] = entry_gba_path.get()
                gba_ret["name"] = entry_gba_name.get()
                gba_ret["save_slot"] = (
                    None
                    if entry_save_slot.get() == "None"
                    else int(entry_save_slot.get())
                )
                add_game(gba_ret)
                global max_slot
                if gba_ret["save_slot"] == max_slot:
                    max_slot += 1
                window_add_rom.quit()
                window_add_rom.destroy()

            button_done = tkinter.ttk.Button(
                frame_add_rom, text=app_lang.button_done, command=finish_add_rom
            )
            button_done.grid(row=3, column=1)
            window_add_rom.mainloop()

        # Menu part
        menu = tkinter.Menu(self)
        ## Add Game Menu
        menu.add_command(label=app_lang.menu_add_game, command=show_window_add_rom)
        ## Language Menu
        menu_lang = tkinter.Menu(menu, tearoff=False)
        for lang in I18n.lang_dict.keys():
            # Yes these are really strange but using lambda to pass args are causing problems here.
            # If you have a better idea please submit a pull request for this.
            exec(
                f"""
def set_lang_{lang}():
    config.set_lang('{lang}')
    tkinter.messagebox.showinfo(message=I18n.{lang}.info_change_lang)
menu_lang.add_command(label=I18n.lang_dict['{lang}'], command=set_lang_{lang})
"""
            )
        menu.add_cascade(label=app_lang.menu_lang_set, menu=menu_lang)

        ##About
        def show_window_about():
            window_about = tkinter.Toplevel(self)
            frame_about = tkinter.ttk.Frame(window_about)
            frame_about.pack(padx=10, pady=10)
            lable_icon = tkinter.ttk.Label(frame_about, image=app_icon)
            lable_icon.pack(padx=5, pady=5)
            lable_about_title = tkinter.ttk.Label(
                frame_about,
                text=app_lang.text_about_title,
                font=tkinter.font.Font(weight="bold"),
            )
            lable_about_title.pack(padx=5, pady=5)
            lable_about_ver = tkinter.ttk.Label(
                frame_about, text=app_lang.text_about_version
            )
            lable_about_ver.pack(padx=5, pady=5)
            lable_about_url = tkinter.Label(
                frame_about, text=app_lang.text_about_url, fg="blue"
            )
            global image_transflag
            image_transflag = base64.b64decode(Resource.transflag)
            image_transflag = ImageTk.PhotoImage(data=image_transflag)
            label_transgender_flag = tkinter.ttk.Label(
                frame_about, image=image_transflag
            )
            label_transgender_flag.pack(padx=5, pady=5)
            lable_about_url.bind(
                "<Button-1>",
                lambda event: webbrowser.open(app_lang.text_about_url, new=0),
            )
            lable_about_url.pack(padx=5, pady=5)

        menu.add_command(label=app_lang.menu_about, command=show_window_about)
        ##Theme
        menu_theme = tkinter.Menu(menu, tearoff=False)
        menu_theme_system = tkinter.Menu(menu, tearoff=False)
        menu_theme_system.add_command(
            label=app_lang.menu_theme_dict["classic"],
            command=lambda: set_theme("classic"),
        )
        menu_theme.add_cascade(
            label=app_lang.menu_theme_type_dict["system"], menu=menu_theme_system
        )
        menu_theme_sv = tkinter.Menu(menu, tearoff=False)
        menu_theme_sv.add_command(
            label=app_lang.menu_theme_dict["auto"],
            command=lambda: set_theme("auto"),
        )
        menu_theme_sv.add_command(
            label=app_lang.menu_theme_dict["light"],
            command=lambda: set_theme("light"),
        )
        menu_theme_sv.add_command(
            label=app_lang.menu_theme_dict["dark"],
            command=lambda: set_theme("dark"),
        )
        menu_theme.add_cascade(
            label=app_lang.menu_theme_type_dict["sun_valley"], menu=menu_theme_sv
        )
        menu.add_cascade(label=app_lang.menu_theme, menu=menu_theme)
        ## Exit
        menu.add_command(label=app_lang.menu_exit, command=self.quit)
        self.config(menu=menu)

        frame_style = tkinter.ttk.Style().configure("TFrame")

        # Game Manage Part
        frame_game_mgr = tkinter.ttk.LabelFrame(
            self, style=frame_style, text=app_lang.frame_rom_mgr
        )
        table_game_list = tkinter.ttk.Treeview(
            frame_game_mgr,
            columns=list(app_lang.table_rom_headings.keys()),
            show="headings",
        )
        table_game_list.heading(
            0,
            text=app_lang.table_rom_headings[
                list(app_lang.table_rom_headings.keys())[0]
            ],
        )
        table_game_list.heading(
            1,
            text=app_lang.table_rom_headings[
                list(app_lang.table_rom_headings.keys())[1]
            ],
        )
        table_game_list.heading(
            2,
            text=app_lang.table_rom_headings[
                list(app_lang.table_rom_headings.keys())[2]
            ],
        )
        table_game_list.pack(padx=5, pady=5)

        def delete_game():
            selection = table_game_list.selection()
            if selection:
                for cselection in selection:
                    table_game_list.delete(cselection)

        def add_game(game_info):
            table_game_list.insert(
                "",
                tkinter.END,
                values=[game_info["name"], game_info["path"], game_info["save_slot"]],
            )

        button_game_delete = tkinter.ttk.Button(
            frame_game_mgr, text=app_lang.button_delete, command=delete_game
        )
        button_game_delete.pack(padx=5, pady=5)
        frame_game_mgr.grid(row=0, column=0, padx=10, pady=10)

        # Rom Generate Part
        frame_rom_gen = tkinter.ttk.LabelFrame(
            self, style=frame_style, text=app_lang.frame_rom_gen
        )
        ## Generate Settings Part
        frame_settings = tkinter.ttk.Frame(frame_rom_gen)
        label_cartridge_type = tkinter.ttk.Label(
            frame_settings, text=app_lang.text_cart_type
        )
        label_cartridge_type.grid(row=0, column=0, padx=5, pady=5)
        combo_cartridge_type = tkinter.ttk.Combobox(
            frame_settings, values=app_lang.text_cart_type_list
        )
        combo_cartridge_type.current(0)
        combo_cartridge_type.grid(row=0, column=1, padx=5, pady=5, sticky=tkinter.W)

        label_cartridge_min_rom_size = tkinter.ttk.Label(
            frame_settings, text=app_lang.text_cart_min_size
        )
        label_cartridge_min_rom_size.grid(row=1, column=0, padx=5, pady=5)
        combo_cartridge_min_rom_size = tkinter.ttk.Combobox(
            frame_settings, values=list(app_lang.text_cart_min_size_list.keys())
        )
        combo_cartridge_min_rom_size.current(0)
        combo_cartridge_min_rom_size.grid(
            row=1, column=1, padx=5, pady=5, sticky=tkinter.W
        )

        label_cartridge_battery_type = tkinter.ttk.Label(
            frame_settings, text=app_lang.text_cart_battery_type
        )
        label_cartridge_battery_type.grid(row=2, column=0, padx=5, pady=5)
        check_cartridge_battery_type_stat = tkinter.BooleanVar()
        check_cartridge_battery_type = tkinter.ttk.Checkbutton(
            frame_settings, variable=check_cartridge_battery_type_stat
        )
        check_cartridge_battery_type.grid(
            row=2, column=1, padx=5, pady=5, sticky=tkinter.W
        )

        label_cartridge_split = tkinter.ttk.Label(
            frame_settings, text=app_lang.text_cart_split
        )
        label_cartridge_split.grid(row=3, column=0, padx=5, pady=5)
        check_cartridge_split_stat = tkinter.BooleanVar()
        check_cartridge_split = tkinter.ttk.Checkbutton(
            frame_settings, variable=check_cartridge_split_stat
        )
        check_cartridge_split.grid(row=3, column=1, padx=5, pady=5, sticky=tkinter.W)

        frame_settings.pack(padx=5, pady=5)

        ## label for background image
        label_image_lk_bg_text = tkinter.Label(frame_rom_gen, text=app_lang.text_lk_bg)
        label_image_lk_bg_text.pack(padx=5, pady=5)
        ## background image view
        global image_lk_bg
        global bg_path
        image_lk_bg = ImageTk.PhotoImage(file=r"bg.png")
        label_image_lk_bg = tkinter.ttk.Label(frame_rom_gen, image=image_lk_bg)
        label_image_lk_bg.pack(padx=5, pady=5)
        ## bottom for select the background image
        bg_path = ""

        def select_menu_bg():
            selected_file_path = tkinter.filedialog.askopenfilename(
                parent=self, filetypes=[(app_lang.text_filetype_png, ".png")]
            )
            if selected_file_path:
                image = Image.open(selected_file_path)
                if image.size == (240, 160):
                    global image_lk_bg
                    global bg_path
                    bg_path = selected_file_path
                    image_lk_bg = ImageTk.PhotoImage(file=selected_file_path)
                    label_image_lk_bg["image"] = image_lk_bg
                else:
                    tkinter.messagebox.showerror(
                        message=app_lang.error_image_size_not_allowed
                    )

        button_lk_build = tkinter.ttk.Button(
            frame_rom_gen, text=app_lang.button_lk_set_bg, command=select_menu_bg
        )
        button_lk_build.pack(padx=5, pady=5)

        ## button for build the rom
        def start_build():
            game_list_children = table_game_list.get_children()
            game_list = list()
            for child in game_list_children:
                game_list_elem = gba_struct.copy()
                game_list_elem["name"] = table_game_list.item(child)["values"][0]
                game_list_elem["path"] = table_game_list.item(child)["values"][1]
                save_slot = table_game_list.item(child)["values"][2]
                game_list_elem["save_slot"] = (
                    None if save_slot == "None" else int(save_slot)
                )
                game_list.append(game_list_elem)
            options = {
                "type": combo_cartridge_type.current() + 1,
                "battery_present": check_cartridge_battery_type_stat.get(),
                "min_rom_size": app_lang.text_cart_min_size_list[
                    list(app_lang.text_cart_min_size_list.keys())[
                        combo_cartridge_min_rom_size.current()
                    ]
                ],
            }
            argoptions = {}
            argoptions["split"] = check_cartridge_split_stat.get()
            if bg_path != "":
                argoptions["bg"] = bg_path
            path_save = tkinter.filedialog.asksaveasfilename(
                parent=self, filetypes=[(app_lang.text_filetype_gba, ".gba")]
            )
            if path_save:
                if not path_save.endswith(".gba"):
                    path_save = path_save + ".gba"
                argoptions["output"] = path_save
                msg, err = [], []
                for result in MenuBuilder.build_start(options, argoptions, game_list):
                    if result.success:
                        msg.append(result)
                    else:
                        err.append(result)
                if len(err) == 0:
                    tkinter.messagebox.showinfo(message=app_lang.info_build_done)
                else:
                    error_list = []
                    for error in err:
                        print(error)
                        error_list.append(
                            {"game": error.path, "type": error.type, "msg": error.msg}
                        )
                    error_log = {
                        "options": options,
                        "argoptions": argoptions,
                        "error": error_list,
                    }
                    log_file_name = f"error-{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log"
                    with open(log_file_name, "w") as log:
                        json.dump(error_log, log, indent=2, ensure_ascii=False)
                    if tkinter.messagebox.askyesno(
                        message=app_lang.info_build_done_with_error.replace(
                            "%file_name", log_file_name
                        ),
                    ):
                        if platform.system() == "Windows":
                            os.startfile(log_file_name)
                        elif platform.system() == "Darwin":
                            subprocess.call(["open", log_file_name])
                        else:
                            subprocess.call(["xdg-open", log_file_name])

        button_lk_build = tkinter.ttk.Button(
            frame_rom_gen, text=app_lang.button_lk_build, command=start_build
        )
        button_lk_build.pack(padx=5, pady=5)
        frame_rom_gen.grid(row=0, column=1, padx=10, pady=10)
