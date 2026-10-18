from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        from core import audit
        from education.models import Course, CourseBlock, Enrollment
        from events.models import Event, EventAnnouncement, EventSeries
        from finance.models import Donation, Expense
        from members.models import Family, Member, Tag, User
        from tenants.models import Site, Tenant

        for model, label in (
            (Member, "Miembro"),
            (Family, "Familia"),
            (Tag, "Etiqueta"),
            (User, "Usuario"),
            (Donation, "Donación"),
            (Expense, "Gasto"),
            (Course, "Curso"),
            (CourseBlock, "Bloque de cursos"),
            (Enrollment, "Inscripción a curso"),
            (Event, "Evento"),
            (EventSeries, "Serie de eventos"),
            (EventAnnouncement, "Anuncio de evento"),
            (Tenant, "Configuración de la iglesia"),
            (Site, "Sede"),
        ):
            audit.register(model, label)
