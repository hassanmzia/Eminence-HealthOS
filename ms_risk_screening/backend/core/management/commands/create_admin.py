"""
Management command: create_admin
Creates a Django superuser for admin panel access.

Usage:
    python manage.py create_admin
    python manage.py create_admin --email admin@hospital.com --password MySecurePass1!
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a Django superuser for admin panel access."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default="admin",
            help="Admin username (default: admin)",
        )
        parser.add_argument(
            "--email",
            type=str,
            default="admin@eminence.health",
            help="Admin email (default: admin@eminence.health)",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="admin123",
            help="Admin password (default: admin123)",
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Superuser '{username}' already exists. Updating password."
                )
            )
            user = User.objects.get(username=username)
            user.set_password(password)
            user.email = email
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Updated superuser '{username}' password.")
            )
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created superuser '{username}' ({email})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nYou can now log in to Django admin at /admin/ with:\n"
                f"  Username: {username}\n"
                f"  Password: {password}\n"
            )
        )
