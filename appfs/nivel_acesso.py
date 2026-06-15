from database import db

class NivelAcesso(db.Model):
    __tablename__ = 'nacesso'
    registralog = True
    labellog = "Nível de acesso"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(50), nullable=False)
    # O parâmetro extra faz a correspondência da variável pra coluna no banco
    # O hífen pode causar problemas no SQLAlchemy por ser um operador de subtração, então é necessário um tratamento
    item_menu = db.Column('item-menu', db.SmallInteger, nullable=False, default=0)
    pagina = db.Column(db.SmallInteger, nullable=False, default=0)
    usuario = db.Column(db.SmallInteger, nullable=False, default=0)
    colaborador = db.Column(db.SmallInteger, nullable=False, default=0)
    departamento = db.Column(db.SmallInteger, nullable=False, default=0)
    col_departamento = db.Column('col-departamento', db.SmallInteger, nullable=False, default=0)
    financeiro = db.Column(db.SmallInteger, nullable=False, default=0)
    empresa = db.Column(db.SmallInteger, nullable=False, default=0)
    usr_empresa = db.Column('usr-empresa', db.SmallInteger, nullable=False, default=0)
    mod_os = db.Column('mod-os', db.SmallInteger, nullable=False, default=0)
    os = db.Column(db.SmallInteger, nullable=False, default=0)
    marketing = db.Column(db.SmallInteger, nullable=False, default=0)
    analitico = db.Column(db.SmallInteger, nullable=False, default=0)

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "item_menu": self.item_menu,
            "pagina": self.pagina,
            "usuario": self.usuario,
            "colaborador": self.colaborador,
            "departamento": self.departamento,
            "col_departamento": self.col_departamento,
            "financeiro": self.financeiro,
            "empresa": self.empresa,
            "usr_empresa": self.usr_empresa,
            "mod_os": self.mod_os,
            "os": self.os,
            "marketing": self.marketing,
            "analitico": self.analitico
        }