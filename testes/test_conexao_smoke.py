from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modelos import Base, Prioridade, Projeto, StatusTarefa, Tarefa


def test_criar_tabelas_e_inserir_registro(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine)

    with Sessao() as sessao:
        projeto = Projeto(nome="PDI - To-Do Avançado", descricao="Projeto de teste")
        tarefa = Tarefa(
            titulo="Modelar entidades",
            status=StatusTarefa.CONCLUIDA,
            prioridade=Prioridade.ALTA,
            projeto=projeto,
        )
        sessao.add(projeto)
        sessao.add(tarefa)
        sessao.commit()

        assert sessao.query(Projeto).count() == 1
        assert sessao.query(Tarefa).count() == 1

        tarefa_salva = sessao.query(Tarefa).first()
        assert tarefa_salva.titulo == "Modelar entidades"
        assert tarefa_salva.status == StatusTarefa.CONCLUIDA
        assert tarefa_salva.projeto.nome == "PDI - To-Do Avançado"
