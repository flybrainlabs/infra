"""Persistent browser data for sequential full-model acceptance runs.

Localhost and HTTPS caches remain separate origins inside the same profile.
Never deletes a profile, OPFS files, results, or browser preferences.
"""
from contextlib import contextmanager
import fcntl
import os
import signal
import threading
from pathlib import Path

DEFAULT_PROFILE = Path(__file__).resolve().parents[2] / '.flypow-tools/mining-3d-profile'

def close_test_browser(driver, timeout=5):
    """Bound teardown of this test's driver tree; never removes profile files.

    SwiftShader can hang Chromium's quit response on GPU-less CI. Try ordinary
    quit first, then terminate only descendants recorded for this ChromeDriver.
    """
    owner=driver.service.process.pid
    parents={}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:parents[int(entry.name)]=int((entry/'stat').read_text().rsplit(')',1)[1].split()[1])
            except (OSError,ValueError):pass
    owned={owner}
    for _ in range(8):owned.update(pid for pid,parent in parents.items() if parent in owned)
    def ordinary_quit():
        try:driver.quit()
        except Exception:pass
    worker=threading.Thread(target=ordinary_quit,daemon=True);worker.start();worker.join(timeout)
    if not worker.is_alive():return
    for sig in (signal.SIGTERM,signal.SIGKILL):
        for pid in owned:
            try:os.kill(pid,sig)
            except ProcessLookupError:pass
        worker.join(2)
        if not worker.is_alive():break

@contextmanager
def retained_profile(path=DEFAULT_PROFILE):
    profile=Path(path).resolve()
    profile.mkdir(parents=True,exist_ok=True)
    with Path(str(profile)+'.acceptance.lock').open('a') as lease:
        try:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('This test browser profile is in use; finish its current test first') from error
        try:
            yield str(profile)
        finally:
            fcntl.flock(lease,fcntl.LOCK_UN)
