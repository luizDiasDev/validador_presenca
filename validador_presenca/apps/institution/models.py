from django.db import models

# Create your models here.

class Institution(models.Model):
    # Definindo Colunas
    nome = models.CharField(max_length=250)
    cnpj = models.CharField(max_length=14, unique=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # Nome que vai aparecer
    class Meta:
        db_table = "instituicao"
        verbose_name = "Instituição"
        verbose_name_plural = "Instituições"

    # Como vai retornar
    def __str__(self):
        return self.nome

class Campus(models.Model):
    # Definindo FK
    instituicao = models.ForeignKey(
        Institution, # Qual model o Campus pertence
        on_delete=models.PROTECT, # Nao tem como apagar o Institution se tiver Campus vinculado 
        db_column="instituicao_id", # Nome da coluna FK
        related_name="campi", # Como acessar a info de Campus a partir da Institution como instituicao.campi.all()
    )
    nome = models.CharField(max_length=250)
    latitude = models.DecimalField(max_digits=9, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    raio_metros = models.IntegerField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus"
        verbose_name = "Campus"
        verbose_name_plural = "Campi"

    def __str__(self):
        return f"{self.nome} ({self.instituicao.nome})"

class Room(models.Model):
    campus = models.ForeignKey(
        Campus,
        on_delete=models.PROTECT,
        db_column="campus_id",
        related_name="salas",
    )
    codigo = models.CharField(max_length=20)
    nome = models.CharField(max_length=200, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sala"
        verbose_name = "Sala"
        verbose_name_plural = "Salas"

    def __str__(self):
        return f"{self.codigo} - {self.campus.nome}"

class Machine(models.Model):
    # Definindo Colunas
    sala = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        db_column="sala_id",
        related_name="maquinas",
    )
    apelido = models.CharField(max_length=20)
    codigo_pareamento = models.CharField(max_length=4, unique=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    visto_em = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # Nome que vai aparecer
    class Meta:
        db_table = "maquina"
        verbose_name = "Máquina"
        verbose_name_plural = "Máquinas"

    # Como vai retornar
    def __str__(self):
        return f"Máquina {self.codigo_pareamento} ({self.sala.codigo})"