#!/usr/bin/env python3
import sys
import os

from patcher.utils.admin import is_admin, run_as_admin
from patcher.utils.console import setup_console
from patcher.cli import run_cli, confirmed


if __name__ == "__main__":
    setup_console()
    if os.name == "nt" and os.environ.get("SKIP_ELEVATION") != "1" and not is_admin():
        if run_as_admin():
            sys.exit(0)
        else:
            print("  [!] Could not elevate privileges. The script may fail to modify files.")
    elif os.name == "posix" and not is_admin():
        # Мод 1.3.9: sudo нужен только для системных путей (/usr/share, /opt,
        # /Applications). Юзерская установка (~/.local/bin/agy, ~/Загрузки/...)
        # патчится без root — не дёргаем пользователя лишним вопросом.
        _needs_root = False
        try:
            from patcher.utils.file import get_posix_invoking_user_home
            uh = get_posix_invoking_user_home() or os.path.expanduser("~")
            user_targets = [
                os.path.join(uh, ".local", "bin", "agy"),
                os.path.join(uh, "bin", "agy"),
            ]
            argv_paths = [a for a in sys.argv[1:] if a not in ("--rollback", "-r")]
            user_targets += argv_paths
            for t in user_targets:
                try:
                    p = os.path.abspath(os.path.expandvars(os.path.expanduser(t)))
                    if os.path.isfile(p) and os.access(p, os.W_OK):
                        break
                    d = p if os.path.isdir(p) else os.path.dirname(p)
                    if d and os.path.isdir(d) and os.access(d, os.W_OK):
                        break
                except Exception:
                    continue
            else:
                _needs_root = True
        except Exception:
            _needs_root = True
        if not _needs_root:
            from patcher.constants import COLOR_GREEN
            from patcher.utils.console import color
            print(color("  [+] User-local install detected — proceeding without sudo.", COLOR_GREEN))
            print()
        else:
            print("  [!] Root access is required to patch files in the root directory.")
            if confirmed("Re-launch with sudo?"):
                try:
                    if getattr(sys, "frozen", False):
                        args = ["sudo", sys.executable] + sys.argv[1:]
                    else:
                        args = ["sudo", sys.executable] + sys.argv
                    os.execvp("sudo", args)
                except Exception as e:
                    print(f"  [!] Failed to re-launch with sudo: {e}")
                    sys.exit(1)
            else:
                from patcher.constants import COLOR_YELLOW
                from patcher.utils.console import color
                print(color("  [!] Proceeding without root. Write errors are possible.", COLOR_YELLOW))
                print()

    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n  [i] Exiting...")
        sys.exit(0)
    except (PermissionError, OSError) as e:
        # Страховка от необработанного traceback как на скриншоте
        # (бэкап language_server.agybak -> Errno 1 Operation not permitted):
        # вместо "Failed to execute script 'main'" показываем понятную подсказку.
        print(f"\n  [!] Filesystem error: {e}")
        import sys as _sys

        if _sys.platform == "darwin":
            print("  [i] macOS blocked writing inside Antigravity.app.")
            print("  [i] Close Antigravity and re-run with sudo:")
            print("        sudo python main.py   (or sudo ./Open_AG_Patcher)")
            print("  [i] If it still says 'Operation not permitted', check flags:")
            print("        ls -lO /Applications/Antigravity.app/Contents/resources/bin/language_server")
        else:
            print("  [i] No write access — re-run as admin/root and close Antigravity first.")
        sys.exit(1)
    except Exception as e:
        print(f"\n  [!] Unexpected error: {e}")
        print("  [i] Please report it: https://github.com/AvenCores/open-antigravity-unlock/issues")
        sys.exit(1)