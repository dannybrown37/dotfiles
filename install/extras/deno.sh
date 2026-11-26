#!/usr/bin/env bash
## @extra deno | Deno 2 JavaScript/TypeScript runtime
set -euo pipefail

# shellcheck source=install/curl_retry.sh
source "$(dirname "${BASH_SOURCE[0]}")/../curl_retry.sh"

curl_buffered -fsSL https://deno.land/install.sh | sh
