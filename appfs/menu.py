from database import db

class Menu(db.Model):
    __tablename__ = 'menu'
    registralog = True
    labellog = "Menu"

    posicao = db.Column(db.Integer, primary_key=True, autoincrement=False)
    texto = db.Column(db.Text)
    url = db.Column(db.Text)

    def f_para_dicionario(self):
        v_dicionario = {
            v_c.name: getattr(self, v_c.name) 
            for v_c in self.__table__.columns
        }
        
        return v_dicionario
    
    @property
    def nome(self):
        return self.texto

    @property
    def id(self):
        return self.posicao