import hashlib
from pathlib import Path

from cloudsync.providers.base import CloudProvider, RemoteFile


class FakeProvider(CloudProvider):
    def __init__(self, destination="fake:default"):
        self.destination = destination
        self.files = {}
        self.calls = []
        self.fail_on = None

    def identity(self):
        return self.destination

    def list_files(self, remote_path=""):
        prefix = remote_path.strip("/")
        prefix = f"{prefix}/" if prefix else ""
        return {
            key[len(prefix) :]: RemoteFile(
                key,
                key[len(prefix) :],
                len(data),
                0,
                hashlib.md5(data, usedforsecurity=False).hexdigest(),
            )
            for key, data in self.files.items()
            if key.startswith(prefix)
        }

    def _call(self, name):
        self.calls.append(name)
        if self.fail_on == name:
            raise RuntimeError(f"failed {name}")

    def upload(self, local_path, remote_path):
        self._call("upload")
        self.files[remote_path] = Path(local_path).read_bytes()
        return remote_path

    def update(self, remote_id, local_path):
        self._call("update")
        self.files[remote_id] = Path(local_path).read_bytes()

    def delete(self, remote_id):
        self._call("delete")
        del self.files[remote_id]

    def get_storage_info(self):
        usage = sum(map(len, self.files.values()))
        return {"usage": usage, "limit": 1000000, "available": 1000000 - usage}
