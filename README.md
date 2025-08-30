# Kit Gmail - Knowledge Integration Tool

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive Python application for intelligent Gmail mailbox management, featuring AI-powered email summarization and advanced organization capabilities.

## ✨ Features

### 📧 Email Management
- **Smart Classification**: Automatically categorize emails (receipts, junk, mailing lists, critical emails)
- **Intelligent Cleanup**: Remove duplicates, archive old emails, delete junk automatically
- **Contact Analysis**: Extract and analyze email contacts with behavioral insights
- **Receipt Organization**: Automatically organize purchase receipts and invoices
- **Mailing List Management**: Detect and organize newsletter subscriptions

### 🤖 AI-Powered Insights
- **Email Summarization**: Daily, weekly, and monthly AI-generated email summaries
- **Multiple AI Providers**: Support for Anthropic Claude, OpenAI GPT, and xAI Grok
- **Pattern Analysis**: Discover email patterns and get management recommendations
- **Batch Processing**: Analyze multiple emails simultaneously for insights

### 🔧 Advanced Features
- **Secure Configuration**: API keys stored securely using system keyring
- **Comprehensive CLI**: Feature-rich command-line interface with rich formatting
- **Database Integration**: SQLite database for contact and metadata storage
- **OAuth2 Authentication**: Secure Gmail API integration
- **Extensible Architecture**: Modular design for easy feature additions

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Gmail account with API access enabled
- API keys for desired AI services (optional but recommended)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/rickyarm/kit_gmail.git
cd kit_gmail
```

2. **Set up virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install the package**:
```bash
pip install -e .
```

### Gmail API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth2 credentials (Desktop Application)
5. Download the credentials JSON file

### Initial Configuration

1. **Initialize configuration**:
```bash
kit-gmail config init
```

2. **Set up Gmail authentication**:
```bash
kit-gmail auth setup /path/to/your/credentials.json
```

3. **Configure AI services** (optional):
```bash
kit-gmail config set anthropic_api_key your_api_key_here
kit-gmail config set openai_api_key your_api_key_here
```

4. **Verify setup**:
```bash
kit-gmail status
```

## 📖 Usage

### Basic Commands

**View application status**:
```bash
kit-gmail status
kit-gmail dashboard
```

**Quick mailbox cleanup**:
```bash
kit-gmail quick-cleanup --days 30 --dry-run
kit-gmail quick-cleanup --days 30 --execute
```

**Generate AI email summary**:
```bash
kit-gmail quick-summary --days 7
kit-gmail summarize daily --days 1
kit-gmail summarize weekly --weeks 2
```

### Email Management

**Organize emails**:
```bash
kit-gmail cleanup organize --dry-run
kit-gmail cleanup organize --execute
```

**Delete old emails**:
```bash
kit-gmail cleanup delete-old --days 90 --dry-run
kit-gmail cleanup delete-old --days 90 --execute
```

**Archive old emails**:
```bash
kit-gmail cleanup archive-old --days 60 --keep-important
```

**Remove duplicates**:
```bash
kit-gmail cleanup remove-duplicates --dry-run
kit-gmail cleanup remove-duplicates --execute
```

### Contact Management

**Analyze contacts**:
```bash
kit-gmail contacts analyze --max-emails 500
```

**List contacts**:
```bash
kit-gmail contacts list --category frequent --limit 20
kit-gmail contacts list --category important
kit-gmail contacts list --category spam
```

**Search contacts**:
```bash
kit-gmail contacts search "john@example.com"
kit-gmail contacts search "John"
```

**Get contact statistics**:
```bash
kit-gmail contacts stats
kit-gmail contacts suggestions
```

**Export contacts**:
```bash
kit-gmail contacts export --format csv --output contacts.csv
kit-gmail contacts export --format json --output contacts.json
```

### AI-Powered Summarization

**Daily summaries**:
```bash
kit-gmail summarize daily --days 1
kit-gmail summarize daily --days 3 --provider anthropic
```

**Weekly summaries**:
```bash
kit-gmail summarize weekly --weeks 1
kit-gmail summarize weekly --weeks 2 --provider openai
```

**Custom summaries**:
```bash
kit-gmail summarize custom 14 --type "bi-weekly" --save summary.md
```

**Email insights**:
```bash
kit-gmail summarize insights --type patterns --days 30
kit-gmail summarize insights --type cleanup --days 60
kit-gmail summarize insights --type security --days 90
```

**Batch email analysis**:
```bash
kit-gmail summarize analyze-batch --max-emails 50 --save analysis.json
```

### Configuration Management

**View configuration**:
```bash
kit-gmail config show
kit-gmail config validate
```

**Set configuration values**:
```bash
kit-gmail config set anthropic_api_key your_key_here
kit-gmail config set default_ai_service anthropic
```

**Get configuration values**:
```bash
kit-gmail config get anthropic_api_key
kit-gmail config get default_ai_service --show-value
```

**Backup and reset**:
```bash
kit-gmail config backup --output backup.json
kit-gmail config reset  # WARNING: Deletes all data
```

### Authentication Management

**Check authentication status**:
```bash
kit-gmail auth status
```

**Refresh credentials**:
```bash
kit-gmail auth refresh
```

**Revoke access**:
```bash
kit-gmail auth revoke
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Gmail API Configuration
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret

