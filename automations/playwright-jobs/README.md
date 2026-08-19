# Playwright Job Scraper

Browser-based job scraping using Playwright with AI filtering.

## Overview

This automation uses Playwright to scrape job postings from websites, filters them using AI, and sends notifications via Telegram.

## Workflow

The workflow is a placeholder - the actual implementation is done via the Playwright service.

## Requirements

- PostgreSQL connection for job storage
- OpenRouter API key for AI filtering
- Telegram bot token for notifications
- Playwright service running

## Credentials Mapping

| n8n Credential | Provider |
|----------------|----------|
| postgres | postgresql |
| openRouterApi | openrouter |
| telegramApi | telegram |

## Source

Based on workflow: `05-playwright-jobs.json`