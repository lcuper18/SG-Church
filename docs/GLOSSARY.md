# Glossary

This glossary defines key terms used throughout the SG Church project documentation and codebase.

## A

### Admin
A user role with full access to all church data and settings. Admins can manage members, configure modules, and invite other users.

### API (Application Programming Interface)
A set of endpoints that allow external systems to interact with SG Church programmatically.

### App Router
Django URL routing system based on URL patterns defined in urls.py.

### ATR (Average Transaction Response)
Metric measuring API response times.

### Attendance
Record of member participation in services, events, or activities.

### Authentication
Process of verifying user identity (login).

### Authorization
Process of determining what resources a user can access (permissions).

## B

### Baptism
A Christian sacrament or ordinance. In SG Church, records of baptisms are stored in the Sacraments module.

### Celery
Distributed task queue for Python used for background job processing.

### Budget
Financial plan allocating expected income and expenses across categories.

## C

### CASL
Authorization library used for permission management in SG Church.

### Chart of Accounts
Categorized list of all financial accounts used in bookkeeping.

### Course
Educational content organized into lessons within the Learning Management System (LMS).

### CSV (Comma-Separated Values)
File format used for importing/exporting data.

### CTR (Click-Through Rate)
Metric measuring user engagement with emails or notifications.

## D

### Donation
Financial contribution made to the church. Can be one-time or recurring.

### Double-Entry Bookkeeping
Accounting method where every transaction affects at least two accounts.

## E

### Edge Functions
Serverless functions that run close to users for better performance.

### Event
Scheduled church activity such as services, meetings, or special programs.

## F

### Family
Group of related members (e.g., parents and children) in the membership system.

## G

### GDPR (General Data Protection Regulation)
European Union data privacy law that SG Church complies with.

### Group
Collection of members organized by ministry, small group, or other category.

## I

### i18n (Internationalization)
Process of designing software to support multiple languages and locales.

### ISR (Incremental Static Regeneration)
Django concept for caching and invalidating rendered pages.

## L

### Learning Path
Sequence of courses designed to achieve specific educational goals.

### Lesson
Individual unit of content within a course.

### LMS (Learning Management System)
Module for creating and delivering educational content.

## M

### Member
Individual registered in the church's membership database.

### Member Portal
User-facing interface where members can access their information and church resources.

### Middleware
Code that runs before requests are processed, used for tenant resolution and authentication.

### Migration
Script that changes database schema structure (adding tables, columns, etc.).

### Ministry
Area of church service (e.g., worship, youth, missions).

### Multi-Tenant
Architecture pattern where a single application instance serves multiple churches (tenants).

## N

### Django Auth
Built-in authentication framework for Django applications.

## O

### ORM (Object-Relational Mapping)
Technology that maps database tables to code objects. SG Church uses Django ORM.

## P

### PCI DSS (Payment Card Industry Data Security Standard)
Security standard for organizations that handle credit card information.

### Permission
Specific action a user is allowed to perform (e.g., "create member", "view reports").

### Django ORM
Object-Relational Mapper included with Django for database operations.

### PWA (Progressive Web App)
Web application that can work offline and be installed on mobile devices.

## Q

### Query
Read operation to retrieve data from the database or API.

### Queue
System for processing background jobs asynchronously.

### Quiz
Assessment within a course to test member knowledge.

## R

### RBAC (Role-Based Access Control)
Permission system where users are assigned roles that determine their access.

### Recurring Donation
Donation that repeats automatically on a schedule (monthly, quarterly, annual).

### Redis
In-memory data store used for caching and queue management.

### Role
Set of permissions assigned to users (e.g., Admin, Staff, Member).

### Template Rendering
Server-side rendering of HTML templates in Django.

## S

### Sacrament
Religious ceremony or ritual. SG Church tracks records of sacraments like baptism, communion, and marriage.

### Schema
Database structure definition, including tables, columns, and relationships. In multi-tenancy, each church has its own schema.

### Seed
Process of populating database with initial or test data.

### Serverless
Cloud computing model where the provider manages server infrastructure.

### SSR (Server-Side Rendering)
Technique where pages are rendered on the server before being sent to the browser.

### Stripe
Payment processing platform used for donations.

### Stripe Connect
Stripe product enabling platforms to process payments on behalf of multiple accounts (churches).

### Subscription
Recurring donation arrangement.

## T

### Tenant
Individual church instance in the multi-tenant system.

### Transaction
Financial record of money moving between accounts.

### Django REST Framework
Web framework for building REST APIs in Django.

### tRPC
TypeScript framework for building type-safe APIs (not used - Django REST Framework used instead).

### Turborepo
Build system for managing monorepos (not used in this project).

### Type Safety
Programming approach that catches type errors at compile time rather than runtime.

## U

### UI (User Interface)
Visual elements users interact with.

### UUID (Universally Unique Identifier)
128-bit identifier used as primary keys in many SG Church tables.

## V

### Vercel
Cloud platform (not used - Railway/Render used instead for Django).

## W

### Webhook
HTTP callback that sends real-time data when events occur.

### Workspace
In monorepo context, a package or application within the repository.

## Z

### zod
Schema validation library (not used - Django serializers used instead).

---

## Architecture Terms

### Monorepo
Repository structure containing multiple related projects (apps, packages, services).

### Schema-per-Tenant
Multi-tenancy approach where each tenant gets a separate PostgreSQL schema.

### Shared Database, Shared Schema
Multi-tenancy approach where all tenants share the same tables (not used in SG Church).

### Database-per-Tenant
Multi-tenancy approach where each tenant gets a separate database (alternative to schema-per-tenant).

## Development Terms

### Hot Reload
Development feature that automatically updates the application when code changes.

### Lint
Tool that checks code for errors and style violations.

### Mock
Simulated object or function used in testing.

### Pipeline
Automated sequence of steps in CI/CD (Continuous Integration/Continuous Deployment).

### Test Coverage
Percentage of code exercised by automated tests.

### Type Inference
TypeScript's ability to automatically determine variable types.

## Related Resources

- [README](../README.md) - Project overview
- [ARCHITECTURE](../ARCHITECTURE.md) - Technical architecture details
- [DATABASE](../DATABASE.md) - Database schema documentation
- [FAQ](./FAQ.md) - Frequently asked questions

---

*This glossary is continuously updated as the project evolves. If you notice missing terms, please submit a pull request!*
