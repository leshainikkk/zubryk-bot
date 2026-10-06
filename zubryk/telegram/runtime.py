import fcntl
import os

from zubryk.config import ROOT


def acquire_polling_lock():
    runtime=ROOT/".runtime"
    runtime.mkdir(exist_ok=True)
    handle=(runtime/"bot.lock").open("a+")
    try:
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise RuntimeError("Другой экземпляр бота уже работает в этом проекте") from None
    handle.seek(0);handle.truncate();handle.write(str(os.getpid()));handle.flush()
    (runtime/"bot.pid").write_text(str(os.getpid()))
    return handle
