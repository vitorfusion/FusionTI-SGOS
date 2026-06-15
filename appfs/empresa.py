from database import db
from datetime import datetime, date

class Empresa(db.Model):
    __tablename__ = 'empresas'
    registralog = True
    labellog = "Empresa"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    razao = db.Column(db.String(255))
    cnpj = db.Column(db.String(150), nullable=False, unique=True)
    ie = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    rua = db.Column(db.String(100), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    cep = db.Column(db.String(11), nullable=False)
    mapa = db.Column(db.String(300), nullable=False)
    idusuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    valorcontrato = db.Column(db.Numeric(10, 2), nullable=False)
    valordeslocamento = db.Column(db.Numeric(10, 2), nullable=False)
    nvisitasfisicas = db.Column(db.Integer, nullable=False)
    vigenciacontrato = db.Column(db.Date, nullable=False)
    diavencimento = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Boolean)

    def f_para_dicionario(self):
        v_dicionario = {v_c.name: getattr(self, v_c.name) for v_c in self.__table__.columns}
        for v_chave, v_valor in v_dicionario.items():
            if isinstance(v_valor, (datetime, date)):
                v_dicionario[v_chave] = v_valor.strftime('%d/%m/%Y')
            # Garante que valores decimais sejam convertidos para float no JSON
            if isinstance(v_valor, (float,)):
                v_dicionario[v_chave] = float(v_valor)
        return v_dicionario
    
    @property
    def nome(self):
        return self.razao