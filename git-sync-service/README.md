# Bidirectional GitHub ↔ Gitea Sync Service

A comprehensive Docker-based service for bidirectional synchronization between GitHub and Gitea repositories with real-time webhook integration.

## 🚀 Features

- **Bidirectional Sync**: Automatically synchronize repositories between GitHub and Gitea
- **Real-time Webhooks**: Instant sync triggers on repository changes
- **Repository Import**: Import existing GitHub repositories to Gitea
- **Docker Containerized**: Easy deployment with Docker Compose
- **REST API**: FastAPI web service with comprehensive endpoints
- **Automated Setup**: Scripts for webhook configuration

## 📋 Prerequisites

- Docker and Docker Compose
- GitHub Personal Access Token
- Gitea instance with API token
- Network access between services

## 🛠️ Quick Start

### 1. Configure Environment

Copy the example environment file and add your tokens:

```bash
cp .env.example .env
```

Edit `.env` with your actual tokens:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_USER=your_github_username

# Gitea Configuration
GITEA_URL=http://your-gitea-host:3000
GITEA_TOKEN=your_gitea_api_token
GITEA_USER=your_gitea_username
```

### 2. Deploy the Service

```bash
# Start the service
docker-compose up -d

# Check service health
curl http://localhost:9000/health
```

### 3. Setup Webhooks

Run the automated webhook setup script:

```bash
# Make the script executable
chmod +x scripts/setup-webhooks.sh

# Setup webhooks for all repositories
./scripts/setup-webhooks.sh
```

### 4. Import Repositories

Import existing GitHub repositories to Gitea:

```bash
# Trigger manual import
curl -X POST http://localhost:9000/sync/manual
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/status` | GET | Sync service status |
| `/repositories` | GET | List tracked repositories |
| `/sync/manual` | POST | Trigger manual sync/import |
| `/webhooks/github` | POST | GitHub webhook handler |
| `/webhooks/gitea` | POST | Gitea webhook handler |
| `/logs` | GET | Recent sync logs |

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | Required |
| `GITHUB_USER` | GitHub username | Required |
| `GITEA_URL` | Gitea instance URL | Required |
| `GITEA_TOKEN` | Gitea API token | Required |
| `GITEA_USER` | Gitea username | Required |
| `SYNC_INTERVAL` | Sync check interval (seconds) | 300 |
| `CONFLICT_RESOLUTION` | How to handle conflicts | manual |
| `WEBHOOK_SECRET` | Webhook authentication secret | auto-generated |

### Sync Features

```bash
# Enable/disable sync features
SYNC_BRANCHES=true
SYNC_TAGS=true  
SYNC_RELEASES=true
SYNC_ISSUES=false
SYNC_PRS=false
```

### Repository Filtering

```bash
# Optional: Only sync specific repositories
INCLUDE_REPOS=repo1,repo2,repo3

# Optional: Exclude specific repositories  
EXCLUDE_REPOS=test-repo,temp-repo
```

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐
│   GitHub    │◄──►│ Sync Service│◄──►│   Gitea     │
│ Repositories│    │   (FastAPI) │    │Repositories │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │              ┌─────────┐              │
       └──────────────┤ Webhooks├──────────────┘
                      └─────────┘
                           │
                      ┌─────────┐
                      │  Redis  │
                      │ (Queue) │
                      └─────────┘
```

## 📊 Service Components

- **sync-main.py**: Main sync service with import functionality
- **src/services/**: Core sync engine, webhook handler, scheduler  
- **src/utils/**: Git operations, API clients, logging utilities
- **src/database/**: SQLite models for sync state tracking
- **docker-compose.yml**: Complete service orchestration
- **scripts/**: Automated setup and management scripts

## 🔄 Sync Process

1. **Webhook Trigger**: GitHub/Gitea sends webhook on repository changes
2. **Event Processing**: Service validates and processes the webhook
3. **Repository Sync**: Clones, compares, and synchronizes changes
4. **Conflict Resolution**: Handles merge conflicts based on configuration
5. **Status Updates**: Logs results and updates repository status

## 📝 Logging

Service logs include:
- Repository sync operations
- Webhook event processing  
- Error handling and resolution
- Performance metrics

Access logs via:
```bash
# View service logs
docker-compose logs git-sync

# API endpoint for recent logs
curl http://localhost:9000/logs
```

## 🛡️ Security

- API tokens stored in environment variables
- Webhook signature validation
- Secure Git authentication
- Network isolation with Docker

## 🔧 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify tokens have required permissions
   - Check token expiration dates

2. **Network Connectivity**
   - Ensure services can reach each other
   - Check firewall and network policies

3. **Webhook Delivery Failures**
   - Verify webhook URLs are accessible
   - Check webhook secret configuration

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG docker-compose up
```

## 🤝 Contributing

This service was created with Claude Code for bidirectional repository synchronization. Contributions and improvements are welcome!

## 📄 License

Open source - feel free to use and modify as needed.

---

🤖 Generated with [Claude Code](https://claude.ai/code)