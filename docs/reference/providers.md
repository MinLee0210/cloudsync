# Provider interface

Providers implement `cloudsync.providers.base.CloudProvider`:

```python
class CloudProvider:
    def list_files(self, remote_path: str = "") -> dict: ...
    def upload(self, local_path: str, remote_path: str) -> str: ...
    def update(self, remote_id: str, local_path: str) -> None: ...
    def delete(self, remote_id: str) -> None: ...
    def get_storage_info(self) -> dict: ...
```

`get_storage_info()` returns a mapping with `usage`, `limit`, and `available`. Providers without a quota concept should return `None` for the latter two values.

## Adding a provider

1. Add a class implementing the interface.
2. Keep remote paths relative to the provider's configured root.
3. Register the provider name in `cloudsync.providers.PROVIDERS`.
4. Add tests for upload, update, delete, listing, and quota behavior.

The sync engine only depends on this interface, so provider-specific authentication and SDK details stay isolated.
