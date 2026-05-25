# Changelog

Historial de cambios en Gmail Bulk Trash.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [1.0.0] - 2026-05-25 (Initial Release)

### Added
- Core CLI with argparse supporting 9+ arguments
- Blocklist/whitelist management (`--add-sender`, `--remove-sender`, `--add-whitelist`, `--remove-whitelist`, `--list-senders`)
- Dynamic query building combining base query + blocklist - whitelist
- `--dry-run` mode to preview without deleting
- Query filters: `--query`, `--before`, `--after` (with YYYY-MM-DD format)
- Progress bar with ETA and elapsed time
- Persistent `senders.json` storage
- OAuth2 authentication with automatic token refresh
- Batch processing (1000 emails per API call for performance)
- Auto-installation of dependencies
- `.gitignore` protecting credentials
- Basic test suite (`test_senders.py`)
- Documentation (README.md, master document, ADRs)

### Configuration
- Default query: `{from:noreply category:promotions category:social}`
- Batch size: 1000 (Gmail API maximum)
- Supported scopes: `gmail.modify`

### Security
- Credentials stored locally (`credentials.json`, `token.json`)
- Emails moved to **Trash** (recoverable for 30 days), not permanently deleted
- No email bodies read — only metadata and IDs

### Files
```
gmail_bulk_trash.py      — Main script
senders.json            — Persistent blocklist/whitelist
credentials.json        — OAuth2 credentials (created by user)
token.json             — Session token (auto-generated, not versioned)
.gitignore             — Git security configuration
```

### Known Limitations
- Single-instance design (no concurrent execution)
- No transaction rollback if process crashes during write
- No audit log of blocklist changes
- Requires manual credentials.json setup from Google Cloud Console

### Future Roadmap (Ideas)
- [ ] Unsubscribe link detection (F-01)
- [ ] CSV export of deleted emails (F-02)
- [ ] Storage space analysis (F-03)
- [ ] Interactive selector UI (F-04)
- [ ] Label move instead of trash (F-05)
- [ ] Scheduled/cron support (F-06)

---

## Release Notes

**Initial release** of Gmail Bulk Trash. Feature-complete implementation of 6 planned tasks:
1. ✅ Senders persistence layer
2. ✅ CLI command support
3. ✅ Dynamic query building
4. ✅ Dry-run mode
5. ✅ Date and custom query filters
6. ✅ Progress bar with ETA

**Code Quality**:
- Average score: 8.67/10 (SUPERREVISION PASADA 3)
- Type hints: 100%
- Test coverage: Core logic covered
- Security: Credentials protected, no secrets in git

**Documentation**:
- README with setup and usage
- Master document with architecture and decisions
- 3 ADRs documenting key architectural choices
- Inline docstrings and comments
