from database import db

class UsuarioEmpresa(db.Model):
    __tablename__ = 'usuariosempresa'
    registralog = True
    labellog = "Vínculo usuário-empresa"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idempresa = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    idusuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    empresa = db.relationship('Empresa', backref=db.backref('usuarios_vinculados', lazy=True))
    usuario = db.relationship('Usuario', backref=db.backref('empresas_vinculadas', lazy=True))

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "idempresa": self.idempresa,
            "idusuario": self.idusuario,
            # Para facilitar a visualização de quais usuários e empresas estão vinculados um ao outro
            "nome_usuario": self.usuario.nome if self.usuario else None,
            "razao_empresa": self.empresa.razao if self.empresa else None
        }
    
    @property
    def nome(self):
        # Busca os nomes através dos relacionamentos já definidos
        v_usr = self.usuario.nome if self.usuario else f"Usuário {self.idusuario}"
        v_emp = self.empresa.razao if self.empresa else f"Empresa {self.idempresa}"
        return f"{v_usr} em {v_emp}"