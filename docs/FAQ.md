# Frequently Asked Questions (FAQ)

## General Questions

### What is SG Church?
SG Church is a free, open-source church management SaaS platform designed to help churches of all sizes manage their membership, finances, events, education programs, and sacraments records.

### Is SG Church really free?
Yes! SG Church is completely free to use. The platform is funded by voluntary donations from churches and individuals who believe in supporting ministry technology. Churches can donate if they find value in the platform, but donations are never required.

### What size of church can use SG Church?
SG Church is designed to scale from small house churches (10-50 members) to large congregations (5,000+ members). The multi-tenant architecture ensures performance regardless of size.

### Is my church's data secure?
Absolutely. We implement schema-per-tenant database isolation, meaning each church's data is physically separated in the database. We follow industry best practices including encryption at rest and in transit, regular backups, and compliance with GDPR and other data protection regulations. See [SECURITY.md](../SECURITY.md) for details.

### Can I self-host SG Church?
Yes! SG Church is open source (MIT License), so you can self-host on your own infrastructure. We provide deployment guides for Vercel, AWS, and other platforms. See [docs/DEPLOYMENT.md](./DEPLOYMENT.md).

## Technical Questions

### What tech stack does SG Church use?
- **Backend**: Django 5, Python 3.12, Django REST Framework
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Database**: PostgreSQL 16+ with Django ORM
- **Infrastructure**: Render/VPS (hosting), PostgreSQL, Redis + Celery
- **Payments**: Stripe Connect

See [TECH_STACK.md](../TECH_STACK.md) for complete details.

### How does multi-tenancy work?
We use a schema-per-tenant approach. Each church gets its own PostgreSQL schema, providing strong data isolation while maintaining cost efficiency. A single public schema handles tenant registration and routing. See [ARCHITECTURE.md](../ARCHITECTURE.md#multi-tenancy-strategy).

### Can I integrate SG Church with my existing tools?
Phase 4 includes a public API for integrations. In earlier phases, you can use webhooks for certain events (donations, new members, etc.).

### What languages does SG Church support?
Phase 4 includes full internationalization (i18n) support. Initially, we support Spanish and English, with plans to add more languages based on community contributions.

### Does SG Church have mobile apps?
Yes! Phase 3 includes a Progressive Web App (PWA) that works offline and can be installed on mobile devices. Phase 4 adds native iOS and Android apps built with Flutter or React Native.

## Features Questions

### What modules are available?
- **Membership Management**: Members, families, roles, groups
- **Financial Management**: Donations, accounting, budgets, reports
- **Event Management**: Calendar, registration, attendance
- **Learning Management**: Courses, lessons, quizzes, certificates
- **Sacraments**: Baptism, communion, marriage records
- **Communications**: Email, SMS, push notifications

### How do donations work?
We integrate with Stripe Connect to process donations. Churches can:
- Accept one-time donations
- Set up recurring donations (monthly, quarterly, annual)
- Accept donations by category (tithes, offerings, missions)
- Generate tax receipts automatically
- Track donor history

Churches keep 100% of donations (minus Stripe's standard payment processing fees: 2.9% + $0.30 per transaction).

### Can members access the platform?
Yes! Churches can enable member portals where members can:
- Update their personal information
- Register for events
- Make donations
- View their giving history
- Take courses and track progress
- Access their sacrament records

### Does it support accounting?
Yes! The finance module includes:
- Chart of accounts
- Double-entry bookkeeping
- Budget vs. actual reports
- Financial statements
- Tax reporting
- Donation receipts
- Expense tracking

### Can I track attendance?
Yes! The attendance module allows you to:
- Track attendance by service/event
- Check members in via mobile app
- Generate attendance reports
- Identify inactive members
- Track trends over time

## Privacy & Compliance

### Is SG Church GDPR compliant?
Yes. We implement GDPR requirements including:
- Consent management
- Right to access data
- Right to be forgotten (data deletion)
- Data portability
- Privacy by design
- Data processing agreements

### How long is data retained?
Churches control their own data retention policies. By default:
- Active member data: Retained indefinitely
- Inactive members: Retained per church policy
- Financial records: 7 years (recommended for tax purposes)
- Logs and analytics: 90 days

Churches can configure custom retention policies per data type.

### Can members delete their data?
Yes. Members can request data deletion through their portal. Church admins are notified and can approve the request, which permanently deletes personal data while maintaining anonymized statistical records for reporting.

## Donations & Support

### How can I support SG Church?
You can support the project by:
1. **Donate**: Make a one-time or recurring donation
2. **Contribute**: Submit code, documentation, or translations
3. **Spread the word**: Tell other churches about SG Church
4. **Report issues**: Help us improve by reporting bugs
5. **Pray**: Pray for the project and its users

### Are donations tax-deductible?
*To be determined based on fiscal sponsorship arrangement*

### Where do donations go?
100% of donations go toward:
- Infrastructure and hosting costs
- Development and maintenance
- Security and compliance
- Customer support
- New feature development

We publish financial transparency reports quarterly showing how funds are used.

## Getting Started

### How do I register my church?
1. Visit the SG Church platform
2. Click "Register Church"
3. Complete the registration form
4. Verify your email
5. Complete the onboarding wizard
6. Start inviting members!

### How long does setup take?
Most churches complete initial setup in 1-2 hours:
- Registration: 5 minutes
- Church information: 10 minutes
- Import members: 30-60 minutes (optional)
- Configure modules: 30 minutes
- Team training: 30 minutes

### Can I import data from my current system?
Yes! We provide CSV importers for:
- Members and families
- Donation history
- Events
- Groups

We also offer migration assistance for churches switching from other platforms.

### Do you provide training?
Yes! We offer:
- Video tutorials
- Written documentation
- Live training webinars (monthly)
- Community forum for questions
- Email support

## Contributing

### How can I contribute code?
See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed contribution guidelines.

### I found a bug. What should I do?
1. Check if it's already reported in [GitHub Issues](https://github.com/your-org/sg-church/issues)
2. If not, create a new issue with details
3. Include steps to reproduce
4. Include screenshots if applicable

### I have a feature request. Where do I suggest it?
Use [GitHub Discussions](https://github.com/your-org/sg-church/discussions) to propose new features. The community can vote and discuss before implementation.

## Troubleshooting

### I forgot my password. How do I reset it?
Click "Forgot Password" on the login page and follow the instructions sent to your email.

### I can't access a feature. Why?
Check with your church administrator. Features may be disabled or you may need specific permission roles to access them.

### The platform is slow. What can I do?
1. Check your internet connection
2. Clear browser cache
3. Try a different browser
4. Report persistent issues to support

### My email notifications aren't working
Check:
1. Your email settings in profile
2. Spam/junk folder
3. Church notification settings
4. Contact church admin to verify email service configuration

---

## Still Have Questions?

- **Community Forum**: [GitHub Discussions](https://github.com/your-org/sg-church/discussions)
- **Email Support**: support@sgchurch.app
- **Documentation**: Ver archivos en carpeta `docs/`
- **Report Issues**: [GitHub Issues](https://github.com/your-org/sg-church/issues)
