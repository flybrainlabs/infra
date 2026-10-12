# Persistent target service deployment

These systemd/nginx examples use external persistent configuration, model caches,
authority keys, private artifacts and SQLite/WAL. Review and set actual paths
before installing them.

Build and operations instructions are maintained in the English
[operations guide](https://github.com/flybrainlabs/docs/blob/main/docs/OPERATIONS.md).
The serial verifier is one operator with three identities; it does not establish
independent validator consensus. Production payments/rewards stay disabled.
