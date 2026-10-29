# One-download implementation plan

1. Independent tester defines the distribution journey oracle. Add failing unit/contract tests for complete package and GUI-ready handshake.
2. Add a small Windows setup/launch coordinator and stable shortcut. Preserve explicit source-only entrypoint and existing consent/verification controls.
3. Add ready-after-visible GUI record and thread it through source launch. Keep startup failure, crash and timeout distinct; no duplicate app on unresolved startup.
4. Build complete Windows ZIP and SHA256 manifest from explicit public files. Update version, README/help, installation/removal notes and release notes to match actual behavior.
5. Run full Linux and hosted Windows regressions, complete unified first/repeat/fallback/shortcut/recovery journey, inspect screenshots/logs, fix real failures.
6. Publish exact passing patch assets and verify public checksums and README links. Stop after verified publication and CI terminal status.
