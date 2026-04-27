# NewsPlatform - Premium News Subscription SaaS

A complete Django-based subscription platform for news and content delivery with automated news aggregation, tiered access control, and payment processing via Lemon Squeezy.

## 🚀 Features

### Core Functionality
- **User Authentication** - JWT-based authentication with registration and login
- **Subscription Management** - Multiple tiers (Free, Premium, Pro) with recurring billing
- **Payment Processing** - Lemon Squeezy integration for secure payments
- **Content Management** - Full CMS for articles with categories, tags, and authors
- **Automated News Fetching** - Celery tasks to fetch news from NewsAPI.org and RSS feeds
- **Smart Auto-Publishing** - Trusted sources auto-publish, others go to drafts for review
- **Paywall System** - Tier-based access control with free article limits

### User Features
- **Reading List** - Save articles to read later
- **Bookmarks** - Permanent article bookmarks with personal notes
- **Article Views Tracking** - Analytics for popular content
- **Search** - Full-text search across all articles
- **Payment History** - View all transactions
- **Subscription Management** - Upgrade, downgrade, or cancel subscriptions

### Admin Features
- **Django Admin** - Full content management interface
- **Manual News Fetch** - Trigger news fetching from admin
- **Draft Review System** - Review auto-fetched articles before publishing
- **Analytics Dashboard** - View article performance and user metrics

## 📋 Table of Contents

- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Project](#running-the-project)
- [Celery Setup](#celery-setup)
- [API Endpoints](#api-endpoints)
- [News Fetching](#news-fetching)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| Backend | Django 5.x, Django REST Framework |
| Database | PostgreSQL (or SQLite for development) |
| Task Queue | Celery with Redis/RabbitMQ |
| Payments | Lemon Squeezy API |
| Authentication | JWT (djangorestframework-simplejwt) |
| Frontend | Django Templates, Tailwind CSS, Alpine.js |
| News APIs | NewsAPI.org, RSS Feeds (feedparser) |
| Async Tasks | Celery Beat for scheduled fetching |
| HTTP Client | Requests |

### Prerequisites

- Python 3.10+
- PostgreSQL (or SQLite for development)
- Redis (for Celery)
- Node.js and npm (for Tailwind CSS)
- Requirements.txt (contains all the libraries name that are required)

### Installation

- Clone repository
- Create virtual environment
- Install dependencies (requirements.txt)
- Create database
- Run migrations
- Start redis
- Start celery
- Start development server
