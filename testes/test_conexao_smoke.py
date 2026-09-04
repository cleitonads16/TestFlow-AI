from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modelos import Base, CasoDeTeste, CategoriaCasoDeTeste, Escopo, Prioridade, Projeto


def test_criar_tabelas_e_inserir_registro(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine)

    with Sessao() as sessao:
        projeto = Projeto(nome="PDI - Gestor de Casos de Teste", descricao="Projeto de teste")
        escopo = Escopo(nome_arquivo="escopo-exemplo.docx", projeto=projeto)
        caso = CasoDeTeste(
            codigo="CT-001",
            titulo="Validar modelagem das entidades",
            categoria=CategoriaCasoDeTeste.FUNCIONAL,
            prioridade=Prioridade.ALTA,
            escopo=escopo,
        )
        sessao.add(projeto)
        sessao.add(escopo)
        sessao.add(caso)
        sessao.commit()

        assert sessao.query(Projeto).count() == 1
        assert sessao.query(Escopo).count() == 1
        assert sessao.query(CasoDeTeste).count() == 1

        caso_salvo = sessao.query(CasoDeTeste).first()
        assert caso_salvo.titulo == "Validar modelagem das entidades"
        assert caso_salvo.categoria == CategoriaCasoDeTeste.FUNCIONAL
        assert caso_salvo.escopo.projeto.nome == "PDI - Gestor de Casos de Teste"
