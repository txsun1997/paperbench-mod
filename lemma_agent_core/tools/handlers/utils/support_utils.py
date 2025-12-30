from multiprocessing import Value
import os
import sys
import functools
from contextlib import redirect_stdout, redirect_stderr, chdir
import threading
from pathlib import Path

from support.py.credential import access_token
from support.py.configuration import load_configration as load_configration_support
from support.py.credential import (
    _load_dynamic_credential as _load_dynamic_credential_support,
    _save_dynamic_credential as _save_dynamic_credential_support,
    _remove_dynamic_credential as _remove_dynamic_credential_support,
    login_by_email as login_by_email_support,
    _load_user_email_credential_from_env,
    _load_user_token_credential_from_env,
    login_by_token as login_by_token_support,
)
from support.py.configuration import Configuration
from support.py.proto.credential_models import EmailCredential, DynamicCredential, TokenCredential

from utils.user_manager import get_user_working_dir, set_current_user, clear_current_user, get_current_user

from utils.logging_config import get_logger
from utils.user_manager import extract_user_from_lemma_credential
from io import StringIO

logger = get_logger(__name__)

chdir_lock = threading.Lock()

def get_support_py_dir() -> Path:
    """
    Get support/py directory path
    
    When running from PyInstaller bundle, support/py is extracted to _MEIPASS.
    When running from source, it's in the parent directory.

    Returns:
        Path to support/py directory
    """
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running from source
        base_path = Path(__file__).parent.parent.parent
    
    return base_path / 'support' / 'py'

def silent_io(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        text_io = StringIO()
        with open(os.devnull, 'r') as fnull_r:
            old_stdin = sys.stdin
            sys.stdin = fnull_r  # 屏蔽 input()
            try:
                with redirect_stdout(text_io), redirect_stderr(text_io):
                    return func(*args, **kwargs)
            finally:
                logger.info(f"{func.__name__} output: {text_io.getvalue()}")
                sys.stdin = old_stdin  # 恢复 stdin
    return wrapper


class chdir_thread_safe(chdir):
    def __init__(self, path):
        super().__init__(path)

    def __enter__(self):
        chdir_lock.acquire()
        super().__enter__()
        return self

    def __exit__(self, *excinfo):
        super().__exit__(*excinfo)
        chdir_lock.release()


def change_working_directory(path: Path):
    with chdir_lock:
        os.chdir(path)

def load_configration() -> Configuration:
    with chdir_thread_safe(get_support_py_dir()):
        logger.info(f"Loading configuration from {get_support_py_dir()}")
        return load_configration_support()

def access_token_with_login() -> str:
    return access_token()

@silent_io
def load_dynamic_credential() -> DynamicCredential | None:
    user_email = get_current_user()
    if not user_email:
        return None
    with chdir_thread_safe(get_user_working_dir(user_email)):
        return _load_dynamic_credential_support()

@silent_io
def load_user_email_credential_from_env() -> EmailCredential | None:
    return _load_user_email_credential_from_env()

@silent_io
def load_user_token_credential_from_env() -> TokenCredential | None:
    return _load_user_token_credential_from_env()

def post_login_action(cred: DynamicCredential, email: str):
    with chdir_thread_safe(get_user_working_dir(email)):
        logger.info(f"Saving dynamic credential to {get_user_working_dir(email)}")
        _save_dynamic_credential_support(cred)
    set_current_user(email)
    os.chdir(get_user_working_dir(email))

@silent_io
def login_by_token() -> dict:
    try:
        token_cred = load_user_token_credential_from_env()
        if not token_cred:
            return {
                "success": False,
                "message": "No token credential found"
            }
        cred = login_by_token_support(
            token_cred,
            f"https://{load_configration().auth_host}"
        )
    except RuntimeError as e:
        raise e
    except Exception as e:
        import traceback
        logger.error(f"{traceback.format_exc()}")
        return {
            "success": False,
            "message": f"{e}"
        }
    email = extract_user_from_lemma_credential(cred.accessToken)
    if not email:
        return {
            "success": False,
            "message": "Failed to extract user email from access token",
        }
    post_login_action(cred, email)
    return {
        "success": True,
        "message": "Login successful using token",
    }

@silent_io
def login_by_email(email: str, password: str) -> dict:
    try:
        cred = login_by_email_support(
            EmailCredential(email=email, password=password),
            f"https://{load_configration().auth_host}"
        )
    except RuntimeError as e:
        raise e
    except Exception as e:
        import traceback
        logger.error(f"{traceback.format_exc()}")
        return {
            "success": False,
            "message": f"{e}"
        }
    post_login_action(cred, email)
    return {
        "success": True,
        "message": "Login successful",
    }

@silent_io
def logout():
    user_email = get_current_user()
    if not user_email:
        return
    with chdir_thread_safe(get_user_working_dir(user_email)):
        _remove_dynamic_credential_support()
    clear_current_user()
