#!/usr/bin/env bash
# Apply CVSM's labels, merge settings and protection of main to a GitHub repo.
# Run once per repo as an admin, from the repo root; it is safe to run again.
#     bash scripts/setup.sh [owner/repo]    (default: the repo of the current directory)
set -euo pipefail
repo=${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}

label() { echo "label $1"; gh label create "$1" --repo "$repo" --color "$2" --description "$3" --force; }
label study 1d76db "Research study (parent issue)"
label plan 5319e7 "Development plan (parent issue)"
label code 0e8a16 "Code task: one issue, one branch, one PR"
label run fbca04 "Run task: closes with a results comment"
label needs-decision d93f0b "Agent stopped; waiting for the human"

echo "settings: squash merge only, PR title as subject, delete branches on merge"
gh api -X PATCH "repos/$repo" --silent \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=BLANK

echo "protect main: PR with checks guard and test, admins included, no force push or deletion"
gh api -X PUT "repos/$repo/branches/main/protection" --silent --input - <<'JSON'
{
  "required_status_checks": {"strict": false, "contexts": ["guard", "test"]},
  "enforce_admins": true,
  "required_pull_request_reviews": {"required_approving_review_count": 0},
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
echo "done: $repo"
