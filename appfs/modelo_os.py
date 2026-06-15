from database import db

class ModeloOS(db.Model):
    __tablename__ = 'modeloos'
    registralog = True
    labellog = "Modelo de OS"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    iddepartamento = db.Column(db.Integer, db.ForeignKey('departamentos.id'), nullable=False)
    predescricao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    peso = db.Column(db.Integer, nullable=False)
    grupo = db.Column(db.SmallInteger, nullable=False)

    def __init__(self, iddepartamento, predescricao, descricao, peso, grupo, id=None):
        if id is not None:
            self.id = id
        self.iddepartamento = iddepartamento
        self.predescricao = predescricao
        self.descricao = descricao
        self.peso = peso
        self.grupo = grupo

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "iddepartamento": self.iddepartamento,
            "predescricao": self.predescricao,
            "descricao": self.descricao,
            "peso": self.peso,
            "grupo": self.grupo
        }
    
    @property
    def nome(self):
        return self.predescricao if self.predescricao else f"OS #{self.id}"