"""
Fill a tenant with realistic, fake demo data (members, families, tags,
donations, expenses, courses, events) so a demo or test install isn't empty.

All seeded members use the @demo.sgchurch.test email domain, which is how the
command recognises a previous run and skips (idempotent) unless --force.

Usage:
    python manage.py seed_demo_data                  # the only tenant, 520 people
    python manage.py seed_demo_data --tenant main --members 800
"""

import os
import random
import unicodedata
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from education.models import Course, CourseBlock, Enrollment
from events.models import Event, EventAttendance, EventRegistration
from finance.models import Donation, Expense
from members.models import Family, Member, Tag, User
from tenants.models import Tenant

DEMO_DOMAIN = "demo.sgchurch.test"

MALE = [
    "José", "Luis", "Carlos", "Juan", "Jorge", "Manuel", "Andrés", "Daniel", "David",
    "Diego", "Esteban", "Fernando", "Gabriel", "Gerardo", "Gustavo", "Héctor", "Iván",
    "Javier", "Kevin", "Marco", "Mario", "Mauricio", "Miguel", "Pablo", "Pedro", "Rafael",
    "Ricardo", "Roberto", "Sergio", "Steven", "Alejandro", "Allan", "Bryan", "Christian",
    "Darío", "Eduardo", "Felipe", "Francisco", "Guillermo", "Josué", "Mateo", "Samuel",
]
FEMALE = [
    "María", "Ana", "Carmen", "Laura", "Sofía", "Daniela", "Andrea", "Gabriela", "Paola",
    "Karla", "Mónica", "Patricia", "Rebeca", "Raquel", "Rosa", "Silvia", "Tatiana",
    "Valeria", "Verónica", "Vanessa", "Yolanda", "Adriana", "Alejandra", "Beatriz",
    "Cristina", "Elena", "Fabiola", "Jimena", "Lucía", "Marcela", "Natalia", "Priscila",
    "Sara", "Susana", "Isabel", "Julieta", "Melissa", "Noelia", "Ruth", "Esther",
]
SURNAMES = [
    "Rodríguez", "Mora", "Jiménez", "Vargas", "Hernández", "Solís", "Araya", "Castro",
    "Calderón", "Chaves", "Quesada", "Rojas", "Salazar", "Soto", "Ramírez", "Gómez",
    "Fernández", "González", "Alfaro", "Barrantes", "Brenes", "Campos", "Cordero",
    "Corrales", "Cruz", "Díaz", "Esquivel", "Fallas", "Gamboa", "Guzmán", "Leitón",
    "Madrigal", "Murillo", "Núñez", "Obando", "Pérez", "Picado", "Porras", "Retana",
    "Sáenz", "Sánchez", "Segura", "Torres", "Ulate", "Valverde", "Zamora", "Zúñiga",
]
PLACES = [
    ("San José", "San José", "10101"), ("Escazú", "San José", "10201"),
    ("Desamparados", "San José", "10301"), ("Alajuela", "Alajuela", "20101"),
    ("Heredia", "Heredia", "40101"), ("Cartago", "Cartago", "30101"),
    ("Curridabat", "San José", "11801"), ("Santa Ana", "San José", "10901"),
    ("San Pedro", "San José", "11501"), ("Tibás", "San José", "11301"),
]
TAGS = [
    ("Líder", "#DC2626"), ("Voluntario", "#16A34A"), ("Alabanza", "#9333EA"),
    ("Jóvenes", "#2563EB"), ("Niños", "#F59E0B"), ("Diácono", "#0D9488"),
    ("Maestro", "#DB2777"), ("Intercesión", "#64748B"),
]
VENDORS = [
    ("ICE - Electricidad", "utilities"), ("AyA - Agua", "utilities"),
    ("Kölbi Internet", "utilities"), ("Librería Universal", "programs"),
    ("Sonido y Luces CR", "maintenance"), ("Ferretería El Mástil", "maintenance"),
    ("Limpieza Brillante", "operations"), ("Supermercado Más x Menos", "programs"),
    ("Misiones Mundiales", "missions"), ("Imprenta Nacional", "operations"),
]
CAMPAIGN_AMOUNTS = {
    "tithe": (15, 250), "offering": (3, 60), "building": (20, 400),
    "missions": (5, 100), "youth": (5, 80), "other": (5, 50),
}


