# Split compact source

This retained table/document exceeds the per-file limit or is a compressed CSV. The ordered UTF-8 parts concatenate to the complete payload without changing values. Use `python3 scripts/materialize_v3_4_sources.py` from the repository root to restore native paths under ignored `generated/v3.4/`. Gzip tables are losslessly decompressed for export and recompressed on materialization; their gzip container bytes can differ. The inventory retains both original-source and uncompressed-payload hashes.

- [part-001.txt](part-001.txt)
- [part-002.txt](part-002.txt)
