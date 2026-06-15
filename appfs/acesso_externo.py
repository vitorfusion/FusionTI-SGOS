from database import db

from empresa import Empresa

class AcessoExterno(db.Model):
    __tablename__ = 'empresas_acesso_externo'
    registralog = True
    labellog = "Acesso externo"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_empresa = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(255), nullable=False)
    peso = db.Column(db.Integer, nullable=False)
    sentinela = db.Column(db.Integer, nullable=False, default=1)
    porta = db.Column(db.String(100), default='1319')

    empresa = db.relationship('Empresa', backref=db.backref('acessos_externos', cascade="all, delete-orphan"))

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "id_empresa": self.id_empresa,
            "razao_empresa": self.empresa.razao if self.empresa else "Empresa não encontrada",
            "descricao": self.descricao,
            "ip": self.ip,
            "peso": self.peso,
            "sentinela": self.sentinela,
            "porta": self.porta
        }
    
    @property
    def nome(self):
        return self.descricao