EVENT_PLAN = [
    ("Culto dominical", "service", -14, 3, 400), ("Culto dominical", "service", 7, 3, 400),
    ("Reunión de líderes", "meeting", -10, 2, 40, {"courses": ["Liderazgo Cristiano"]}), ("Reunión de líderes", "meeting", 12, 2, 40, {"courses": ["Liderazgo Cristiano"]}),
    ("Retiro de matrimonios", "retreat", 21, 48, 60, {"requires_married": True}), ("Campamento de jóvenes", "camp", 35, 72, 80),
    ("Conferencia de misiones", "conference", 50, 8, 250, {"requires_baptized": True}), ("Noche de alabanza", "special", 5, 3, 200),
    ("Feria de la familia", "special", -30, 6, 300), ("Bautizos", "special", 18, 3, 100),
    ("Retiro de damas", "retreat", -45, 30, 70, {"requires_baptized": True}), ("Cena de agradecimiento a voluntarios", "special", 28, 3, 90),
]


def ascii_slug(text):
    return (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    )


class Command(BaseCommand):
    help = "Fill a tenant with fake demo data (people, finance, courses, events)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            default=os.environ.get("SEED_DEMO_TENANT") or None,
            help="Tenant subdomain (default: SEED_DEMO_TENANT, else the only tenant)",
        )
        parser.add_argument("--members", type=int, default=520)
        parser.add_argument("--seed", type=int, default=2026)
        parser.add_argument("--force", action="store_true", help="Seed even if already seeded")

    def handle(self, *args, **opts):
        self.rng = random.Random(opts["seed"])
        tenant = self._get_tenant(opts["tenant"])

        already = Member.objects.filter(
            tenant=tenant, email__endswith=f"@{DEMO_DOMAIN}"
        ).exists()
        if already and not opts["force"]:
            updated, removed = self._event_requirements(tenant)
            added = self._attendance(tenant)
            self.stdout.write(
                f"Demo data already present (use --force to add more people). "
                f"Requirements applied to {updated} events ({removed} ineligible "
                f"registrations/attendances removed). "
                f"Attendance backfilled for {added} past events."
            )
            return

        with transaction.atomic():
            members = self._members_and_families(tenant, opts["members"])
            self._tags(tenant, members)
            donations = self._donations(tenant, members)
            expenses = self._expenses(tenant)
            self._courses(tenant, members)
            events = self._events(tenant, members)
            self._attendance(tenant)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(members)} members, {donations} donations, "
                f"{expenses} expenses, {events} events into '{tenant.subdomain}'."
            )
        )

    def _get_tenant(self, subdomain):
        if subdomain:
            tenant = Tenant.objects.filter(subdomain=subdomain).first()
            if not tenant:
                raise CommandError(f"No tenant with subdomain '{subdomain}'.")
            return tenant
        tenants = list(Tenant.objects.all()[:2])
        if len(tenants) != 1:
            raise CommandError("Pass --tenant: expected exactly one tenant to exist.")
        return tenants[0]

    # ------------------------------------------------------------------ people

    def _birth(self, min_age, max_age):
        days = self.rng.randint(min_age * 365, max_age * 365)
        return date.today() - timedelta(days=days)

    def _new_member(self, tenant, first, last, gender, birth, family, marital, counter):
        age = (date.today() - birth).days // 365
        status = self.rng.choices(
            ["member", "attendee", "visitor", "inactive"], [55, 20, 15, 10]
        )[0]
        if age < 12 and status == "visitor":
            status = "attendee"
        baptized = age >= 8 and self.rng.random() < {
            "member": 0.85, "attendee": 0.35, "visitor": 0.1, "inactive": 0.6
        }[status]
        place = self.rng.choice(PLACES)
        email = None
        if age >= 16:
            email = f"{ascii_slug(first)}.{ascii_slug(last.split()[0])}{counter}@{DEMO_DOMAIN}"
        today = date.today()
        return Member(
            tenant=tenant,
            first_name=first,
            last_name=last,
            email=email,
            phone=f"+506 {self.rng.choice('678')}{self.rng.randint(100, 999)} {self.rng.randint(1000, 9999)}"
            if age >= 14 else "",
            date_of_birth=birth,
            gender=gender,
            marital_status=marital if age >= 18 else "",
            member_status=status,
            membership_date=(today - timedelta(days=self.rng.randint(30, 3650)))
            if status == "member" else None,
            is_baptized=baptized,
            baptism_date=(birth + timedelta(days=self.rng.randint(8 * 365, max(8 * 365 + 1, age * 365))))
            if baptized else None,
            family=family,
            address=f"{self.rng.randint(25, 400)} metros norte de la iglesia",
            city=place[0],
            state=place[1],
            postal_code=place[2],
        )

    def _members_and_families(self, tenant, target):
        members = []
        counter = 0
        used_names = set(Family.objects.filter(tenant=tenant).values_list("name", flat=True))
        while len(members) < target:
            counter += 1
            surname_a = self.rng.choice(SURNAMES)
            surname_b = self.rng.choice(SURNAMES)
            family_name = f"Familia {surname_a} {surname_b}"
            if family_name in used_names:
                family_name = f"{family_name} ({counter})"
            used_names.add(family_name)
            place = self.rng.choice(PLACES)
            family = Family.objects.create(
                tenant=tenant, name=family_name, address=f"{self.rng.randint(25, 400)} metros norte de la iglesia",
                city=place[0], state=place[1], postal_code=place[2],
                home_phone=f"+506 2{self.rng.randint(200, 799)} {self.rng.randint(1000, 9999)}",
            )
            roll = self.rng.random()
            batch = []
            husband_age = self.rng.randint(24, 72)
            if roll < 0.62:  # couple (+ kids)
                batch.append(("M", self.rng.choice(MALE), f"{surname_a} {surname_b}", self._birth(husband_age, husband_age), "married"))
                batch.append(("F", self.rng.choice(FEMALE), f"{self.rng.choice(SURNAMES)} {self.rng.choice(SURNAMES)}", self._birth(max(21, husband_age - 6), husband_age + 3), "married"))
                if husband_age >= 28:
                    for _ in range(self.rng.choices([0, 1, 2, 3, 4], [15, 25, 35, 20, 5])[0]):
                        gender = self.rng.choice("MF")
                        first = self.rng.choice(MALE if gender == "M" else FEMALE)
                        batch.append((gender, first, f"{surname_a} {surname_b}", self._birth(1, min(husband_age - 22, 25)), "single"))
            else:  # single adult / single parent / widow
                gender = self.rng.choice("MF")
                marital = self.rng.choices(["single", "divorced", "widowed"], [55, 25, 20])[0]
                batch.append((gender, self.rng.choice(MALE if gender == "M" else FEMALE), f"{surname_a} {surname_b}", self._birth(19, 80), marital))
            for gender, first, last, birth, marital in batch:
                counter += 1
                members.append(self._new_member(tenant, first, last, gender, birth, family, marital, counter))
        members = members[:target]
        Member.objects.bulk_create(members)
        # first adult in each family becomes head of family
        heads = {}
        for m in members:
            if m.family_id and m.family_id not in heads and (date.today() - m.date_of_birth).days >= 18 * 365:
                heads[m.family_id] = m
        families = list(Family.objects.filter(tenant=tenant, id__in=heads.keys()))
        for family in families:
            family.head_of_family = heads[family.id]
        Family.objects.bulk_update(families, ["head_of_family"])
        return members

    def _tags(self, tenant, members):
        tags = [Tag.objects.get_or_create(tenant=tenant, name=n, defaults={"color": c})[0] for n, c in TAGS]
        by_name = {t.name: t for t in tags}
        through = Member.tags.through
        links = []
        for m in members:
            age = (date.today() - m.date_of_birth).days // 365
            chosen = []
            if age < 12:
                chosen = [by_name["Niños"]]
            elif age < 30 and self.rng.random() < 0.5:
                chosen = [by_name["Jóvenes"]]
            elif m.member_status == "member" and self.rng.random() < 0.25:
                chosen = self.rng.sample(
                    [t for n, t in by_name.items() if n not in ("Niños", "Jóvenes")],
                    self.rng.randint(1, 2),
                )
            links += [through(member_id=m.id, tag_id=t.id) for t in chosen]
        through.objects.bulk_create(links, ignore_conflicts=True)

    # ----------------------------------------------------------------- finance

    def _donations(self, tenant, members):
        now = timezone.now()
        donations = []
        for m in members:
            age = (date.today() - m.date_of_birth).days // 365
            if age < 18 or m.member_status in ("visitor", "inactive"):
                continue
            if self.rng.random() > 0.65:
                continue
            for _ in range(self.rng.randint(2, 10)):
                campaign = self.rng.choices(
                    list(CAMPAIGN_AMOUNTS), [45, 30, 8, 8, 5, 4]
                )[0]
                low, high = CAMPAIGN_AMOUNTS[campaign]
                donations.append(
                    Donation(
                        tenant=tenant, member=m,
                        amount=Decimal(self.rng.randint(low, high)),
                        currency=tenant.currency or "USD",
                        campaign=campaign,
                        status=self.rng.choices(["completed", "pending", "failed"], [93, 4, 3])[0],
                        payment_method=self.rng.choice(["card", "cash", "transfer"]),
                        donor_name=m.full_name, donor_email=m.email or "",
                    )
                )
        Donation.objects.bulk_create(donations)
        for d in donations:  # donation_date is auto_now_add, spread it afterwards
            d.donation_date = now - timedelta(
                days=self.rng.randint(0, 364), hours=self.rng.randint(0, 23)
            )
        Donation.objects.bulk_update(donations, ["donation_date"], batch_size=500)
        return len(donations)

    def _expenses(self, tenant):
        creator = User.objects.filter(tenant=tenant).first()
        expenses = []
        today = date.today()
        for months_ago in range(12):
            base = today - timedelta(days=30 * months_ago)
            expenses.append(self._expense(tenant, creator, "Salario pastoral", "salaries", "Planilla de la iglesia", base, Decimal(1200)))
            expenses.append(self._expense(tenant, creator, "Salario secretaria", "salaries", "Planilla de la iglesia", base, Decimal(600)))
            for vendor, category in self.rng.sample(VENDORS, 5):
                expenses.append(self._expense(
                    tenant, creator, f"Pago a {vendor}", category, vendor,
                    base - timedelta(days=self.rng.randint(0, 25)),
                    Decimal(self.rng.randint(40, 700)),
                ))
        Expense.objects.bulk_create(expenses)
        return len(expenses)

    def _expense(self, tenant, creator, description, category, vendor, when, amount):
        old = (date.today() - when).days > 45
        return Expense(
            tenant=tenant, description=description, amount=amount, category=category,
            status="paid" if old else self.rng.choice(["paid", "approved", "pending"]),
            vendor_name=vendor, expense_date=when, created_by=creator,
        )

    # ----------------------------------------------------------------- courses

    def _courses(self, tenant, members):
        teachers = list(User.objects.filter(tenant=tenant))

        def course(title, description, block=None, order=0, **kw):
            c, _ = Course.objects.get_or_create(
                tenant=tenant, title=title,
                defaults=dict(description=description, course_block=block, order_in_block=order,
                              instructor=self.rng.choice(teachers) if teachers else None, **kw),
            )
            return c

        b1, _ = CourseBlock.objects.get_or_create(tenant=tenant, name="Formación de Nuevos Creyentes", defaults={"description": "Ruta de discipulado inicial."})
        b2, _ = CourseBlock.objects.get_or_create(tenant=tenant, name="Matrimonio y Familia", defaults={"description": "Fortalecer el hogar cristiano."})
        c1 = course("Fundamentos de la Fe", "Doctrinas básicas del cristianismo.", b1, 1)
        c2 = course("Bautismo y Discipulado", "Preparación para el bautismo.", b1, 2)
        c3 = course("Vida Cristiana Práctica", "Oración, lectura bíblica y servicio.", b1, 3, capacity=60)
        c2.prerequisite_courses.add(c1)
        c3.prerequisite_courses.add(c2)
        m1 = course("Preparación Prematrimonial", "Para parejas que planean casarse.", b2, 1)
        m2 = course("Enriquecimiento Matrimonial", "Para matrimonios.", b2, 2, requires_married=True)
        m3 = course("Crianza con Propósito", "Formando hijos en la fe.", b2, 3, requires_married=True)
        s1 = course("Escuela Bíblica para Jóvenes", "Estudio bíblico juvenil.", capacity=40)
        s2 = course("Liderazgo Cristiano", "Para líderes de ministerio.", requires_baptized=True, capacity=30)
        s3 = course("Evangelismo Básico", "Cómo compartir tu fe.")

        adults = [m for m in members if (date.today() - m.date_of_birth).days >= 16 * 365]
        for c in [c1, c2, c3, m1, m2, m3, s1, s2, s3]:
            pool = self.rng.sample(adults, min(len(adults), self.rng.randint(25, 70)))
            for m in pool:
                ok, _ = c.can_enroll(m)
                if not ok:
                    continue
                enrollment = Enrollment.objects.create(tenant=tenant, member=m, course=c)
                outcome = self.rng.choices(["completed", "enrolled", "dropped"], [55, 33, 12])[0]
                if outcome == "completed":
                    enrollment.mark_completed()
                elif outcome == "dropped":
                    enrollment.status = "dropped"
                    enrollment.save(update_fields=["status"])

        # A few members who finished every course of a block, so the demo shows
        # issued certificates (random sampling rarely completes a whole chain).
        for chain in ([c1, c2, c3], [m1, m2, m3]):
            for m in self.rng.sample(adults, 12):
                for c in chain:
                    if c.requires_married and m.marital_status != "married":
                        break
                    enrollment, _ = Enrollment.objects.get_or_create(
                        tenant=tenant, member=m, course=c
                    )
                    enrollment.mark_completed()

    # ------------------------------------------------------------------ events

    def _events(self, tenant, members):
        now = timezone.now()
        adults = [m for m in members if (date.today() - m.date_of_birth).days >= 14 * 365]
        for title, kind, offset_days, hours, capacity, *extra in EVENT_PLAN:
            rules = extra[0] if extra else {}
            start = now + timedelta(days=offset_days)
            event, created = Event.objects.get_or_create(
                tenant=tenant, title=title, start_at=start.replace(minute=0, second=0, microsecond=0),
                defaults=dict(event_type=kind, requires_baptized=rules.get("requires_baptized", False),
                              requires_married=rules.get("requires_married", False), location="Templo principal" if kind in ("service", "meeting", "special") else "Centro de retiros",
                              end_at=start + timedelta(hours=hours), capacity=capacity,
                              description=f"{title} - evento de demostración."),
            )
            if not created:
                continue
            if rules.get("courses"):
                event.required_courses.set(
                    Course.objects.filter(tenant=tenant, title__in=rules["courses"])
                )
            eligible = [m for m in adults if event.meets_requirements(m)[0]]
            count = min(capacity, self.rng.randint(int(capacity * 0.3), int(capacity * 0.95)), len(eligible))
            EventRegistration.objects.bulk_create(
                [EventRegistration(tenant=tenant, member=m, event=event) for m in self.rng.sample(eligible, count)]
            )
        return len(EVENT_PLAN)

    def _event_requirements(self, tenant):
        """Apply EVENT_PLAN's requirements to demo events created before the
        plan had any, then drop registrations and attendances of members who
        don't meet them. Only events with no requirements yet are touched, so
        anything edited by hand (or already backfilled) is left alone."""
        updated = removed = 0
        for title, *_rest in EVENT_PLAN:
            rules = _rest[4] if len(_rest) > 4 else {}
            if not rules:
                continue
            for event in Event.objects.filter(tenant=tenant, title=title):
                if (
                    event.requires_baptized
                    or event.requires_married
                    or event.required_courses.exists()
                ):
                    continue
                event.requires_baptized = rules.get("requires_baptized", False)
                event.requires_married = rules.get("requires_married", False)
                event.save(update_fields=["requires_baptized", "requires_married"])
                if rules.get("courses"):
                    event.required_courses.set(
                        Course.objects.filter(tenant=tenant, title__in=rules["courses"])
                    )
                for rel in (event.registrations, event.attendances):
                    for row in rel.select_related("member"):
                        if not event.meets_requirements(row.member)[0]:
                            row.delete()
                            removed += 1
                updated += 1
        return updated, removed

    def _attendance(self, tenant):
        """Attendance for finished events that have none yet: most of the
        registered members show up, plus some walk-ins who never registered.
        Idempotent - events that already have attendance are left alone."""
        now = timezone.now()
        everyone = list(Member.objects.filter(tenant=tenant, date_of_birth__lte=date.today() - timedelta(days=14 * 365)))
        done = 0
        for event in Event.objects.filter(tenant=tenant, start_at__lt=now, attendances__isnull=True):
            registered = list(
                event.registrations.filter(status="registered").values_list("member_id", flat=True)
            )
            attended = {m for m in registered if self.rng.random() < 0.82}
            walk_ins = self.rng.sample(everyone, min(len(everyone), self.rng.randint(5, 40))) if everyone else []
            attended |= {m.id for m in walk_ins if event.meets_requirements(m)[0]}
            EventAttendance.objects.bulk_create(
                [EventAttendance(tenant=tenant, member_id=m_id, event=event) for m_id in attended]
            )
            done += 1
        return done
