from database import db
from datetime import datetime, date, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    registralog = True
    labellog = "Usuário"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(150))
    celular = db.Column(db.String(150))
    fax = db.Column(db.String(150))
    cpfcnpj = db.Column(db.String(20))
    rgie = db.Column(db.String(20))
    tipo = db.Column(db.String(8))
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    datacadastro = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    datanascimento = db.Column(db.Date)
    nivel = db.Column(db.Integer, nullable=False)
    # Boolean converte para tinyint(1) no MySQL
    estado = db.Column(db.Boolean, nullable=False)

    # Transforma o objeto em dicionário para possibilitar retorno em JSON
    def f_para_dicionario(self):
        # A senha é omitida por segurança
        v_dicionario = {v_c.name: getattr(self, v_c.name) for v_c in self.__table__.columns if v_c.name != 'senha'}
        for v_chave, v_valor in v_dicionario.items():
            if isinstance(v_valor, (datetime, date)):
                v_dicionario[v_chave] = v_valor.strftime('%d/%m/%Y')
        return v_dicionario
    
    # Gera o hash pras senhas
    def f_definir_senha(self, v_senha_pura):
        self.senha = generate_password_hash(v_senha_pura)

    # Verifica se a senha inserida corresponde ao hash
    def f_verificar_senha(self, v_senha_pura):
        return check_password_hash(self.senha, v_senha_pura)