from database import db

from user import Usuario

class Colaborador(db.Model):
    __tablename__ = 'colaboradores'
    registralog = True
    labellog = "Colaborador"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idusuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    usuario = db.relationship('Usuario', backref=db.backref('colaborador', uselist=False))

    # Retorna o nome do usuário vinculado, para viabilizar os logs
    @property
    def nome(self):
        if self.usuario:
            return self.usuario.nome
        
        if self.idusuario:
            v_user = Usuario.query.get(self.idusuario)
            if v_user:
                return v_user.nome
                
        return "Usuário desconhecido"

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "idusuario": self.idusuario,
            "nome_usuario": self.nome
        }