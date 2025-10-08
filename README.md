# Discord Authentication Bot

A professional, scalable Discord bot that provides user authentication and role management across multiple servers. Users can sign up with their email, receive secure credentials, and log in to gain access to designated roles.

## 🌟 Features

### Core Functionality

-   **User Registration (Signup)**: Users create accounts with email and password
-   **User Authentication (Login)**: Role assignment after credential verification
-   **Logout System**: Role removal with confirmation prompt
-   **Role Management**: Admins configure which roles users can select during signup
-   **Multi-Server Support**: Works independently across unlimited Discord servers
-   **Database Integration**: Persistent data storage using Supabase (PostgreSQL)
-   **Security**: Input validation, unique constraints, and secure password generation

### Admin Features

-   **Dynamic Role Configuration**: Add/remove signup roles per server
-   **Channel Setup**: Configure login and logout channels via commands
-   **Configuration View**: See current bot setup at a glance
-   **Manual Command Sync**: Force-sync slash commands when needed
-   **Role List View**: Display all available signup roles

### User Experience

-   **Interactive Modals**: Clean forms for data entry
-   **Dropdown Menus**: Select roles from configured options
-   **Confirmation Prompts**: Prevent accidental logout
-   **Ephemeral Messages**: Private responses visible only to the user
-   **Rich Embeds**: Beautiful, informative messages

---

## 📋 Table of Contents

