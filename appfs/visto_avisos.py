from database import db

# Como esta é uma tabela puramente relacional, não é necessária uma classe tradicional 
VistoAvisos = db.Table(
    'os_avisos_visto',
    db.metadata,
    db.Column('idOs', db.Integer, db.ForeignKey('os.id'), primary_key=True),
    db.Column('idColaborador', db.Integer, db.ForeignKey('colaboradores.id'), primary_key=True)
)