from database import db

class OSAgendamento(db.Model):
    __tablename__ = 'os_agendamento'
    registralog = True
    labellog = "Agendamento de OS"

    # O CamelCase pode causar problemas no SQLAlchemy, então é necessário um tratamento
    idagendamento = db.Column('idAgendamento', db.Integer, primary_key=True, autoincrement=True, key='idagendamento')
    idempresa = db.Column('idEmpresa', db.Integer, db.ForeignKey('empresas.id'), nullable=False, key='idempresa')
    idmodelo = db.Column('idModelo', db.Integer, db.ForeignKey('modeloos.id'), nullable=False, key='idmodelo')
    intervalo = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Boolean, nullable=False)

    def __init__(self, idempresa, idmodelo, intervalo, estado, idagendamento=None):
        if idagendamento is not None:
            self.idagendamento = idagendamento
        self.idempresa = idempresa
        self.idmodelo = idmodelo
        self.intervalo = intervalo
        self.estado = estado

    def f_para_dicionario(self):
        return {
            "idagendamento": self.idagendamento,
            "idempresa": self.idempresa,
            "idmodelo": self.idmodelo,
            "intervalo": self.intervalo,
            "estado": self.estado
        }
    
    @property
    def id(self):
        return self.idagendamento
    
    @property
    def nome(self):
        return f"Agendamento #{self.id}"