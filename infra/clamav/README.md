ClamAV is accessible only on the Compose network. Its signature database persists
in `clamav_db`. First startup downloads signatures and may take several minutes.
The API starts only when clamd is healthy and never parses a file after a scan error.
The default 25 MiB upload limit is below clamd's default 100 MiB INSTREAM limit.
If increasing uploads, update clamd StreamMaxLength/MaxScanSize/MaxFileSize and the
API /tmp quota and frontend nginx client_max_body_size together. Keep archive
limits within scanner limits. Do not expose port 3310 to the host.
