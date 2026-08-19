# Laboral Job Scraper

Automated job scraping from LinkedIn and InfoJobs with AI filtering.

## Overview

This automation scrapes job postings from LinkedIn and InfoJobs, filters them using AI, and sends notifications via Telegram.

## Workflow

The workflow is a placeholder - the actual scraping is done via the Playwright service.

## Requirements

- PostgreSQL connection for job storage
- OpenRouter API key for AI filtering
- Telegram bot token for notifications
- Playwright scraper service

## Credentials Mapping

| n8n Credential | Provider |
|----------------|----------|
| postgres | postgresql |
| openRouterApi | openrouter |
| telegramApi | telegram |

## Source

Based on workflow: `02-laboral.json`