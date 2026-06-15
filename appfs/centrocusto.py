from database import db

class CentroCusto(db.Model):
    __tablename__ = 'centrocusto'
    registralog = True
    labellog = "Centro de custo"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    descricao = db.Column(db.String(90), nullable=False)

    def __init__(self, descricao):
        self.descricao = descricao

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "descricao": self.descricao
        }

    @property
    def nome(self):
        return self.descricao