from database import db

class AvisoOS(db.Model):
    __tablename__ = 'os_avisos'
    registralog = True
    labellog = "Aviso de ordem de serviço"

    idaviso = db.Column('idAviso', db.Integer, primary_key=True, autoincrement=True)
    idos = db.Column('idOs', db.Integer, db.ForeignKey('os.id'), nullable=False)
    origem = db.Column(db.Integer, nullable=False)
    analitico = db.Column(db.Boolean, default=False, index=True) # index=True é usado para indicar que o campo receberá tratamento diferenciado no banco (BTree)

    def __init__(self, idos, origem, analitico=False):
        self.idos = idos
        self.origem = origem
        self.analitico = analitico

    def f_para_dicionario(self):
        return {
            "idaviso": self.idaviso,
            "idos": self.idos,
            "origem": self.origem,
            "analitico": self.analitico
        }
    
    @property
    def id(self):
        return self.idaviso
    
    @property
    def nome(self):
        return f"Aviso #{self.id}"