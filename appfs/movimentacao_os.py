from database import db
from datetime import datetime, date

class MovimentacaoOS(db.Model):
    __tablename__ = 'movimentacaoos'
    registralog = True
    labellog = "Movimentação de OS"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idos = db.Column(db.Integer, db.ForeignKey('os.id'), nullable=True)
    idcolaborador = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=True)
    datamov = db.Column(db.Date, nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    visivel = db.Column(db.Integer, nullable=False)

    def f_para_dicionario(self):
        v_dicionario = {v_c.name: getattr(self, v_c.name) for v_c in self.__table__.columns}
        for v_chave, v_valor in v_dicionario.items():
            if isinstance(v_valor, (datetime, date)):
                v_dicionario[v_chave] = v_valor.strftime('%d/%m/%Y')

            if isinstance(v_valor, (float,)):
                v_dicionario[v_chave] = float(v_valor)
        return v_dicionario
    
    @property
    def nome(self):
        if self.descricao:
            return self.descricao[:50] if len(self.descricao) > 50 else self.descricao
        return f"Movimentação #{self.id}"