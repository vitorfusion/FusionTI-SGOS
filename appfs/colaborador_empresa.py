from database import db
from datetime import datetime, date
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash

class ColaboradorEmpresa(db.Model):
    __tablename__ = 'colaborador_empresa_email'
    registralog = True
    labellog = "Vínculo colaborador-empresa"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idempresa = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    nick = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.Integer, nullable=False) # Integer converte para smallint no MySQL
    telefone = db.Column(db.Numeric(17, 0)) # Numeric converte para decimal

    empresa = db.relationship('Empresa', backref=db.backref('colaboradores', lazy=True))

    def f_para_dicionario(self):
        v_dicionario = {
            v_c.name: getattr(self, v_c.name) 
            for v_c in self.__table__.columns if v_c.name != 'senha'
        }
        
        for v_chave, v_valor in v_dicionario.items():
            if isinstance(v_valor, (datetime, date)):
                v_dicionario[v_chave] = v_valor.strftime('%d/%m/%Y')
            # Converte decimal para int ou float, assim evitando erro de serialização JSON
            elif isinstance(v_valor, Decimal):
                v_dicionario[v_chave] = int(v_valor) if v_valor % 1 == 0 else float(v_valor)
                
        return v_dicionario

    def f_definir_senha(self, v_senha_pura):
        self.senha = generate_password_hash(v_senha_pura)

    def f_verificar_senha(self, v_senha_pura):
        return check_password_hash(self.senha, v_senha_pura)