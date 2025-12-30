import sys
import os
import shutil
import platform
import subprocess
from pathlib import Path
from utils.config import LOG_FILENAME
from support_utils import user_manager
from utils.user_manager import get_lemma_dir

def get_config_name() -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return 'configuration.json'
    cfg_file = os.getenv("LEMMA_CONFIGURATION_FILE")
    if not cfg_file:
        cfg_file = 'configuration.json'
    return cfg_file

def get_config_file() -> Path:
    """
    Get path to configuration.json
    
    Returns:
        Path to configuration.json in ~/.lemma/ directory
    """
    return get_lemma_dir() / get_config_name()


def get_log_file() -> Path:
    """
    Get log file path (for main service)

    Returns:
        Path to log file
    """
    current_user = user_manager.get_current_user()
    if not current_user:
        log_dir = get_lemma_dir() / 'logs'
    else:
        log_dir = user_manager.get_user_working_dir(current_user) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / LOG_FILENAME


def get_version() -> str:
    """Read version from VERSION file, works in both dev and packaged environments"""
    # Try multiple locations for VERSION file
    locations = []

    # 1. For PyInstaller packaged app, check _MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        locations.append(Path(sys._MEIPASS) / "VERSION")

    # 2. For development, check relative to this file
    locations.append(Path(__file__).parent.parent.parent / "VERSION")

    for version_file in locations:
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except Exception:
                continue

    raise FileNotFoundError("VERSION file not found")


def _rg_candidate_paths() -> list:
    """
    Build a list of candidate ripgrep (rg) executable paths in priority order.
    """
    candidates = []

    # 1) Embedded binary (PyInstaller bundle or onedir) - prefer packaged rg first
    try:
        system_name = "macos" if sys.platform == "darwin" else ("linux" if sys.platform.startswith("linux") else None)
        machine = platform.machine().lower()
        if machine in ("aarch64", "arm64"):
            arch_name = "arm64"
        elif machine in ("x86_64", "amd64"):
            arch_name = "x86_64"
        else:
            arch_name = None

        if system_name and arch_name:
            base_dirs = []
            if hasattr(sys, "_MEIPASS") and sys._MEIPASS:
                base_dirs.append(sys._MEIPASS)
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else None
            if exe_dir:
                base_dirs.append(exe_dir)

            for base in base_dirs:
                embedded_rg = os.path.join(base, "_internal", "support", "rg", f"{system_name}-{arch_name}", "rg")
                candidates.append(embedded_rg)
    except Exception:
        # Ignore embedded resolution issues
        pass

    # 2) Environment override
    env_rg = os.getenv("LEMMA_RG_PATH")
    if env_rg:
        candidates.append(env_rg)

    # 3) PATH
    which_rg = shutil.which("rg")
    if which_rg:
        candidates.append(which_rg)

    # 4) Common locations
    candidates.extend([
        os.path.expanduser("~/.lemma/bin/rg"),
        "/opt/homebrew/bin/rg",
        "/usr/local/bin/rg",
        "/usr/bin/rg",
    ])

    return candidates


def _parse_rg_version(output: str) -> str:
    """Parse ripgrep version from `rg --version` output."""
    # Typical: "ripgrep 14.1.0 (rev ...)"
    first_line = (output or "").splitlines()[0] if output else ""
    return first_line.strip()


def detect_ripgrep(set_env: bool = True, logger=None) -> tuple[str | None, str | None]:
    """
    Detect ripgrep (rg) once during service/CLI initialization.

    Returns:
        (rg_path, version_string) if found, otherwise (None, None)
    """
    candidates = _rg_candidate_paths()

    for rg_path in candidates:
        try:
            if os.path.isfile(rg_path) and not os.access(rg_path, os.X_OK):
                try:
                    os.chmod(rg_path, 0o755)
                except Exception:
                    # best effort
                    pass

            result = subprocess.run([rg_path, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = _parse_rg_version(result.stdout)
                if set_env:
                    os.environ["LEMMA_RG_PATH"] = rg_path
                if logger:
                    logger.info(f"ripgrep detected: {rg_path} | {version}")
                return rg_path, version
        except FileNotFoundError:
            continue
        except PermissionError:
            continue
        except Exception:
            # ignore and continue to next candidate
            continue

    if logger:
        logger.warning(
            "ripgrep (rg) not found. The Grep tool will be unavailable. "
        )
    return None, None

