from database import db

class Departamento(db.Model):
    __tablename__ = 'departamentos'
    registralog = True
    labellog = "Departamento"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(180))

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "nome": self.nome
        }