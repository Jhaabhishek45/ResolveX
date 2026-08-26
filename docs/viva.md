# Viva Reference

## Why Flask?

Flask is lightweight, easy to understand, and well suited to a small university web application.

## Why SQLite?

SQLite is serverless, reliable for an academic MVP, and keeps setup simple.

## Why OOP?

Domain models describe the campus problem space, while focused services keep triage, assignment, and analytics responsibilities separate.

## How triage works

`TriageEngine` applies transparent category and subcategory rules, uses reported impact for priority, calculates a target due time, and counts recent related issues.

## How the dashboard works

`AnalyticsService` runs parameterized SQLite queries. Dashboard values are calculated from issue records rather than hardcoded.
