from database import db
from datetime import datetime, date

class Pagina(db.Model):
    __tablename__ = 'pagina'
    registralog = True
    labellog = "Página"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text, nullable=False)
    banner = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    conteudo = db.Column(db.Text)

    def f_para_dicionario(self):
        v_dicionario = {v_c.name: getattr(self, v_c.name) for v_c in self.__table__.columns}
        
        return v_dicionario
    
    @property
    def nome(self):
        return self.title