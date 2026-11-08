from django.db.models import Count, Q
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.models import Aluno, Disciplina, Turma
from apps.validator.models import PresencaRecord


class DashboardService:
    def gerar_dados(self, professor=None, turma_id: int | None = None) -> dict:
        # Filtra as disciplinas do professor (ou todas caso seja administrador sem perfil professor)
        disciplinas_qs = Disciplina.objects.select_related("turma__sala").order_by(
            "nome"
        )
        if professor:
            disciplinas_qs = disciplinas_qs.filter(professor=professor)

        turmas_ids = list(disciplinas_qs.values_list("turma_id", flat=True).distinct())
        if professor and turmas_ids:
            turmas_qs = Turma.objects.filter(id__in=turmas_ids).order_by("codigo")
        else:
            turmas_qs = Turma.objects.all().order_by("codigo")

        if turma_id:
            disciplinas_qs = disciplinas_qs.filter(turma_id=turma_id)

        # Filtra registros de presenca do escopo do professor e da turma selecionada
        registros_qs = PresencaRecord.objects.select_related(
            "sessao__aula__disciplina__turma",
            "usuario",
        )
        if professor:
            registros_qs = registros_qs.filter(
                Q(sessao__professor=professor) | Q(sessao__isnull=True)
            )
        if turma_id:
            registros_qs = registros_qs.filter(
                Q(sessao__aula__disciplina__turma_id=turma_id)
                | Q(usuario__aluno__turma_id=turma_id)
            ).distinct()

        total_registros = registros_qs.count()
        aprovados = registros_qs.filter(status="APPROVED").count()
        pendentes = registros_qs.filter(status="PENDING").count()
        rejeitados = registros_qs.filter(status="REJECTED").count()

        frequencia_media = (
            round((aprovados / total_registros) * 100, 1)
            if total_registros > 0
            else 0.0
        )

        # Sessoes de chamada abertas pelo professor
        sessoes_qs = ChamadaSession.objects.all()
        if professor:
            sessoes_qs = sessoes_qs.filter(professor=professor)
        if turma_id:
            sessoes_qs = sessoes_qs.filter(aula__disciplina__turma_id=turma_id)
        total_chamadas = sessoes_qs.count()

        # Indicadores agrupados por disciplina
        resumo_disciplinas = []
        for disc in disciplinas_qs:
            regs_disc = PresencaRecord.objects.filter(sessao__aula__disciplina=disc)
            tot_d = regs_disc.count()
            aprov_d = regs_disc.filter(status="APPROVED").count()
            pend_d = regs_disc.filter(status="PENDING").count()
            rej_d = regs_disc.filter(status="REJECTED").count()
            taxa_d = round((aprov_d / tot_d) * 100, 1) if tot_d > 0 else 0.0
            chamadas_d = ChamadaSession.objects.filter(aula__disciplina=disc).count()

            resumo_disciplinas.append(
                {
                    "id": disc.id,
                    "nome": disc.nome,
                    "turma_codigo": disc.turma.codigo,
                    "chamadas": chamadas_d,
                    "total": tot_d,
                    "aprovados": aprov_d,
                    "pendentes": pend_d,
                    "rejeitados": rej_d,
                    "frequencia": taxa_d,
                }
            )

        # Resumo de frequencia por aluno matriculado
        alunos_qs = Aluno.objects.select_related("usuario", "turma").order_by(
            "turma__codigo", "matricula"
        )
        if turma_id:
            alunos_qs = alunos_qs.filter(turma_id=turma_id)
        elif professor and turmas_ids:
            alunos_qs = alunos_qs.filter(turma_id__in=turmas_ids)

        resumo_alunos = []
        for al in alunos_qs:
            regs_al = registros_qs.filter(usuario_id=al.usuario_id)
            tot_al = regs_al.count()
            aprov_al = regs_al.filter(status="APPROVED").count()
            pend_al = regs_al.filter(status="PENDING").count()
            rej_al = regs_al.filter(status="REJECTED").count()
            taxa_al = round((aprov_al / tot_al) * 100, 1) if tot_al > 0 else 0.0

            resumo_alunos.append(
                {
                    "matricula": al.matricula,
                    "nome": al.usuario.get_full_name() or al.usuario.email,
                    "turma_codigo": al.turma.codigo,
                    "aprovados": aprov_al,
                    "pendentes": pend_al,
                    "rejeitados": rej_al,
                    "total": tot_al,
                    "frequencia": taxa_al,
                }
            )

        return {
            "turmas": turmas_qs,
            "turma_selecionada": turma_id,
            "total_registros": total_registros,
            "total_chamadas": total_chamadas,
            "aprovados": aprovados,
            "pendentes": pendentes,
            "rejeitados": rejeitados,
            "frequencia_media": frequencia_media,
            "resumo_disciplinas": resumo_disciplinas,
            "resumo_alunos": resumo_alunos,
        }