# AI Service Configuration
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
XAI_API_KEY=your_xai_key
DEFAULT_AI_SERVICE=anthropic

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
MAX_EMAIL_BATCH_SIZE=100
DEFAULT_SUMMARY_DAYS=7

# Email Processing
RECEIPT_KEYWORDS=receipt,invoice,order,purchase,payment
JUNK_KEYWORDS=unsubscribe,promotion,deal,offer,sale
CRITICAL_SENDERS=bank,insurance,government,tax
```

### Secure Storage

API keys are automatically stored securely using the system keyring:
- **macOS**: Keychain
- **Windows**: Windows Credential Locker  
- **Linux**: Secret Service API (GNOME Keyring, KDE KWallet)

## 🧪 Testing

**Run all tests**:
```bash
pytest
```

**Run with coverage**:
```bash
pytest --cov=kit_gmail --cov-report=html
```

**Run specific test categories**:
```bash
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

**Run with verbose output**:
```bash
pytest -v
```

## 🏗️ Architecture

```
kit_gmail/
├── src/kit_gmail/
│   ├── core/                 # Core email processing
│   │   ├── gmail_auth.py     # Gmail OAuth2 authentication
│   │   ├── gmail_manager.py  # Main Gmail operations
│   │   └── email_processor.py # Email classification
│   ├── services/             # Business logic services
│   │   ├── ai_service.py     # AI provider integration
│   │   └── contact_manager.py # Contact analysis
│   ├── cli/                  # Command-line interface
│   │   ├── main.py          # Main CLI application
│   │   └── commands/        # CLI command modules
│   └── utils/               # Utilities and helpers
│       ├── config.py        # Configuration management
│       ├── logger.py        # Logging setup
│       └── security.py     # Security utilities
└── tests/                   # Test suite
    ├── unit/                # Unit tests
    └── integration/         # Integration tests
```

## 🔒 Security & Privacy

- **Local Processing**: All email processing happens locally on your machine
- **Secure Storage**: API keys stored in system keyring, never in plain text
- **Minimal Data**: Only metadata is stored; email content is not persisted
- **OAuth2**: Secure Gmail authentication without storing passwords
- **No Data Transmission**: Email content is only sent to AI services when explicitly requested

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork and clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Install pre-commit hooks: `pre-commit install`
5. Run tests: `pytest`

### Code Quality

- **Formatting**: Black (`black .`)
- **Import Sorting**: isort (`isort .`)
- **Type Checking**: mypy (`mypy src/`)
- **Linting**: flake8 (`flake8 src/`)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Gmail API](https://developers.google.com/gmail/api) - Google's Gmail API
- [Anthropic](https://www.anthropic.com/) - Claude AI models
- [OpenAI](https://openai.com/) - GPT models  
- [xAI](https://x.ai/) - Grok models
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/rickyarm/kit_gmail/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rickyarm/kit_gmail/discussions)
- **Email**: rickyarm@users.noreply.github.com

---

**Kit Gmail** - Making email management intelligent and effortless! 📧✨