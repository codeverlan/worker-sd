#!/bin/bash
# Setup webhooks for GitHub and Gitea repositories

# Configuration
GITHUB_TOKEN="${GITHUB_TOKEN:-your_github_token_here}"
GITHUB_USER="${GITHUB_USER:-codeverlan}"
GITEA_URL="${GITEA_URL:-http://cloud-dev:3020}"
GITEA_TOKEN="${GITEA_TOKEN:-your_gitea_token_here}"
GITEA_USER="${GITEA_USER:-tbwyler}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-git-sync-webhook-secret-2024}"
SYNC_SERVICE_URL="${SYNC_SERVICE_URL:-http://cloud-dev:9000}"

echo "Setting up webhooks for GitHub ↔ Gitea sync..."
echo "GitHub User: $GITHUB_USER"
echo "Gitea User: $GITEA_USER"
echo "Sync Service: $SYNC_SERVICE_URL"

# Function to create GitHub webhook
create_github_webhook() {
    local repo=$1
    echo "Creating GitHub webhook for $repo..."
    
    curl -X POST \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/hooks" \
        -d "{
            \"name\": \"web\",
            \"active\": true,
            \"events\": [\"push\", \"create\", \"delete\", \"repository\", \"release\"],
            \"config\": {
                \"url\": \"$SYNC_SERVICE_URL/webhooks/github\",
                \"content_type\": \"json\",
                \"secret\": \"$WEBHOOK_SECRET\",
                \"insecure_ssl\": \"0\"
            }
        }"
}

# Function to create Gitea webhook
create_gitea_webhook() {
    local repo=$1
    echo "Creating Gitea webhook for $repo..."
    
    curl -X POST \
        -H "Authorization: token $GITEA_TOKEN" \
        -H "Content-Type: application/json" \
        "$GITEA_URL/api/v1/repos/$GITEA_USER/$repo/hooks" \
        -d "{
            \"type\": \"gitea\",
            \"active\": true,
            \"events\": [\"push\", \"create\", \"delete\", \"repository\", \"release\"],
            \"config\": {
                \"url\": \"$SYNC_SERVICE_URL/webhooks/gitea\",
                \"content_type\": \"json\",
                \"secret\": \"$WEBHOOK_SECRET\"
            }
        }"
}

# Function to list GitHub repositories
list_github_repos() {
    echo "Fetching GitHub repositories..."
    curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
        "https://api.github.com/users/$GITHUB_USER/repos?per_page=100" | \
        jq -r '.[].name'
}

# Function to list Gitea repositories
list_gitea_repos() {
    echo "Fetching Gitea repositories..."
    curl -s -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/users/$GITEA_USER/repos?limit=100" | \
        jq -r '.[].name'
}

# Main execution
echo "Step 1: Updating webhook secret in .env file..."
sed -i "s/WEBHOOK_SECRET=.*/WEBHOOK_SECRET=$WEBHOOK_SECRET/" .env

echo "Step 2: Getting repository lists..."

# Get GitHub repositories
GITHUB_REPOS=$(list_github_repos)
echo "GitHub repositories found:"
echo "$GITHUB_REPOS"

echo ""

# Get Gitea repositories  
GITEA_REPOS=$(list_gitea_repos)
echo "Gitea repositories found:"
echo "$GITEA_REPOS"

echo ""
echo "Step 3: Setting up webhooks..."

# Setup webhooks for GitHub repositories
echo "Setting up GitHub webhooks..."
while IFS= read -r repo; do
    if [ -n "$repo" ]; then
        create_github_webhook "$repo"
        echo "✓ GitHub webhook created for $repo"
        sleep 1  # Rate limiting
    fi
done <<< "$GITHUB_REPOS"

echo ""

# Setup webhooks for Gitea repositories
echo "Setting up Gitea webhooks..."
while IFS= read -r repo; do
    if [ -n "$repo" ]; then
        create_gitea_webhook "$repo"
        echo "✓ Gitea webhook created for $repo"
        sleep 1  # Rate limiting
    fi
done <<< "$GITEA_REPOS"

echo ""
echo "Webhook setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the sync service: docker-compose up -d"
echo "2. Check service status: curl http://cloud-dev:8080/health"
echo "3. View repositories: curl http://cloud-dev:8080/repositories"
echo "4. Trigger manual sync: curl -X POST http://cloud-dev:8080/sync/manual"