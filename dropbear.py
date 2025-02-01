__version__ = "0.2.2"

from pathlib import Path
from typing import Union

from zenlib.util import contains


def drop_the_bear(self) -> str:
    """Returns shell lines to kill the dropbear server if the switch_root_target is mounted"""
    return """
    if [ -n "$(awk '$2 == "'"$(cat /run/vars/SWITCH_ROOT_TARGET)"'" {print $2}' /proc/mounts)" ]; then
        einfo "Switch root target mounted, killing dropbear."
        kill -9 $(cat /run/dropbear.pid)
        return
    fi
    eerror "Switch root target not mounted after dropbear init, ending session"
    rd_fail
    """


def _process_dropbear_authorized_keys(self, authorized_key_path: Union[str, Path]):
    """Sets the dropbear_authorized_keys to the path of the authorized_keys file"""
    authorized_key_path = Path(authorized_key_path)
    if not authorized_key_path.exists():
        raise FileNotFoundError(f"[dropbear] Authorized_keys file not found at: {authorized_key_path}")
    self.data["dropbear_authorized_keys"] = authorized_key_path


@contains("dropbear_authorized_keys", raise_exception=True)
def add_dropbear_keys(self):
    """Adds public keys to the dropbear authorized_keys file"""
    self["copies"] = {
        "dropbear_authorized_keys": {
            "source": self["dropbear_authorized_keys"],
            "destination": "/root/.ssh/authorized_keys",
        }
    }


def dropbear_wait(self):
    """ Returns a shell script to sleep while dropbear is running """
    return """
    while [ "$(cat /proc/$(cat /run/dropbear.pid)/comm)" == "dropbear" ]; do
        edebug "Dropbear is still running, sleeping"
        sleep 1
    done
    einfo "Dropbear has stopped, continuing"
    """

def dropbear_finalize(self):
    """ Create a passwd entry for root if it doesn't exist, chmod 0600 the authorized_keys file """
    self._write("etc/passwd", "root:x:0:0:root:/root:/bin/sh\n", append=True)
    authorized_keys_file = self._get_build_path(self["copies"]["dropbear_authorized_keys"]["destination"])
    authorized_keys_file.chmod(0o600)

def dropbear_init(self):
    """Returns a shell script to start init_main using dropbear"""

    custom_init_contents = [
        self["shebang"],
        f'einfo "Starting dropbear module v{__version__}"',
        "print_banner",
        *self.generate_init_main(),
        "drop_the_bear",
    ]

    run_init = [  # Run dropbear as a daemon
        "einfo Starting dropbear",
        f"dropbear -R -E -j -k -s -c /{self['_custom_init_file']} -P /run/dropbear.pid || rd_fail",
        "dropbear_wait",
    ]

    return run_init, custom_init_contents
