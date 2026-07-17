from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class RemoteFile:
    """Represents a file on the remote provider."""

    id: str
    path: str
    size: int
    mtime: object
    hash: Optional[str] = None


class CloudProvider(ABC):
    """Common interface all cloud backends must implement."""

    @abstractmethod
    def list_files(self, remote_path: str = "") -> Dict[str, RemoteFile]:
        """Return mapping of relative path -> RemoteFile for everything under remote_path."""

    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> str:
        """Upload a new file. Returns the remote file id."""

    @abstractmethod
    def update(self, remote_id: str, local_path: str) -> None:
        """Overwrite an existing remote file with local content."""

    @abstractmethod
    def delete(self, remote_id: str) -> None:
        """Delete (or trash) a remote file."""

    @abstractmethod
    def get_storage_info(self) -> dict:
        """Return {'usage': int, 'limit': Optional[int], 'available': Optional[int]}."""

    def identity(self) -> str:
        """Stable destination identity used to isolate synchronization state."""
        return self.__class__.__qualname__