-   [Prerequisites](#prerequisites)
-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Database Setup](#database-setup)
-   [Running the Bot](#running-the-bot)
-   [Commands](#commands)
-   [Usage Guide](#usage-guide)
-   [Project Structure](#project-structure)
-   [Troubleshooting](#troubleshooting)
-   [Security Considerations](#security-considerations)
-   [Contributing](#contributing)
-   [License](#license)

---

## 🔧 Prerequisites

Before you begin, ensure you have:

-   **Python 3.8+** installed
-   **Discord Account** with server admin permissions
-   **Supabase Account** (free tier works perfectly)
-   **Discord Bot Token** from Discord Developer Portal
-   Basic understanding of Discord server management

---

## 📥 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/discord-auth-bot.git
cd discord-auth-bot
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Project Structure

Create the following folder structure:

```
discord-auth-bot/
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── database.py
│
├── cogs/
│   ├── __init__.py
│   ├── auth.py
│   └── logout.py
│
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── server_config.py
│   └── allowed_roles.py
│
├── ui/
│   ├── __init__.py
│   ├── embeds.py
│   ├── views.py
│   └── modals.py
│
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── helpers.py
│
├── database/
│   └── schema.sql
│
├── logs/
│
├── main.py
├── .env
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Configuration

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name
3. Go to **"Bot"** → Click **"Add Bot"**
4. Under **"TOKEN"**, click **"Reset Token"** and copy it (save securely!)
5. Enable these **Privileged Gateway Intents**:
    - ✅ Server Members Intent
    - ✅ Message Content Intent
6. Save changes

### 2. Generate Bot Invite Link

1. Go to **"OAuth2"** → **"URL Generator"**
2. Select scopes:
    - ✅ `bot`
    - ✅ `applications.commands`
3. Select bot permissions:
    - ✅ Manage Roles
    - ✅ Send Messages
    - ✅ Embed Links
    - ✅ Read Message History
    - ✅ Use Slash Commands
4. Copy the generated URL and invite bot to your server

### 3. Setup Supabase

1. Go to [Supabase](https://supabase.com) and create account
2. Click **"New Project"**
3. Fill in project details and create
4. Once ready, go to **Settings** → **API**
5. Copy:
    - **Project URL**
    - **anon/public key**

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here

# Bot Configuration (Optional)
LOG_LEVEL=INFO
PASSWORD_LENGTH=12
```

---

## 🗄️ Database Setup

### 1. Create Database Tables

1. Go to your Supabase Dashboard
2. Click **"SQL Editor"** in the sidebar
3. Click **"New query"**
4. Copy the entire contents of `database/schema.sql`
5. Paste into the editor
6. Click **"Run"** or press `Ctrl+Enter`
7. Verify success message appears

### 2. Verify Tables Created

1. Click **"Table Editor"** in sidebar
2. You should see these tables:
    - `server_config`
    - `allowed_roles`
    - `users`
    - `login_history`
    - `schema_version`

---

## 🚀 Running the Bot

### 1. Start the Bot

```bash
python main.py
```

### 2. Expected Output

You should see:

```
INFO     | Initializing database connection...
INFO     | ✓ Database connection established successfully
INFO     | Database initialized successfully!
INFO     | Starting bot...
INFO     | Loading cogs...
INFO     | ✓ Loaded cogs.auth
INFO     | ✓ Loaded cogs.logout
INFO     | Bot logged in as YourBot#1234 (ID: ...)
INFO     | Connected to 1 guild(s)
INFO     | ✓ Synced 8 global command(s)
INFO     | Bot is ready!
```

### 3. Sync Commands (First Time)

In your Discord server, type:

```
!sync
```

This registers all slash commands. You should see:

```
✅ Commands Synced Successfully!
📊 Global Commands: 8
🌐 Synced to Guilds: 1/1
```

---

## 📜 Commands

### Admin Commands (Slash Commands)

| Command                        | Description                       | Permission    |
| ------------------------------ | --------------------------------- | ------------- |
| `/set_login_channel #channel`  | Set the login/signup channel      | Administrator |
| `/set_logout_channel #channel` | Set the logout channel            | Administrator |
| `/add_signup_role @role`       | Add a role to signup options      | Administrator |
| `/remove_signup_role @role`    | Remove a role from signup options | Administrator |
| `/list_signup_roles`           | List all available signup roles   | Administrator |
| `/clear_signup_roles`          | Remove all signup roles           | Administrator |
| `/setup_auth`                  | Create authentication embed       | Administrator |
| `/setup_logout`                | Create logout embed               | Administrator |
| `/view_config`                 | View current configuration        | Administrator |

### Bot Management Commands (Text Commands)

| Command    | Description                  | Permission    |
| ---------- | ---------------------------- | ------------- |
| `!sync`    | Sync slash commands globally | Administrator |
| `!botinfo` | Display bot information      | Everyone      |

---

## 📖 Usage Guide

### For Server Administrators

#### Initial Setup

1. **Set Login Channel**

    ```
    /set_login_channel #auth-portal
    ```

2. **Set Logout Channel**

    ```
    /set_logout_channel #logout
    ```

3. **Add Signup Roles** (the roles users can select)

    ```
    /add_signup_role @Developer
    /add_signup_role @Designer
    /add_signup_role @Manager
    /add_signup_role @Member
    ```

4. **Verify Configuration**

    ```
    /view_config
    ```

5. **Setup Auth Embed** (in the login channel)

    ```
    /setup_auth
    ```

6. **Setup Logout Embed** (in the logout channel)
    ```
    /setup_logout
    ```

#### Managing Roles

**View all signup roles:**

```
/list_signup_roles
```

**Remove a specific role:**

```
/remove_signup_role @Developer
```

**Clear all roles:**

```
/clear_signup_roles
```

### For Users

#### Signing Up

1. Go to the **login channel**
2. Click the **📝 Sign Up** button
3. Fill in the modal:
    - Enter your full name
    - Enter your email address
4. Select your role from the dropdown menu
5. You'll receive your credentials in a private message
6. **Save your password!**

#### Logging In

1. Go to the **login channel**
2. Click the **🔑 Login** button
3. Enter your email and password
4. Your role will be assigned automatically
5. You now have access to the server!

#### Logging Out

1. Go to the **logout channel**
2. Click the **👋 Logout** button
3. Review the roles that will be removed
4. Click **"Yes, Logout"** to confirm
5. Your roles are removed (you can login again anytime)

---

## 📁 Project Structure

```
discord-auth-bot/
│
├── config/                      # Configuration files
│   ├── __init__.py
│   ├── settings.py             # Environment variables and settings
│   └── database.py             # Database connection management
│
├── cogs/                       # Discord bot cogs (command groups)
│   ├── __init__.py
│   ├── auth.py                # Authentication commands
│   └── logout.py              # Logout commands
│
├── models/                     # Database models
│   ├── __init__.py
│   ├── user.py                # User CRUD operations
│   ├── server_config.py       # Server configuration management
│   └── allowed_roles.py       # Signup roles management
│
├── ui/                        # User interface components
│   ├── __init__.py
│   ├── embeds.py             # Discord embed templates
│   ├── views.py              # Button views
│   └── modals.py             # Input forms
│
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── logger.py             # Logging configuration
│   └── helpers.py            # Helper functions
│
├── database/                  # Database files
│   └── schema.sql            # Database schema
│
├── logs/                      # Log files (auto-generated)
│
├── main.py                    # Bot entry point
├── .env                       # Environment variables (not in git)
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore file
└── README.md                # This file
```

---

## 🐛 Troubleshooting

### Bot doesn't start

**Error: "DISCORD_TOKEN is required"**

-   Check your `.env` file has the correct token
-   Make sure `.env` is in the root directory

**Error: "Failed to initialize database"**

-   Verify Supabase credentials in `.env`
-   Check internet connection
-   Ensure database tables are created

### Slash commands don't appear

1. Run `!sync` in Discord
2. Wait a few minutes for Discord to propagate commands
3. Try kicking and re-inviting the bot
4. Verify bot has `applications.commands` scope

### Can't assign roles

**"Missing permissions to assign role"**

-   Go to Server Settings → Roles
-   Drag the bot's role **above** the roles it needs to assign
-   Verify bot has "Manage Roles" permission

### Signup roles not showing

**"No roles available for signup"**

-   Make sure you added roles with `/add_signup_role`
-   Verify roles exist in the server
-   Check roles aren't managed by another bot
-   Ensure roles don't have Administrator permission

### Login/Signup buttons don't work

**Buttons are unresponsive**

-   Restart the bot
-   Run `!sync` again
-   Check bot logs in `logs/` folder
-   Verify bot has proper intents enabled

### Database errors

**"Connection failed"**

-   Check Supabase credentials
-   Verify Supabase project is active
-   Check for firewall blocking connections

**"Unique constraint violation"**

-   User already exists with that email or Discord ID
-   Use different email or contact admin to remove old account

---

## 🔒 Security Considerations

### Current Implementation

⚠️ **WARNING**: The current implementation stores passwords in **plain text**. This is acceptable for development/testing but **NOT for production use**.

### For Production Use

Before deploying to production, implement these security measures:

#### 1. Password Hashing

Install bcrypt:

```bash
pip install bcrypt
```

Update `models/user.py`:

```python
import bcrypt

# When creating user
password = generate_password()
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Store hashed_password.decode('utf-8') in database

# When authenticating
stored_hash = user_data['password'].encode('utf-8')
provided_password = password.encode('utf-8')
if bcrypt.checkpw(provided_password, stored_hash):
    # Authentication successful
```

#### 2. Additional Security Measures

-   **Rate Limiting**: Implement rate limits on login attempts
-   **Password Reset**: Add password reset functionality
-   **2FA**: Consider two-factor authentication
-   **Audit Logging**: Log all authentication events
-   **Session Management**: Implement session tokens
-   **Input Sanitization**: Already implemented, but review regularly
-   **SQL Injection Protection**: Supabase handles this, but validate all inputs
-   **Environment Variables**: Never commit `.env` to git

#### 3. Database Security

-   Enable Row Level Security (RLS) in Supabase
-   Use service role key only from backend
-   Implement database backups
-   Monitor for suspicious activity

---

## 📊 Database Schema

### Tables

**server_config**

-   Stores per-server channel configurations
-   Fields: guild_id, login_channel_id, logout_channel_id

**allowed_roles**

-   Stores roles users can select during signup
-   Fields: guild_id, role_id, role_name

**users**

-   Stores user authentication data
-   Fields: guild_id, discord_user_id, full_name, email, password, designation
-   Constraints: Unique email per guild, unique user per guild

**login_history**

-   Tracks login attempts and success/failure
-   Fields: user_id, guild_id, discord_user_id, email, success, attempted_at

### Useful Queries

**Get all users in a guild:**

```sql
SELECT * FROM users WHERE guild_id = 123456789;
```

**Get guild statistics:**

```sql
SELECT * FROM get_guild_stats(123456789);
```

**Clean up when bot leaves a server:**

```sql
SELECT cleanup_guild_data(123456789);
```

---

## 📝 Logging

Logs are automatically created in the `logs/` folder:

-   `bot_YYYYMMDD.log` - All bot activity
-   `errors_YYYYMMDD.log` - Errors only

### View Logs

```bash
# View today's logs
cat logs/bot_20250108.log          # Mac/Linux
type logs\bot_20250108.log         # Windows

# View errors only
cat logs/errors_20250108.log       # Mac/Linux
type logs\errors_20250108.log      # Windows

# Follow logs in real-time
tail -f logs/bot_20250108.log      # Mac/Linux
Get-Content logs\bot_20250108.log -Wait  # Windows PowerShell
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style

-   Follow PEP 8 guidelines
-   Add docstrings to all functions
-   Include type hints where possible
-   Write descriptive commit messages
-   Add comments for complex logic

---

## 🎯 Roadmap

### Planned Features

-   [ ] Password hashing with bcrypt
-   [ ] Password reset functionality
-   [ ] Email verification
-   [ ] Two-factor authentication (2FA)
-   [ ] User profile management
-   [ ] Role change requests
-   [ ] Admin dashboard (web interface)
-   [ ] Statistics and analytics
-   [ ] Backup and restore commands
-   [ ] Multi-language support
-   [ ] Custom welcome messages
-   [ ] Activity logging
-   [ ] Integration with other services

---

## ❓ FAQ

**Q: Can I use this bot in multiple servers?**  
A: Yes! The bot is designed to work independently in unlimited servers.

**Q: Is the bot data separated per server?**  
A: Yes, all data is stored per guild_id, so each server has its own users and configuration.

**Q: What happens if I remove the bot from my server?**  
A: User data remains in the database. Use the `cleanup_guild_data()` function to remove it.

**Q: Can users have different roles in different servers?**  
A: Yes! A user can sign up with different roles in each server.

**Q: How secure is this bot?**  
A: Currently suitable for development. For production, implement password hashing (see Security Considerations).

**Q: Can I customize the embeds and messages?**  
A: Yes! Edit the files in `ui/embeds.py` to customize all messages.

**Q: Does the bot support custom prefixes?**  
A: The bot uses `/` for slash commands and `!` for admin commands. You can change the `!` prefix in `main.py`.

**Q: Can I add more signup fields?**  
A: Yes! Update the database schema, models, and modals to add additional fields.

---

## 📞 Support

If you encounter issues or have questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [FAQ](#faq)
3. Check existing [GitHub Issues](https://github.com/yourusername/discord-auth-bot/issues)
4. Create a new issue with:
    - Bot version
    - Error message (from logs)
    - Steps to reproduce
    - Expected vs actual behavior

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

-   [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
-   [Supabase](https://supabase.com) - Database and backend services
-   [Discord](https://discord.com) - Platform
-   All contributors and users

---

**Made with ❤️ by [Your Name]**

**Discord Bot Version:** 2.0  
**Last Updated:** January 2025

---

## 🚀 Quick Start Summary

```bash
# 1. Clone and setup
git clone <repo-url>
cd discord-auth-bot
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your credentials

# 3. Setup database
# Run schema.sql in Supabase SQL Editor

# 4. Start bot
python main.py

# 5. In Discord
!sync
/set_login_channel #channel
/set_logout_channel #channel
/add_signup_role @role
/setup_auth
/setup_logout
```

**That's it! Your bot is ready to use!**
