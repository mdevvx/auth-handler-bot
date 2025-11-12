# 🛡️ Auth Handler Discord Bot

A **secure role-based authentication system** for Discord servers — powered by **Supabase**.
This bot allows administrators to manage users, roles, and authentication channels with **multi-role support**, **login/logout tracking**, and **user statistics**.

---

## 🚀 Features

### 🔐 Authentication System

* `/setup_auth` — Posts the login portal with a **Login** button.
* `/login` — Users log in with **email + password**.
* First-time logins automatically link Discord accounts.
* Roles are assigned automatically on successful login.

### 👋 Logout System

* `/setup_logout` — Posts a **Logout** embed with a logout button.
* Users can confirm logout and have their roles removed safely.
* Logout events are logged in Supabase and Discord log channels.

### 🧑‍💼 Admin User Management

Admins can create and manage users directly within Discord:

* `/create_user` — Create a new user with one or more roles.
* `/update_user` — Edit user info or roles.
* `/read_user` — View specific user details.
* `/read_all_users` — View all registered users.
* `/delete_user` — Delete users safely (with confirmation).

Includes **multi-role selection**, **role mentions**, and **password auto-generation**.

### ⚙️ Server Configuration Commands

Server admins can easily configure bot channels:

* `/set_login_channel` — Set the login portal channel.
* `/set_logout_channel` — Set the logout channel.
* `/set_logging_channel` — Set the log channel for audit messages.
* `/view_config` — Display current configuration and setup tips.

### 🧾 Role Management

* `/add_signup_role` — Add a role to signup options.
* `/remove_signup_role` — Remove a signup role.
* `/list_signup_roles` — View all configured signup roles.
* `/clear_signup_roles` — Remove all signup roles.

### 📊 User Statistics

Track user activity over time:

* `/user_stats period:<day|week|month|year>`
  → Shows login/logout count and active hours.
* Admins can view stats for **other users** too.

### 🧠 Utility Commands

* `/help` — Displays all bot commands and usage.
* `!sync` — Manually sync slash commands.
* `!botinfo` — Display bot info, uptime, latency, and command list.

---

## 🧩 Tech Stack

| Component        | Description                         |
| ---------------- | ----------------------------------- |
| **discord.py**   | Discord bot framework               |
| **Supabase**     | Database backend (PostgreSQL + API) |
| **dotenv**       | Environment variable management     |
| **asyncio**      | Asynchronous event handling         |
| **Python 3.10+** | Required runtime                    |

---

## 📁 Project Structure

```
.
├── bot.py                 # Main bot entry point
├── cogs/
│   ├── auth.py            # Authentication commands and login flow
│   ├── logout.py          # Logout system and embed setup
│   ├── admin_users.py     # Multi-role user management
│   ├── user_stats.py      # Login/logout activity statistics
│
├── config/
│   ├── settings.py        # Environment configuration
│   ├── database.py        # Supabase client and connection utilities
│
├── models/
│   ├── user.py            # User database operations
│   ├── server_config.py   # Per-server channel and log settings
│   ├── allowed_roles.py   # Allowed signup roles model
│
├── ui/
│   ├── embeds.py          # Reusable embed templates
│   ├── modals.py          # Login/Create/Update modals
│   ├── views.py           # Button views for login/logout flows
│
├── utils/
│   ├── logger.py          # Centralized logging system
│   ├── helpers.py         # Input validation and helper functions
│
├── requirements.txt       # Python dependencies
└── .env                   # Environment configuration file
```

---

## ⚙️ Setup Guide

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/auth-handler-bot.git
cd auth-handler-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

Create a `.env` file (if not already present) and add:

```env
# Discord Bot
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN

# Supabase Credentials
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=your-service-key

# Optional Settings
LOG_LEVEL=INFO
PASSWORD_LENGTH=12
OWNER_ID=your_discord_id
```

### 4. Run the Bot

```bash
python bot.py
```

---

## 🧑‍💻 Admin Setup Steps

1. **Set Channels:**

   * `/set_login_channel #auth-login`
   * `/set_logout_channel #auth-logout`
   * `/set_logging_channel #auth-logs`

2. **Add Roles for Signup:**

   * `/add_signup_role @Member`
   * `/add_signup_role @VIP`

3. **Post Authentication Interfaces:**

   * In login channel: `/setup_auth`
   * In logout channel: `/setup_logout`

4. **Verify Configuration:**

   * `/view_config`

---

## 📊 Example Command Usage

```bash
/create_user
/update_user email:user@example.com
/delete_user email:user@example.com
/read_user email:user@example.com
/user_stats period:month
```

---

## 🧾 Database Schema (Supabase)

| Table           | Description                                       |
| --------------- | ------------------------------------------------- |
| `users`         | Stores user profiles, roles, and Discord bindings |
| `login_history` | Tracks login/logout attempts with timestamps      |
| `allowed_roles` | Whitelisted roles for signup                      |
| `server_config` | Per-guild channel and log settings                |

---

## 🧰 Logging

Logs are stored in the `/logs` directory:

* `bot_YYYYMMDD.log` — All logs
* `errors_YYYYMMDD.log` — Error-only logs

---

## 🛠️ Development Notes

* All commands use **slash commands** (`/`).
* Supports **multi-server** configurations.
* Fully **async**, built using `discord.py 2.x`.
* Login/logout events are logged both in **Discord** and **Supabase**.

---

## 🧑‍🏫 Example Workflow

**Admin creates a user → User logs in → Roles are assigned → User logs out → Roles are removed → Stats tracked.**

---

## 🪪 License

MIT License © 2025 Auth Handler Bot Team

Would you like me to include a **Quick Start (Developer)** section with steps for setting up Supabase tables automatically (SQL schema)?
