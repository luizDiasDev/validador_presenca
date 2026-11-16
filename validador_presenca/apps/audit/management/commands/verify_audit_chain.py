from django.core.management.base import BaseCommand, CommandError

from apps.audit.domain.log_register import verify_chain


class Command(BaseCommand):
    help = "Confere a cadeia de hashes do log de auditoria e aponta o primeiro registro adulterado."

    def handle(self, *args, **options):
        result = verify_chain()
        if result.legacy:
            self.stdout.write(
                f"{result.legacy} registro(s) anteriores à versão 2 do hash não podem ser recalculados e foram pulados."
            )
        if not result.intact:
            raise CommandError(
                f"Cadeia quebrada no registro #{result.broken_id}: {result.reason} "
                f"({result.checked} registro(s) conferidos antes dele)."
            )
        self.stdout.write(self.style.SUCCESS(f"Cadeia íntegra: {result.checked} registro(s) conferidos."))
