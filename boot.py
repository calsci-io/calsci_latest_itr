from core.fscompat import dirname
from core.update_boot import apply_pending_update

apply_pending_update(dirname(__file__) or ".")

from core.bootstrap import boot

boot()
