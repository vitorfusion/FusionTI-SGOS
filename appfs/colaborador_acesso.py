from database import db
from datetime import datetime, date

class ColaboradorAcesso(db.Model):
    __tablename__ = 'colaborador_empresa_acesso'
    registralog = True
    labellog = "Vínculo colaborador-acesso"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idcolaboradoremail = db.Column(db.Integer, db.ForeignKey('colaborador_empresa_email.id'), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    data = db.Column(db.Date, nullable=False)
    estado = db.Column(db.SmallInteger, nullable=False)

    colaborador = db.relationship('ColaboradorEmpresa', backref=db.backref('acessos', lazy=True))

    def f_para_dicionario(self):
        v_dicionario = {
            v_c.name: getattr(self, v_c.name) 
            for v_c in self.__table__.columns
        }
        
        for v_chave, v_valor in v_dicionario.items():
            if isinstance(v_valor, (datetime, date)):
                v_dicionario[v_chave] = v_valor.strftime('%d/%m/%Y')
                
        return v_dicionario
    
    @property
    def nome(self):
        # O "nome" identificador é a combinação de IP + data
        v_data_formatada = self.data.strftime('%d/%m/%Y') if self.data else "data ignorada"
        return f"Acesso: {self.ip} em {v_data_formatada}"