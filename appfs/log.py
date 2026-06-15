from database import db
from datetime import datetime

class Log(db.Model):
    __tablename__ = 'logs'
    registralog = False

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idusuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    evento = db.Column(db.String(255))
    data = db.Column(db.Date)
    hora = db.Column(db.Time)

    def __init__(self, idusuario, evento):
        self.idusuario = idusuario
        self.evento = evento
        # Preenche automaticamente com a data e hora do servidor no momento da criação
        agora = datetime.now()
        self.data = agora.date()
        self.hora = agora.time()

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "idusuario": self.idusuario,
            "evento": self.evento,
            "data": self.data.strftime('%d/%m/%Y') if self.data else None,
            "hora": self.hora.strftime('%H:%M:%S') if self.hora else None
        }