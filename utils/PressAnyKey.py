import sys


def press_any_key():
    if sys.platform == "win32":
        import msvcrt

        print("Press any key to continue...", end="", flush=True)
        msvcrt.getch()
    else:
        import termios
        import tty

        print("Press any key to continue...", end="", flush=True)
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    print()
