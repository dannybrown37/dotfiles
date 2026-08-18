#!/usr/bin/env bash
## Demo script to show bash-preexec hooks in action

echo "=== bash-preexec Hooks Demo ==="
echo
echo "This script demonstrates the hooks added to config/.bash_preexec_hooks"
echo "To see them in action, source your .bashrc in a new shell:"
echo
echo "  source ~/.bashrc"
echo
echo "Then try these commands:"
echo
echo "1. AWS Profile Context:"
echo "   export AWS_PROFILE=production"
echo "   aws s3 ls"
echo "   Expected: Gray text showing [AWS Profile: production]"
echo
echo "2. Long-Running Command (requires \$PERSONAL_ALERT_TOPIC set):"
echo "   sleep 35"
echo "   Expected: Phone notification via ntfy.sh after completion"
echo
echo "3. Auto-Activate Environment:"
echo "   cd into a directory with .venv/, .nvmrc, or .node-version"
echo "   Expected: Automatic activation message"
echo
echo "=== Files Created ==="
echo "  config/.bash_preexec_hooks      - 3 hook implementations"
echo "  scripts/test_bash_preexec_hooks.sh - Test suite"
echo "  docs/bash-preexec-hooks.md      - Full documentation"
echo
echo "To customize or disable hooks, edit config/.bash_preexec_hooks"
echo "See docs/bash-preexec-hooks.md for full details"
