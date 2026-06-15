from database import db
from werkzeug.security import generate_password_hash, check_password_hash

class ApiCliente(db.Model):
    __tablename__ = 'api_cliente'
    registralog = True
    labellog = "API do cliente"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idcliente = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    idsentinela = db.Column(db.Integer, db.ForeignKey('empresas_acesso_externo.id'), nullable=False)
    usr = db.Column(db.String(80), nullable=False)
    senha = db.Column(db.String(255), nullable=False)

    empresa = db.relationship('Empresa')
    acesso_externo = db.relationship('AcessoExterno')

    def f_definir_senha(self, v_senha_pura):
        self.senha = generate_password_hash(v_senha_pura)

    def f_verificar_senha(self, v_senha_pura):
        return check_password_hash(self.senha, v_senha_pura)

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "idcliente": self.idcliente,
            "razao_empresa": self.empresa.razao if self.empresa else "Não encontrada",
            "idsentinela": self.idsentinela,
            "descricao_sentinela": self.acesso_externo.descricao if self.acesso_externo else "Sentinela não encontrado",
            "usr": self.usr
        }
    
    @property
    def nome(self):
        return self.usr