"""Forms for the members app."""

import uuid

from django import forms
from django.db import transaction
from django.utils.functional import cached_property

from .models import Family, FollowUp, Member, User


class FamilyForm(forms.ModelForm):
    """Create/edit a family, including who belongs to it.

    A member belongs to at most one family (Member.family), so ticking someone
    who is in another family moves them here. The head of the family is always
    a member of it: picking a head who isn't ticked adds them.
    """

    members = forms.ModelMultipleChoiceField(
        label="Miembros de la familia",
        queryset=Member.objects.none(),
        required=False,
    )

    class Meta:
        model = Family
        fields = [
            "name",
            "head_of_family",
            "address",
            "city",
            "state",
            "postal_code",
            "home_phone",
            "notes",
        ]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        people = Member.objects.filter(tenant=tenant) if tenant else Member.objects.none()
        self.fields["head_of_family"].queryset = people
        self.fields["members"].queryset = people.select_related("family").order_by(
            "last_name", "first_name"
        )
        if self.instance.pk and not self.is_bound:
            self.initial["members"] = list(
                self.instance.members.values_list("pk", flat=True)
            )

    @cached_property
    def head_outside_members(self):
        """The current head when they are not among the chosen people (old data
        where the head was not listed as a member), so saving doesn't silently
        drop them from the select."""
        value = self["head_of_family"].value()
        try:
            head_id = uuid.UUID(str(value))
        except ValueError:
            return None
        if head_id in {m.pk for m in self.selected_members}:
            return None
        return self.fields["head_of_family"].queryset.filter(pk=head_id).first()

    @cached_property
    def selected_members(self):
        """The chosen people, also after a failed POST (they are shown as chips
        and re-submitted as hidden inputs, so the page never lists everyone)."""
        ids = []
        for value in self["members"].value() or []:
            try:
                ids.append(uuid.UUID(str(value)))
            except ValueError:
                continue
        return list(
            self.fields["members"].queryset.filter(pk__in=ids).order_by(
                "last_name", "first_name"
            )
        )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        # Names are unique per church; `tenant` isn't a form field, so Django
        # wouldn't check it and a duplicate would crash with an IntegrityError.
        duplicates = Family.objects.filter(tenant=self.tenant, name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("Ya existe una familia con ese nombre.")
        return name

    def clean(self):
        cleaned = super().clean()
        head = cleaned.get("head_of_family")
        members = cleaned.get("members")
        if head is not None and members is not None and head not in members:
            cleaned["members"] = members | Member.objects.filter(pk=head.pk)
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        if self.tenant is not None:
            self.instance.tenant = self.tenant
        family = super().save(commit=True)

        chosen = self.cleaned_data.get("members")
        if chosen is not None:
            chosen_ids = [m.pk for m in chosen]
            # Someone moved here can't stay head of the family they left.
            Family.objects.filter(head_of_family__in=chosen_ids).exclude(
                pk=family.pk
            ).update(head_of_family=None)
            Member.objects.filter(tenant=family.tenant, pk__in=chosen_ids).update(
                family=family
            )
            Member.objects.filter(tenant=family.tenant, family=family).exclude(
                pk__in=chosen_ids
            ).update(family=None)
        return family


class MyContactForm(forms.ModelForm):
    """What a member may change about their own record: how to reach them.
    Everything else (status, baptism, notes, family...) is the church's call."""

    class Meta:
        model = Member
        fields = ["phone", "address", "city", "state", "postal_code", "email_opt_out"]


class FollowUpForm(forms.ModelForm):
    """What a pastor records about a follow-up. `done` marks it as already carried out."""

    done = forms.BooleanField(required=False, label="Ya lo hice")

    class Meta:
        model = FollowUp
        fields = ["kind", "notes", "due_date", "assigned_to"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(
            tenant=tenant, is_active=True, role__in=["admin", "pastor"]
        ).order_by("first_name", "last_name", "email")
        self.fields["assigned_to"].required = False
        if self.instance.pk:
            self.fields["done"].initial = self.instance.status == "done"
